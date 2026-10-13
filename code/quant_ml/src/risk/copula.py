import logging
from typing import Dict, List, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from risk.common import (
    as_frame,
    historical_var_es,
    level_key,
    validate_confidence,
    weight_vector,
)
from scipy import stats

logger = logging.getLogger(__name__)

COPULA_TYPES = ("gaussian", "t", "clayton", "gumbel")
MIN_FIT_ROWS = 30
KENDALL_SAMPLE = 1000


def nearest_correlation(matrix: np.ndarray) -> np.ndarray:
    symmetric = (matrix + matrix.T) / 2.0
    values, vectors = np.linalg.eigh(symmetric)
    values = np.clip(values, 1e-8, None)
    repaired = vectors @ np.diag(values) @ vectors.T
    scale = np.sqrt(np.diag(repaired))
    repaired = repaired / np.outer(scale, scale)
    np.fill_diagonal(repaired, 1.0)
    return repaired


class CopulaMLRiskModel:
    def __init__(
        self,
        copula_type: str = "gaussian",
        n_scenarios: int = 10000,
        seed: Optional[int] = None,
    ) -> None:
        if copula_type not in COPULA_TYPES:
            raise ValueError(f"Unsupported copula type: {copula_type}")
        if (
            isinstance(n_scenarios, bool)
            or not isinstance(n_scenarios, (int, np.integer))
            or n_scenarios < 1
        ):
            raise ValueError("n_scenarios must be a positive integer")
        self.copula_type = copula_type
        self.n_scenarios = int(n_scenarios)
        self.seed = seed
        self.marginals: Dict[str, np.ndarray] = {}
        self.marginal_stats: Dict[str, Dict[str, float]] = {}
        self.correlation_matrix: Optional[np.ndarray] = None
        self.degrees_freedom: float = 5.0
        self.theta: float = 1.0
        self.asset_names: Optional[np.ndarray] = None
        self.trained = False

    def fit(self, returns) -> "CopulaMLRiskModel":
        frame = as_frame(returns, min_rows=MIN_FIT_ROWS)
        self.asset_names = np.array(frame.columns)
        self.marginals = {col: np.sort(frame[col].to_numpy()) for col in frame.columns}
        self.marginal_stats = {
            col: {
                "mean": float(frame[col].mean()),
                "std": float(frame[col].std()),
                "skew": float(stats.skew(frame[col])),
                "kurt": float(stats.kurtosis(frame[col])),
            }
            for col in frame.columns
        }
        n_obs, n_assets = frame.shape
        ranks = frame.rank(method="average").to_numpy() / (n_obs + 1.0)
        scores = stats.norm.ppf(ranks)
        if n_assets > 1:
            self.correlation_matrix = nearest_correlation(
                np.corrcoef(scores, rowvar=False)
            )
        else:
            self.correlation_matrix = np.ones((1, 1))
        if self.copula_type == "t":
            kurtosis = float(np.mean([s["kurt"] for s in self.marginal_stats.values()]))
            self.degrees_freedom = float(
                np.clip(4.0 + 6.0 / max(kurtosis, 0.2), 3.0, 30.0)
            )
        elif self.copula_type in ("clayton", "gumbel"):
            self.theta = self.fit_archimedean(frame)
        self.trained = True
        logger.info("Copula model fitted with %s copula", self.copula_type)
        return self

    def fit_archimedean(self, frame: pd.DataFrame) -> float:
        sample = frame.tail(KENDALL_SAMPLE)
        columns = list(sample.columns)
        taus: List[float] = []
        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                tau, _ = stats.kendalltau(sample[columns[i]], sample[columns[j]])
                if np.isfinite(tau):
                    taus.append(float(tau))
        tau = float(np.mean(taus)) if taus else 0.0
        if self.copula_type == "clayton":
            tau = float(np.clip(tau, 0.02, 0.95))
            return 2.0 * tau / (1.0 - tau)
        tau = float(np.clip(tau, 0.02, 0.95))
        return 1.0 / (1.0 - tau)

    def require_trained(self, action: str) -> None:
        if not self.trained:
            raise ValueError(f"Model must be trained before {action}")

    def uniform_samples(self, n: int, rng: np.random.Generator) -> np.ndarray:
        d = len(self.asset_names)
        if self.copula_type == "gaussian":
            return stats.norm.cdf(
                rng.multivariate_normal(np.zeros(d), self.correlation_matrix, size=n)
            )
        if self.copula_type == "t":
            z = rng.multivariate_normal(np.zeros(d), self.correlation_matrix, size=n)
            chi = rng.chisquare(self.degrees_freedom, size=(n, 1))
            return stats.t.cdf(
                z / np.sqrt(chi / self.degrees_freedom), df=self.degrees_freedom
            )
        e = rng.exponential(size=(n, d))
        if self.copula_type == "clayton":
            v = rng.gamma(1.0 / self.theta, 1.0, size=(n, 1))
            return (1.0 + e / v) ** (-1.0 / self.theta)
        alpha = 1.0 / self.theta
        angle = rng.uniform(0.0, np.pi, size=(n, 1))
        w = rng.exponential(size=(n, 1))
        if alpha >= 1.0 - 1e-9:
            v = np.ones((n, 1))
        else:
            v = (
                np.sin(alpha * angle)
                / np.sin(angle) ** (1.0 / alpha)
                * (np.sin((1.0 - alpha) * angle) / w) ** ((1.0 - alpha) / alpha)
            )
        return np.exp(-((e / v) ** alpha))

    def generate_scenarios(
        self, n_scenarios: Optional[int] = None, seed: Optional[int] = None
    ) -> pd.DataFrame:
        self.require_trained("generating scenarios")
        n = int(n_scenarios if n_scenarios is not None else self.n_scenarios)
        if n < 1:
            raise ValueError("n_scenarios must be positive")
        effective_seed = seed if seed is not None else self.seed
        rng = np.random.default_rng(effective_seed)
        uniforms = np.clip(self.uniform_samples(n, rng), 1e-9, 1 - 1e-9)
        scenarios = np.empty_like(uniforms)
        for i, asset in enumerate(self.asset_names):
            sorted_values = self.marginals[asset]
            grid = (np.arange(len(sorted_values)) + 0.5) / len(sorted_values)
            scenarios[:, i] = np.interp(uniforms[:, i], grid, sorted_values)
        return pd.DataFrame(scenarios, columns=self.asset_names)

    def portfolio_scenarios(self, weights, seed: Optional[int] = None) -> np.ndarray:
        self.require_trained("calculating risk")
        vector = weight_vector(weights, list(self.asset_names))
        return self.generate_scenarios(seed=seed).to_numpy() @ vector

    def calculate_var(self, weights, confidence: float = 0.95) -> float:
        confidence = validate_confidence(confidence)
        var, _ = historical_var_es(self.portfolio_scenarios(weights), confidence)
        return var

    def calculate_es(self, weights, confidence: float = 0.95) -> float:
        confidence = validate_confidence(confidence)
        _, es = historical_var_es(self.portfolio_scenarios(weights), confidence)
        return es

    def calculate_risk_metrics(
        self, weights, confidence_levels: Sequence[float] = (0.95, 0.99)
    ) -> dict:
        values = self.portfolio_scenarios(weights)
        metrics = {
            "mean": float(values.mean()),
            "std": float(values.std()),
            "skewness": float(stats.skew(values)),
            "kurtosis": float(stats.kurtosis(values)),
        }
        for confidence in confidence_levels:
            var, es = historical_var_es(values, validate_confidence(confidence))
            key = level_key(confidence)
            metrics[f"var_{key}"] = var
            metrics[f"es_{key}"] = es
        return metrics

    def plot_return_distribution(self, weights, n_bins: int = 50) -> plt.Figure:
        values = self.portfolio_scenarios(weights)
        metrics = self.calculate_risk_metrics(weights)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(values, bins=n_bins, density=True, alpha=0.6, label="Simulated returns")
        grid = np.linspace(values.min(), values.max(), 1000)
        ax.plot(
            grid,
            stats.norm.pdf(grid, metrics["mean"], metrics["std"]),
            "r-",
            lw=2,
            label="Normal Distribution",
        )
        ax.axvline(
            -metrics["var_95"],
            color="g",
            linestyle="--",
            lw=2,
            label=f"VaR (95%): {metrics['var_95']:.4f}",
        )
        ax.axvline(
            -metrics["es_95"],
            color="r",
            linestyle="--",
            lw=2,
            label=f"ES (95%): {metrics['es_95']:.4f}",
        )
        ax.set_xlabel("Portfolio return")
        ax.set_ylabel("Density")
        ax.set_title(f"{self.copula_type.capitalize()} copula return distribution")
        ax.legend()
        return fig
