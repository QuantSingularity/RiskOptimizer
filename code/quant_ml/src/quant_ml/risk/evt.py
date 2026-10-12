import logging
from typing import List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
from quant_ml.risk.common import as_vector, validate_confidence
from scipy import stats

logger = logging.getLogger(__name__)

MIN_EXCEEDANCES = 10
SEVERITY_LEVELS = {"extreme": 0.01, "moderate": 0.05, "mild": 0.1}


class ExtremeValueRisk:
    def __init__(self, seed: Optional[int] = None) -> None:
        self.data: Optional[np.ndarray] = None
        self.pot_params: Optional[dict] = None
        self.bm_params: Optional[dict] = None
        self.threshold: Optional[float] = None
        self.threshold_quantile: Optional[float] = None
        self.block_size: Optional[int] = None
        self.fitted: bool = False
        self.rng = np.random.default_rng(seed)

    @property
    def gpd_params(self) -> Tuple[float, float]:
        if self.pot_params is None:
            raise ValueError("POT model not yet fitted.")
        return self.pot_params["shape"], self.pot_params["scale"]

    def fit_pot(
        self,
        data,
        threshold: Optional[float] = None,
        threshold_quantile: float = 0.1,
    ) -> "ExtremeValueRisk":
        values = as_vector(data, min_size=20)
        if not 0.0 < threshold_quantile < 0.5:
            raise ValueError("threshold_quantile must be between 0 and 0.5")
        self.data = values
        self.threshold_quantile = threshold_quantile
        losses = -values
        if threshold is None:
            loss_threshold = float(np.quantile(losses, 1.0 - threshold_quantile))
        else:
            loss_threshold = abs(float(threshold))
        self.threshold = -loss_threshold
        excess = losses[losses > loss_threshold] - loss_threshold
        tail_fraction = len(excess) / len(losses)
        shape, scale = self.estimate_gpd(excess, values)
        self.pot_params = {
            "shape": shape,
            "scale": max(scale, 1e-10),
            "threshold": self.threshold,
            "loss_threshold": loss_threshold,
            "tail_fraction": tail_fraction,
            "n_exceedances": int(len(excess)),
        }
        self.fitted = True
        return self

    def estimate_gpd(
        self, excess: np.ndarray, values: np.ndarray
    ) -> Tuple[float, float]:
        fallback_scale = float(np.std(values)) * 0.5
        if len(excess) < 2:
            logger.warning(
                "Too few exceedances for GPD fitting; using exponential tail"
            )
            return 0.0, fallback_scale
        if len(excess) >= MIN_EXCEEDANCES:
            try:
                shape, _, scale = stats.genpareto.fit(excess, floc=0)
                if np.isfinite(shape) and np.isfinite(scale) and scale > 0:
                    return float(shape), float(scale)
            except Exception:
                logger.warning("GPD maximum likelihood failed; using method of moments")
        mean_excess = float(np.mean(excess))
        variance = float(np.var(excess))
        if variance > 0 and mean_excess > 0:
            ratio = mean_excess**2 / variance
            return 0.5 * (1.0 - ratio), 0.5 * mean_excess * (1.0 + ratio)
        return 0.0, mean_excess if mean_excess > 0 else fallback_scale

    def fit_block_maxima(self, data, block_size: int = 20) -> dict:
        values = as_vector(data, min_size=2)
        if block_size < 2 or isinstance(block_size, bool):
            raise ValueError("block_size must be an integer of at least 2")
        n_blocks = len(values) // block_size
        if n_blocks < 2:
            raise ValueError("Data is too short for the requested block size")
        self.data = values
        self.block_size = block_size
        losses = -values[: n_blocks * block_size].reshape(n_blocks, block_size)
        block_maxima = losses.max(axis=1)
        if n_blocks < 10:
            logger.warning("Too few blocks for reliable GEV fitting")
            xi = 0.2
            loc = float(np.mean(block_maxima))
            scale = float(np.std(block_maxima)) or 1e-10
        else:
            try:
                c, loc, scale = stats.genextreme.fit(block_maxima)
                xi = -float(c)
                loc, scale = float(loc), float(scale)
            except Exception:
                logger.warning("GEV fitting failed; using normal approximation")
                xi = 0.1
                loc = float(np.mean(block_maxima))
                scale = float(np.std(block_maxima)) or 1e-10
        self.bm_params = {
            "shape": xi,
            "loc": loc,
            "scale": max(scale, 1e-10),
            "block_maxima": block_maxima,
        }
        self.fitted = True
        return self.bm_params

    def require_data(self, action: str) -> np.ndarray:
        if self.data is None:
            raise ValueError(f"Model must be fitted before {action}")
        return self.data

    def pot_quantile(self, p: float) -> float:
        params = self.pot_params
        shape, scale = params["shape"], params["scale"]
        threshold, p_u = params["loss_threshold"], params["tail_fraction"]
        if p >= p_u or p_u <= 0:
            return float(-np.quantile(self.data, p))
        ratio = p_u / p
        if abs(shape) < 1e-10:
            return threshold + scale * np.log(ratio)
        return threshold + scale / shape * (ratio**shape - 1.0)

    def bm_quantile(self, confidence: float) -> float:
        params = self.bm_params
        level = confidence**self.block_size
        return float(
            stats.genextreme.ppf(
                level, -params["shape"], loc=params["loc"], scale=params["scale"]
            )
        )

    def calculate_var(
        self,
        confidence: float = 0.95,
        method: str = "evt",
        return_period: Optional[int] = None,
    ) -> float:
        data = self.require_data("calculating VaR")
        if return_period is not None:
            if return_period <= 1:
                raise ValueError("return_period must be greater than 1")
            confidence = 1.0 - 1.0 / return_period
        confidence = validate_confidence(confidence)
        if method == "evt":
            if self.pot_params is not None:
                var = self.pot_quantile(1.0 - confidence)
            elif self.bm_params is not None:
                var = self.bm_quantile(confidence)
            else:
                raise ValueError("Either POT or Block Maxima model must be fitted")
        elif method == "historical":
            var = -float(np.quantile(data, 1.0 - confidence))
        elif method == "normal":
            var = -(
                float(np.mean(data)) - stats.norm.ppf(confidence) * float(np.std(data))
            )
        else:
            raise ValueError("Method must be 'evt', 'historical', or 'normal'")
        return max(float(var), 0.0)

    def calculate_es(self, confidence: float = 0.95, method: str = "evt") -> float:
        data = self.require_data("calculating ES")
        confidence = validate_confidence(confidence)
        var = self.calculate_var(confidence, method=method)
        if method == "evt" and self.pot_params is not None:
            params = self.pot_params
            shape, scale = params["shape"], params["scale"]
            threshold = params["loss_threshold"]
            if 1.0 - confidence >= params["tail_fraction"]:
                return self.empirical_es(data, var)
            if shape >= 1.0:
                logger.warning("Shape parameter >= 1, expected shortfall is infinite")
                return float("inf")
            es = (var + scale - shape * threshold) / (1.0 - shape)
            return max(float(es), var)
        if method in ("evt", "historical"):
            return self.empirical_es(data, var)
        if method == "normal":
            z = stats.norm.ppf(confidence)
            es = -float(np.mean(data)) + float(np.std(data)) * stats.norm.pdf(z) / (
                1.0 - confidence
            )
            return max(float(es), var)
        raise ValueError("Method must be 'evt', 'historical', or 'normal'")

    @staticmethod
    def empirical_es(data: np.ndarray, var: float) -> float:
        tail = data[data <= -var]
        if len(tail) == 0:
            return var
        return max(-float(np.mean(tail)), var)

    def generate_scenarios(
        self,
        n_scenarios: int = 1000,
        method: str = "evt",
        severity: str = "extreme",
    ) -> np.ndarray:
        data = self.require_data("generating scenarios")
        if n_scenarios < 1:
            raise ValueError("n_scenarios must be positive")
        if method == "evt":
            if self.pot_params is not None:
                params = self.pot_params
                shape, scale = params["shape"], params["scale"]
                threshold, p_u = params["loss_threshold"], params["tail_fraction"]
                limit = min(SEVERITY_LEVELS.get(severity, 0.1), p_u)
                q = self.rng.uniform(0.0, limit, n_scenarios)
                q = np.maximum(q, 1e-12)
                ratio = p_u / q
                if abs(shape) < 1e-10:
                    losses = threshold + scale * np.log(ratio)
                else:
                    losses = threshold + scale / shape * (ratio**shape - 1.0)
                return -losses
            if self.bm_params is not None:
                params = self.bm_params
                maxima = stats.genextreme.rvs(
                    -params["shape"],
                    loc=params["loc"],
                    scale=params["scale"],
                    size=n_scenarios,
                    random_state=self.rng,
                )
                return -maxima
            raise ValueError("Either POT or Block Maxima model must be fitted")
        if method == "historical":
            scenarios = data[self.rng.integers(0, len(data), n_scenarios)].copy()
            if severity == "extreme":
                cutoff = np.percentile(data, 5)
                extreme = np.where(data <= cutoff)[0]
                if len(extreme) > 0:
                    n_extreme = min(n_scenarios // 2, len(extreme))
                    scenarios[:n_extreme] = data[self.rng.choice(extreme, n_extreme)]
            return scenarios
        if method == "normal":
            std = float(np.std(data))
            std *= {"extreme": 1.5, "moderate": 1.2}.get(severity, 1.0)
            return self.rng.normal(float(np.mean(data)), std, n_scenarios)
        raise ValueError("Method must be 'evt', 'historical', or 'normal'")

    def simulate_extreme_scenarios(
        self, n_scenarios: int = 100, confidence: float = 0.95
    ) -> np.ndarray:
        self.require_data("simulating scenarios")
        method = "evt" if self.pot_params else "historical"
        var = self.calculate_var(confidence, method=method)
        collected: List[float] = []
        for _ in range(100):
            batch = self.generate_scenarios(
                n_scenarios * 10, method=method, severity="extreme"
            )
            collected.extend((-batch[batch < -var]).tolist())
            if len(collected) >= n_scenarios:
                break
        if len(collected) < n_scenarios:
            shortfall = n_scenarios - len(collected)
            collected.extend(
                (var * (1.0 + self.rng.exponential(0.1, shortfall))).tolist()
            )
        return np.array(collected[:n_scenarios])

    def tail_dependence(
        self, x, y, method: str = "empirical", threshold_quantile: float = 0.1
    ) -> float:
        return self.calculate_tail_dependence(x, y, method, threshold_quantile)

    def calculate_tail_dependence(
        self, x, y, method: str = "empirical", threshold_quantile: float = 0.1
    ) -> float:
        x_values = np.asarray(x, dtype=float).reshape(-1)
        y_values = np.asarray(y, dtype=float).reshape(-1)
        if len(x_values) != len(y_values):
            raise ValueError("x and y must have the same length")
        if len(x_values) < 10:
            raise ValueError("At least 10 paired observations are required")
        if method == "empirical":
            threshold_x = np.percentile(x_values, threshold_quantile * 100)
            threshold_y = np.percentile(y_values, threshold_quantile * 100)
            x_exceed = np.sum(x_values <= threshold_x)
            joint = np.sum((x_values <= threshold_x) & (y_values <= threshold_y))
            return float(joint / x_exceed) if x_exceed > 0 else 0.0
        if method == "copula":
            tau, _ = stats.kendalltau(x_values, y_values)
            rho = float(np.clip(np.sin(np.pi * tau / 2.0), -0.999, 0.999))
            df = 4
            argument = -np.sqrt((df + 1) * (1 - rho) / (1 + rho))
            return float(2 * stats.t.cdf(argument, df + 1))
        raise ValueError("Method must be 'empirical' or 'copula'")

    def plot_tail_distribution(
        self, confidence_levels: Sequence[float] = (0.9, 0.95, 0.99, 0.999)
    ) -> plt.Figure:
        data = self.require_data("plotting")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(data, bins=50, density=True, alpha=0.5, label="Returns")
        grid = np.linspace(data.min(), data.max(), 1000)
        ax.plot(
            grid,
            stats.norm.pdf(grid, np.mean(data), np.std(data)),
            "r--",
            label="Normal Distribution",
        )
        if self.pot_params is not None:
            params = self.pot_params
            threshold = params["loss_threshold"]
            x_tail = np.linspace(data.min(), -threshold, 500)
            density = stats.genpareto.pdf(
                -x_tail - threshold, params["shape"], scale=params["scale"]
            )
            ax.plot(
                x_tail,
                density * params["tail_fraction"],
                "g-",
                linewidth=2,
                label="EVT Tail Distribution",
            )
        colors = ["b", "g", "r", "c", "m"]
        for i, confidence in enumerate(confidence_levels):
            color = colors[i % len(colors)]
            try:
                var = self.calculate_var(confidence, method="evt")
                es = self.calculate_es(confidence, method="evt")
            except Exception as error:
                logger.warning(
                    "Could not plot for confidence %s: %s", confidence, error
                )
                continue
            ax.axvline(
                -var,
                color=color,
                linestyle="--",
                label=f"VaR ({confidence * 100:.1f}%): {var:.4f}",
            )
            if np.isfinite(es):
                ax.axvline(
                    -es,
                    color=color,
                    linestyle=":",
                    label=f"ES ({confidence * 100:.1f}%): {es:.4f}",
                )
        ax.set_xlabel("Return")
        ax.set_ylabel("Density")
        ax.set_title("Tail Distribution with VaR and ES")
        ax.legend()
        return fig

    def plot_mean_excess(self) -> plt.Figure:
        data = self.require_data("plotting")
        fig, ax = plt.subplots(figsize=(10, 6))
        losses = np.sort((-data)[-data > 0])
        n_points = min(100, len(losses) // 2)
        if n_points < 2:
            logger.warning("Insufficient data for mean excess plot")
            return fig
        thresholds = np.linspace(0, np.percentile(losses, 95), n_points)
        mean_excess = np.array(
            [
                np.mean(losses[losses > t] - t) if np.any(losses > t) else np.nan
                for t in thresholds
            ]
        )
        ax.plot(thresholds, mean_excess, "b-", linewidth=2)
        if self.pot_params is not None:
            level = self.pot_params["loss_threshold"]
            ax.axvline(
                level,
                color="r",
                linestyle="--",
                label=f"Current Threshold: {level:.4f}",
            )
            ax.legend()
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Mean Excess")
        ax.set_title("Mean Excess Function")
        return fig

    def plot_return_level(
        self, return_periods: Sequence[int] = (2, 5, 10, 20, 50, 100)
    ) -> plt.Figure:
        self.require_data("plotting")
        fig, ax = plt.subplots(figsize=(10, 6))
        periods: List[int] = []
        levels: List[float] = []
        for period in return_periods:
            if period <= 1:
                continue
            try:
                levels.append(self.calculate_var(1.0 - 1.0 / period, method="evt"))
                periods.append(period)
            except ValueError as error:
                logger.warning(
                    "Could not compute return level for %s: %s", period, error
                )
        if periods:
            ax.plot(periods, levels, "bo-")
            ax.set_xscale("log")
        ax.set_xlabel("Return period (observations)")
        ax.set_ylabel("Loss level")
        ax.set_title("Return Level Plot")
        ax.grid(True, which="both", alpha=0.3)
        return fig
