"""
Extreme Value Theory (EVT) Risk Models for RiskOptimizer

This module provides advanced risk modeling using Extreme Value Theory:
1. Peaks Over Threshold (POT) method with Generalized Pareto Distribution
2. Block Maxima method with Generalized Extreme Value Distribution
3. EVT-based VaR and ES calculation
4. Extreme scenario generation
5. Tail dependence estimation
6. Stress testing with extreme events
"""

import logging
import warnings
from typing import Any, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


class ExtremeValueRisk:
    """Extreme Value Theory Risk Model"""

    def __init__(self) -> None:
        """Initialize Extreme Value Risk Model"""
        self.data: Optional[np.ndarray] = None
        self.pot_params: Optional[dict] = None
        self.bm_params: Optional[dict] = None
        self.threshold: Optional[float] = None
        self.threshold_quantile: Optional[float] = None
        self.block_size: Optional[int] = None
        self.fitted: bool = False

    @property
    def gpd_params(self) -> Tuple[float, float]:
        """Return (shape, scale) from POT fit."""
        if self.pot_params is None:
            raise ValueError("POT model not yet fitted.")
        return self.pot_params["shape"], self.pot_params["scale"]

    def fit_pot(
        self, data: Any, threshold: Any = None, threshold_quantile: Any = 0.1
    ) -> "ExtremeValueRisk":
        """
        Fit Peaks Over Threshold model with Generalized Pareto Distribution

        Args:
            data: Array-like of returns
            threshold: Explicit threshold value (optional)
            threshold_quantile: Quantile for threshold selection (default: 0.1)

        Returns:
            self: The fitted model
        """
        if isinstance(data, (pd.Series, pd.DataFrame)):
            self.data = data.values.flatten()
        else:
            self.data = np.array(data).flatten()

        if threshold is None:
            self.threshold = np.percentile(self.data, threshold_quantile * 100)
        else:
            self.threshold = threshold
        self.threshold_quantile = threshold_quantile

        exceedances = -self.data[self.data <= -abs(self.threshold)]
        if len(exceedances) < 10:
            logger.warning("Too few exceedances for reliable GPD fitting")
            shape = 0.2
            scale = np.std(self.data) * 0.5
        else:
            try:
                excess = exceedances - abs(self.threshold)
                excess = excess[excess > 0]
                shape, _loc, scale = stats.genpareto.fit(excess, floc=0)
                logger.info(
                    f"GPD fit: shape={shape:.4f}, scale={scale:.4f}, threshold={self.threshold:.4f}"
                )
            except Exception:
                logger.warning("MLE fitting failed, using method of moments")
                excess = exceedances - abs(self.threshold)
                excess = excess[excess > 0]
                if len(excess) > 1:
                    mean_excess = np.mean(excess)
                    var_excess = np.var(excess)
                    if var_excess > 0:
                        shape = 0.5 * (1 - mean_excess**2 / var_excess)
                        scale = 0.5 * mean_excess * (1 + mean_excess**2 / var_excess)
                    else:
                        shape = 0.2
                        scale = (
                            mean_excess if mean_excess > 0 else np.std(self.data) * 0.5
                        )
                else:
                    shape = 0.2
                    scale = np.std(self.data) * 0.5

        self.pot_params = {
            "shape": shape,
            "scale": max(scale, 1e-10),
            "threshold": self.threshold,
        }
        self.fitted = True
        return self

    def fit_block_maxima(self, data: Any, block_size: Any = 20) -> dict:
        """
        Fit Block Maxima model with Generalized Extreme Value Distribution

        Args:
            data: Array-like of returns
            block_size: Size of blocks for maxima extraction

        Returns:
            dict with shape, loc, scale, and block_maxima
        """
        if isinstance(data, (pd.Series, pd.DataFrame)):
            self.data = data.values.flatten()
        else:
            self.data = np.array(data).flatten()
        self.block_size = block_size

        n_blocks = len(self.data) // block_size
        block_maxima = np.zeros(n_blocks)
        for i in range(n_blocks):
            block = -self.data[i * block_size : (i + 1) * block_size]
            block_maxima[i] = np.max(block)

        if len(block_maxima) < 10:
            logger.warning("Too few blocks for reliable GEV fitting")
            shape = 0.2
            loc = np.mean(block_maxima)
            scale = np.std(block_maxima) if np.std(block_maxima) > 0 else 1e-10
        else:
            try:
                shape, loc, scale = stats.genextreme.fit(block_maxima)
                logger.info(
                    f"GEV fit: shape={shape:.4f}, loc={loc:.4f}, scale={scale:.4f}"
                )
            except Exception:
                logger.warning("GEV fitting failed, using normal approximation")
                loc = np.mean(block_maxima)
                scale = np.std(block_maxima) if np.std(block_maxima) > 0 else 1e-10
                shape = 0.1

        self.bm_params = {
            "shape": shape,
            "loc": loc,
            "scale": scale,
            "block_maxima": block_maxima,
        }
        self.fitted = True
        return self.bm_params

    def calculate_var(
        self, confidence: Any = 0.95, method: Any = "evt", return_period: Any = None
    ) -> float:
        """
        Calculate Value at Risk (VaR) using EVT

        Args:
            confidence: Confidence level (default: 0.95 for 95% VaR)
            method: Method to use ('evt', 'historical', 'normal')
            return_period: Return period in days (alternative to confidence)

        Returns:
            var: Value at Risk at specified confidence level (positive value)
        """
        if self.data is None:
            raise ValueError("Model must be fitted before calculating VaR")
        if return_period is not None:
            confidence = 1 - 1 / return_period
        if method == "evt":
            if self.pot_params is not None:
                shape = self.pot_params["shape"]
                scale = self.pot_params["scale"]
                threshold = self.pot_params["threshold"]
                p_threshold = (
                    self.threshold_quantile if self.threshold_quantile else 0.1
                )
                p = 1 - confidence
                if p <= 0:
                    p = 1e-10
                if abs(shape) < 1e-10:
                    var = abs(threshold) + scale * np.log(p_threshold / p)
                else:
                    var = abs(threshold) + scale / shape * (
                        (p_threshold / p) ** shape - 1
                    )
                return abs(var)
            elif self.bm_params is not None:
                shape = self.bm_params["shape"]
                loc = self.bm_params["loc"]
                scale = self.bm_params["scale"]
                p = confidence
                if abs(shape) < 1e-10:
                    var = loc - scale * np.log(-np.log(p))
                else:
                    var = loc - scale / shape * (1 - (-np.log(p)) ** (-shape))
                return abs(var)
            else:
                raise ValueError("Either POT or Block Maxima model must be fitted")
        elif method == "historical":
            var = -np.percentile(self.data, 100 * (1 - confidence))
            return abs(var)
        elif method == "normal":
            mean = np.mean(self.data)
            std = np.std(self.data)
            z_score = stats.norm.ppf(confidence)
            var = -(mean + z_score * std)
            return abs(var)
        else:
            raise ValueError("Method must be 'evt', 'historical', or 'normal'")

    def calculate_es(self, confidence: Any = 0.95, method: Any = "evt") -> float:
        """
        Calculate Expected Shortfall (ES) using EVT

        Args:
            confidence: Confidence level (default: 0.95 for 95% ES)
            method: Method to use ('evt', 'historical', 'normal')

        Returns:
            es: Expected Shortfall at specified confidence level
        """
        if self.data is None:
            raise ValueError("Model must be fitted before calculating ES")
        if method == "evt":
            if self.pot_params is not None:
                shape = self.pot_params["shape"]
                scale = self.pot_params["scale"]
                threshold = self.pot_params["threshold"]
                var = self.calculate_var(confidence, method="evt")
                if shape >= 1:
                    logger.warning("Shape parameter >= 1, ES is infinite")
                    es = var * 1.5
                else:
                    es = var / (1 - shape) + (scale - shape * abs(threshold)) / (
                        1 - shape
                    )
                return max(es, var * 1.01)
            elif self.bm_params is not None:
                var = self.calculate_var(confidence, method="evt")
                tail = self.data[self.data <= -var]
                if len(tail) > 0:
                    es = -np.mean(tail)
                else:
                    es = var * 1.25
                return max(es, var * 1.01)
            else:
                raise ValueError("Either POT or Block Maxima model must be fitted")
        elif method == "historical":
            var = self.calculate_var(confidence, method="historical")
            tail = self.data[self.data <= -var]
            if len(tail) > 0:
                es = -np.mean(tail)
            else:
                es = var * 1.25
            return max(es, var * 1.01)
        elif method == "normal":
            mean = np.mean(self.data)
            std = np.std(self.data)
            z_score = stats.norm.ppf(confidence)
            es = -(mean + std * stats.norm.pdf(z_score) / (1 - confidence))
            var = self.calculate_var(confidence, method="normal")
            return max(abs(es), var * 1.01)
        else:
            raise ValueError("Method must be 'evt', 'historical', or 'normal'")

    def generate_scenarios(
        self, n_scenarios: Any = 1000, method: Any = "evt", severity: Any = "extreme"
    ) -> np.ndarray:
        """
        Generate extreme scenarios based on fitted EVT model

        Args:
            n_scenarios: Number of scenarios to generate
            method: Method to use ('evt', 'historical', 'normal')
            severity: Severity of scenarios ('extreme', 'moderate', 'mixed')

        Returns:
            scenarios: Array of generated scenarios (negative = losses)
        """
        if self.data is None:
            raise ValueError("Model must be fitted before generating scenarios")
        if method == "evt":
            if self.pot_params is not None:
                shape = self.pot_params["shape"]
                scale = self.pot_params["scale"]
                threshold = self.pot_params["threshold"]
                if severity == "extreme":
                    severity_factor = 0.01
                elif severity == "moderate":
                    severity_factor = 0.05
                else:
                    severity_factor = 0.1
                u = np.random.uniform(0, severity_factor, n_scenarios)
                if abs(shape) < 1e-10:
                    scenarios = abs(threshold) + scale * np.log(
                        np.maximum(severity_factor, 1e-10) / np.maximum(u, 1e-10)
                    )
                else:
                    scenarios = abs(threshold) + scale / shape * (
                        (np.maximum(u, 1e-10) / severity_factor) ** shape - 1
                    )
                return -scenarios
            elif self.bm_params is not None:
                shape = self.bm_params["shape"]
                loc = self.bm_params["loc"]
                scale = self.bm_params["scale"]
                scenarios = stats.genextreme.rvs(
                    shape, loc=loc, scale=scale, size=n_scenarios
                )
                return -scenarios
            else:
                raise ValueError("Either POT or Block Maxima model must be fitted")
        elif method == "historical":
            indices = np.random.choice(len(self.data), n_scenarios)
            scenarios = self.data[indices].copy()
            if severity == "extreme":
                threshold_val = np.percentile(self.data, 5)
                extreme_indices = np.where(self.data <= threshold_val)[0]
                if len(extreme_indices) > 0:
                    n_extreme = min(n_scenarios // 2, len(extreme_indices))
                    chosen = np.random.choice(extreme_indices, n_extreme, replace=True)
                    scenarios[:n_extreme] = self.data[chosen]
            return scenarios
        elif method == "normal":
            mean = np.mean(self.data)
            std = np.std(self.data)
            if severity == "extreme":
                std *= 1.5
            elif severity == "moderate":
                std *= 1.2
            return np.random.normal(mean, std, n_scenarios)
        else:
            raise ValueError("Method must be 'evt', 'historical', or 'normal'")

    def simulate_extreme_scenarios(
        self, n_scenarios: Any = 100, confidence: Any = 0.95
    ) -> np.ndarray:
        """
        Simulate scenarios that breach the VaR threshold.

        Args:
            n_scenarios: Number of extreme scenarios
            confidence: Confidence level to define 'extreme'

        Returns:
            Array of loss values exceeding VaR
        """
        if self.data is None:
            raise ValueError("Model must be fitted before simulating scenarios")
        var = self.calculate_var(
            confidence, method="evt" if self.pot_params else "historical"
        )
        scenarios = []
        attempts = 0
        max_attempts = n_scenarios * 100
        while len(scenarios) < n_scenarios and attempts < max_attempts:
            batch = self.generate_scenarios(
                n_scenarios * 10,
                method="evt" if self.pot_params else "historical",
                severity="extreme",
            )
            extreme = batch[batch < -var]
            scenarios.extend((-extreme).tolist())
            attempts += n_scenarios * 10
        if len(scenarios) < n_scenarios:
            shortfall = n_scenarios - len(scenarios)
            scenarios.extend(
                [var * (1 + np.random.exponential(0.1)) for _ in range(shortfall)]
            )
        return np.array(scenarios[:n_scenarios])

    def tail_dependence(
        self,
        x: Any,
        y: Any,
        method: Any = "empirical",
        threshold_quantile: Any = 0.1,
    ) -> float:
        """Alias for calculate_tail_dependence for backward compatibility."""
        return self.calculate_tail_dependence(
            x, y, method=method, threshold_quantile=threshold_quantile
        )

    def calculate_tail_dependence(
        self, x: Any, y: Any, method: Any = "empirical", threshold_quantile: Any = 0.1
    ) -> float:
        """
        Calculate tail dependence between two return series

        Args:
            x: First return series
            y: Second return series
            method: Method to use ('empirical', 'copula')
            threshold_quantile: Quantile for threshold selection

        Returns:
            tail_dep: Tail dependence coefficient
        """
        x = np.array(x).flatten()
        y = np.array(y).flatten()
        if method == "empirical":
            threshold_x = np.percentile(x, threshold_quantile * 100)
            threshold_y = np.percentile(y, threshold_quantile * 100)
            joint_exceedances = np.sum((x <= threshold_x) & (y <= threshold_y))
            x_exceedances = np.sum(x <= threshold_x)
            tail_dep = joint_exceedances / x_exceedances if x_exceedances > 0 else 0.0
            return float(tail_dep)
        elif method == "copula":
            rho, _ = stats.spearmanr(x, y)
            df = 4
            tail_dep = 2 * stats.t.cdf(
                -np.sqrt((df + 1) * (1 - rho) / (1 + rho)), df + 1
            )
            return float(tail_dep)
        else:
            raise ValueError("Method must be 'empirical' or 'copula'")

    def plot_tail_distribution(
        self, confidence_levels: List[float] = [0.9, 0.95, 0.99, 0.999]
    ) -> plt.Figure:
        """Plot tail distribution with VaR and ES"""
        if self.data is None:
            raise ValueError("Model must be fitted before plotting")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(self.data, bins=50, density=True, alpha=0.5, label="Returns")
        x = np.linspace(min(self.data), max(self.data), 1000)
        ax.plot(
            x,
            stats.norm.pdf(x, np.mean(self.data), np.std(self.data)),
            "r--",
            label="Normal Distribution",
        )
        if self.pot_params is not None:
            shape = self.pot_params["shape"]
            scale = self.pot_params["scale"]
            threshold = self.pot_params["threshold"]
            x_tail = np.linspace(-max(abs(self.data)), -abs(threshold), 1000)
            y_tail = stats.genpareto.pdf(-x_tail - abs(threshold), shape, scale=scale)
            p_threshold = np.mean(self.data <= -abs(threshold))
            y_tail *= p_threshold
            ax.plot(-x_tail, y_tail, "g-", linewidth=2, label="EVT Tail Distribution")
        colors = ["b", "g", "r", "c", "m"]
        for i, conf in enumerate(confidence_levels):
            color = colors[i % len(colors)]
            try:
                var = self.calculate_var(conf, method="evt")
                es = self.calculate_es(conf, method="evt")
                ax.axvline(
                    -var,
                    color=color,
                    linestyle="--",
                    label=f"VaR ({conf * 100:.1f}%): {var:.4f}",
                )
                ax.axvline(
                    -es,
                    color=color,
                    linestyle=":",
                    label=f"ES ({conf * 100:.1f}%): {es:.4f}",
                )
            except Exception as e:
                logger.warning(f"Could not plot for confidence {conf}: {e}")
        ax.set_xlabel("Return")
        ax.set_ylabel("Density")
        ax.set_title("Tail Distribution with VaR and ES")
        ax.legend()
        return fig

    def plot_mean_excess(self) -> plt.Figure:
        """Plot mean excess function to help with threshold selection"""
        if self.data is None:
            raise ValueError("Data must be provided before plotting")
        fig, ax = plt.subplots(figsize=(10, 6))
        losses = -self.data
        losses_sorted = np.sort(losses[losses > 0])
        n_points = min(100, len(losses_sorted) // 2)
        if n_points < 2:
            logger.warning("Insufficient data for mean excess plot")
            return fig
        thresholds = np.linspace(0, np.percentile(losses_sorted, 95), n_points)
        mean_excess = np.zeros(n_points)
        for i, threshold in enumerate(thresholds):
            exceedances = losses_sorted[losses_sorted > threshold] - threshold
            mean_excess[i] = np.mean(exceedances) if len(exceedances) > 0 else np.nan
        ax.plot(thresholds, mean_excess, "b-", linewidth=2)
        if self.threshold is not None:
            ax.axvline(
                abs(self.threshold),
                color="r",
                linestyle="--",
                label=f"Current Threshold: {abs(self.threshold):.4f}",
            )
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Mean Excess")
        ax.set_title("Mean Excess Function")
        if self.threshold is not None:
            ax.legend()
        return fig

    def plot_return_level(
        self, return_periods: List[int] = [1, 2, 5, 10, 20, 50, 100]
    ) -> plt.Figure:
        """Plot return level plot"""
        if self.data is None:
            raise ValueError("Model must be fitted before plotting")
        fig, ax = plt.subplots(figsize=(10, 6))
        return_levels = []
        valid_periods = []
        for period in return_periods:
            try:
                confidence = 1 - 1 / period
                if 0 < confidence < 1:
                    level = self.calculate_var(confidence, method="evt")
                    return_levels.append(level)
                    valid_periods.append(period)
            except Exception as e:
                logger.warning(
                    f"Could not compute return level for period {period}: {e}"
                )
        if valid_periods:
            ax.semilogx(valid_periods, return_levels, "bo-", linewidth=2)
        ax.set_xlabel("Return Period (days)")
        ax.set_ylabel("Return Level (VaR)")
        ax.set_title("Return Level Plot")
        ax.grid(True, which="both", linestyle="--", linewidth=0.5)
        return fig


if __name__ == "__main__":
    np.random.seed(42)
    n_samples = 1000
    returns = np.random.standard_t(3, n_samples) * 0.02 + 0.001
    evt_model = ExtremeValueRisk()
    evt_model.fit_pot(returns, threshold_quantile=0.1)
    var_95 = evt_model.calculate_var(0.95, method="evt")
    es_95 = evt_model.calculate_es(0.95, method="evt")
    logger.info(f"EVT VaR (95%): {var_95:.4f}")
    logger.info(f"EVT ES (95%): {es_95:.4f}")
