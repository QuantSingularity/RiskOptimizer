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
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Any
from scipy import stats

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("extreme_value_theory")
warnings.filterwarnings("ignore")


class ExtremeValueRisk:
    """Extreme Value Theory Risk Model"""

    def __init__(self) -> None:
        """Initialize Extreme Value Risk Model"""
        self.data = None
        self.pot_params = None
        self.bm_params = None
        self.threshold = None
        self.threshold_quantile = None
        self.block_size = None

    def fit_pot(
        self, data: Any, threshold: Any = None, threshold_quantile: Any = 0.1
    ) -> Any:
        """
        Fit Peaks Over Threshold model with Generalized Pareto Distribution

        Args:
            data: Array-like of returns
            threshold: Explicit threshold value (optional)
            threshold_quantile: Quantile for threshold selection (default: 0.1)

        Returns:
            self: The fitted model
        """
        if isinstance(data, pd.Series) or isinstance(data, pd.DataFrame):
            self.data = data.values.flatten()
        else:
            self.data = np.array(data).flatten()
        if threshold is None:
            self.threshold = np.percentile(self.data, threshold_quantile * 100)
        else:
            self.threshold = threshold
        self.threshold_quantile = threshold_quantile
        exceedances = -self.data[self.data <= -self.threshold]
        if len(exceedances) < 10:
            logger.warning("Too few exceedances for reliable GPD fitting")
            shape = 0.2
            scale = np.std(self.data) * 0.5
        else:
            try:
                excess = exceedances - self.threshold
                shape, loc, scale = stats.genpareto.fit(excess)
                logger.info(
                    f"GPD fit: shape={shape:.4f}, scale={scale:.4f}, threshold={self.threshold:.4f}"
                )
            except:
                logger.warning("MLE fitting failed, using method of moments")
                excess = exceedances - self.threshold
                mean_excess = np.mean(excess)
                var_excess = np.var(excess)
                shape = 0.5 * (1 - mean_excess**2 / var_excess)
                scale = 0.5 * mean_excess * (1 + mean_excess**2 / var_excess)
        self.pot_params = {"shape": shape, "scale": scale, "threshold": self.threshold}
        return self

    def fit_block_maxima(self, data: Any, block_size: Any = 20) -> Any:
        """
        Fit Block Maxima model with Generalized Extreme Value Distribution

        Args:
            data: Array-like of returns
            block_size: Size of blocks for maxima extraction

        Returns:
            self: The fitted model
        """
        if isinstance(data, pd.Series) or isinstance(data, pd.DataFrame):
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
            scale = np.std(block_maxima)
        else:
            try:
                shape, loc, scale = stats.genextreme.fit(block_maxima)
                logger.info(
                    f"GEV fit: shape={shape:.4f}, loc={loc:.4f}, scale={scale:.4f}"
                )
            except:
                logger.warning("GEV fitting failed, using normal approximation")
                loc = np.mean(block_maxima)
                scale = np.std(block_maxima)
                shape = 0.1
        self.bm_params = {"shape": shape, "loc": loc, "scale": scale}
        return self

    def calculate_var(
        self, confidence: Any = 0.95, method: Any = "evt", return_period: Any = None
    ) -> Any:
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
                p_threshold = self.threshold_quantile
                p = 1 - confidence
                if abs(shape) < 1e-10:
                    var = threshold + scale * np.log(p_threshold / p)
                else:
                    var = threshold + scale / shape * ((p_threshold / p) ** shape - 1)
                return abs(var)
            elif self.bm_params is not None:
                shape = self.bm_params["shape"]
                loc = self.bm_params["loc"]
                scale = self.bm_params["scale"]
                p = confidence
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

    def calculate_es(self, confidence: Any = 0.95, method: Any = "evt") -> Any:
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
                    es = var / (1 - shape) + (scale - shape * threshold) / (1 - shape)
                return es
            elif self.bm_params is not None:
                var = self.calculate_var(confidence, method="evt")
                es = -np.mean(self.data[self.data <= -var])
                return es
            else:
                raise ValueError("Either POT or Block Maxima model must be fitted")
        elif method == "historical":
            var = self.calculate_var(confidence, method="historical")
            es = -np.mean(self.data[self.data <= -var])
            return es
        elif method == "normal":
            mean = np.mean(self.data)
            std = np.std(self.data)
            z_score = stats.norm.ppf(confidence)
            es = -(mean + std * stats.norm.pdf(z_score) / (1 - confidence))
            return es
        else:
            raise ValueError("Method must be 'evt', 'historical', or 'normal'")

    def generate_scenarios(
        self, n_scenarios: Any = 1000, method: Any = "evt", severity: Any = "extreme"
    ) -> Any:
        """
        Generate extreme scenarios based on fitted EVT model

        Args:
            n_scenarios: Number of scenarios to generate
            method: Method to use ('evt', 'historical', 'normal')
            severity: Severity of scenarios ('extreme', 'moderate', 'mixed')

        Returns:
            scenarios: Array of generated scenarios
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
                    scenarios = threshold + scale * np.log(u / severity_factor)
                else:
                    scenarios = threshold + scale / shape * (
                        (u / severity_factor) ** shape - 1
                    )
                scenarios = -scenarios
                return scenarios
            elif self.bm_params is not None:
                shape = self.bm_params["shape"]
                loc = self.bm_params["loc"]
                scale = self.bm_params["scale"]
                scenarios = stats.genextreme.rvs(
                    shape, loc=loc, scale=scale, size=n_scenarios
                )
                scenarios = -scenarios
                return scenarios
            else:
                raise ValueError("Either POT or Block Maxima model must be fitted")
        elif method == "historical":
            indices = np.random.choice(len(self.data), n_scenarios)
            scenarios = self.data[indices]
            if severity == "extreme":
                threshold = np.percentile(self.data, 5)
                extreme_indices = np.where(self.data <= threshold)[0]
                if len(extreme_indices) > 0:
                    extreme_indices = np.random.choice(
                        extreme_indices, n_scenarios // 2
                    )
                    scenarios[: n_scenarios // 2] = self.data[extreme_indices]
            return scenarios
        elif method == "normal":
            mean = np.mean(self.data)
            std = np.std(self.data)
            if severity == "extreme":
                std *= 1.5
            elif severity == "moderate":
                std *= 1.2
            scenarios = np.random.normal(mean, std, n_scenarios)
            return scenarios
        else:
            raise ValueError("Method must be 'evt', 'historical', or 'normal'")

    def calculate_tail_dependence(
        self, x: Any, y: Any, method: Any = "empirical", threshold_quantile: Any = 0.1
    ) -> Any:
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
            tail_dep = joint_exceedances / x_exceedances if x_exceedances > 0 else 0
            return tail_dep
        elif method == "copula":
            rho = stats.spearmanr(x, y)[0]
            df = 4
            tail_dep = 2 * stats.t.cdf(
                -np.sqrt((df + 1) * (1 - rho) / (1 + rho)), df + 1
            )
            return tail_dep
        else:
            raise ValueError("Method must be 'empirical' or 'copula'")

    def plot_tail_distribution(
        self, confidence_levels: Any = [0.9, 0.95, 0.99, 0.999]
    ) -> Any:
        """
        Plot tail distribution with VaR and ES

        Args:
            confidence_levels: List of confidence levels to plot

        Returns:
            fig: Matplotlib figure
        """
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
            x_tail = np.linspace(-max(self.data), -threshold, 1000)
            y_tail = stats.genpareto.pdf(-x_tail - threshold, shape, scale=scale)
            p_threshold = np.mean(self.data <= -threshold)
            y_tail *= p_threshold
            ax.plot(-x_tail, y_tail, "g-", linewidth=2, label="EVT Tail Distribution")
        colors = ["b", "g", "r", "c", "m"]
        for i, conf in enumerate(confidence_levels):
            color = colors[i % len(colors)]
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
        ax.set_xlabel("Return")
        ax.set_ylabel("Density")
        ax.set_title("Tail Distribution with VaR and ES")
        ax.legend()
        ax.set_xlim(left=-max(abs(self.data)), right=0)
        return fig

    def plot_mean_excess(self) -> Any:
        """
        Plot mean excess function to help with threshold selection

        Returns:
            fig: Matplotlib figure
        """
        if self.data is None:
            raise ValueError("Data must be provided before plotting")
        fig, ax = plt.subplots(figsize=(10, 6))
        losses = -self.data
        losses.sort()
        losses = losses[losses > 0]
        n_points = min(100, len(losses) // 2)
        thresholds = np.linspace(0, np.percentile(losses, 95), n_points)
        mean_excess = np.zeros(n_points)
        for i, threshold in enumerate(thresholds):
            exceedances = losses[losses > threshold] - threshold
            mean_excess[i] = np.mean(exceedances) if len(exceedances) > 0 else np.nan
        ax.plot(thresholds, mean_excess, "b-", linewidth=2)
        if self.threshold is not None:
            ax.axvline(
                -self.threshold,
                color="r",
                linestyle="--",
                label=f"Current Threshold: {-self.threshold:.4f}",
            )
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Mean Excess")
        ax.set_title("Mean Excess Function")
        if self.threshold is not None:
            ax.legend()
        return fig

    def plot_return_level(
        self, return_periods: Any = [1, 2, 5, 10, 20, 50, 100]
    ) -> Any:
        """
        Plot return level plot

        Args:
            return_periods: List of return periods in days

        Returns:
            fig: Matplotlib figure
        """
        if self.data is None:
            raise ValueError("Model must be fitted before plotting")
        fig, ax = plt.subplots(figsize=(10, 6))
        return_levels = np.zeros(len(return_periods))
        for i, period in enumerate(return_periods):
            confidence = 1 - 1 / period
            return_levels[i] = self.calculate_var(confidence, method="evt")
        ax.semilogx(return_periods, return_levels, "bo-", linewidth=2)
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
    var_hist = evt_model.calculate_var(0.95, method="historical")
    var_norm = evt_model.calculate_var(0.95, method="normal")
    logger.info(f"Historical VaR (95%): {var_hist:.4f}")
    logger.info(f"Normal VaR (95%): {var_norm:.4f}")
    scenarios = evt_model.generate_scenarios(n_scenarios=1000, method="evt")
    logger.info(f"Mean scenario: {np.mean(scenarios):.4f}")
    logger.info(f"Min scenario: {np.min(scenarios):.4f}")
    logger.info(f"Max scenario: {np.max(scenarios):.4f}")
    fig = evt_model.plot_tail_distribution()
    plt.tight_layout()
    plt.savefig("evt_tail_distribution.png")
    fig = evt_model.plot_mean_excess()
    plt.tight_layout()
    plt.savefig("evt_mean_excess.png")
    fig = evt_model.plot_return_level()
    plt.tight_layout()
    plt.savefig("evt_return_level.png")
