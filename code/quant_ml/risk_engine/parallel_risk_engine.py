"""
Parallel Risk Calculation Engine for RiskOptimizer

This module provides optimized risk calculation capabilities using parallel processing:
1. Parallel Monte Carlo simulation for risk metrics
2. Parallel portfolio optimization
3. Parallel batch risk calculation across multiple models
4. Parallel stress testing and scenario analysis
5. Parallel backtesting of risk models
6. Parallel sensitivity analysis
7. Parallel risk decomposition
"""

import logging
import multiprocessing as mp
import time
import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import psutil
from joblib import Parallel, delayed
from scipy import stats

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("parallel_risk_engine")
warnings.filterwarnings("ignore")


class ParallelRiskEngine:
    """Parallel Risk Calculation Engine"""

    def __init__(
        self,
        n_jobs: Optional[int] = None,
        backend: str = "multiprocessing",
        verbose: int = 0,
    ) -> None:
        """
        Initialize Parallel Risk Engine

        Args:
            n_jobs: Number of jobs to run in parallel (None = use all available cores)
            backend: Backend for parallel processing ("multiprocessing", "threading", "loky")
            verbose: Verbosity level (0 = silent, 1 = progress bar, 10 = debug)
        """
        if n_jobs is None:
            self.n_jobs = mp.cpu_count()
        else:
            self.n_jobs = n_jobs
        self.backend = backend
        self.verbose = verbose
        logger.info(
            f"Initialized ParallelRiskEngine with {self.n_jobs} jobs using {backend} backend"
        )

    def parallel_monte_carlo(
        self,
        risk_model: object,
        weights: object,
        n_scenarios: int = 10000,
        confidence_levels: Optional[List[float]] = None,
    ) -> Dict[str, object]:
        """
        Run Monte Carlo simulation in parallel

        Args:
            risk_model: Risk model with generate_scenarios method
            weights: Portfolio weights
            n_scenarios: Number of scenarios to generate
            confidence_levels: List of confidence levels for VaR and ES

        Returns:
            results: Dictionary of simulation results
        """
        if confidence_levels is None:
            confidence_levels = [0.95, 0.99]
        logger.info(
            f"Running parallel Monte Carlo simulation with {n_scenarios} scenarios"
        )
        start_time = time.time()
        batch_size = max(100, n_scenarios // (self.n_jobs * 10))
        n_batches = n_scenarios // batch_size
        scenario_batches = Parallel(
            n_jobs=self.n_jobs, backend=self.backend, verbose=self.verbose
        )(
            delayed(self._generate_scenarios_batch)(risk_model, batch_size)
            for _ in range(n_batches)
        )
        all_scenarios = pd.concat(scenario_batches)
        if isinstance(weights, dict):
            weight_array = np.zeros(len(risk_model.asset_names))
            for i, asset in enumerate(risk_model.asset_names):
                if asset in weights:
                    weight_array[i] = weights[asset]
            weights = weight_array
        portfolio_returns = all_scenarios.dot(weights)
        portfolio_metrics = {
            "expected_return": portfolio_returns.mean(),
            "volatility": portfolio_returns.std(),
            "skewness": stats.skew(portfolio_returns),
            "kurtosis": stats.kurtosis(portfolio_returns),
            "min_return": portfolio_returns.min(),
            "max_return": portfolio_returns.max(),
        }
        risk_metrics = {}
        for conf in confidence_levels:
            var = -np.percentile(portfolio_returns, 100 * (1 - conf))
            es = -portfolio_returns[portfolio_returns <= -var].mean()
            risk_metrics[f"var_{int(conf * 100)}"] = var
            risk_metrics[f"es_{int(conf * 100)}"] = es
        time_taken = time.time() - start_time
        logger.info(f"Monte Carlo simulation completed in {time_taken:.2f} seconds")
        return {
            "portfolio_metrics": portfolio_metrics,
            "risk_metrics": risk_metrics,
            "time_taken": time_taken,
        }

    def _generate_scenarios_batch(
        self, risk_model: object, batch_size: object
    ) -> object:
        """
        Generate a batch of scenarios

        Args:
            risk_model: Risk model with generate_scenarios method
            batch_size: Number of scenarios to generate

        Returns:
            scenarios: DataFrame of generated scenarios
        """
        return risk_model.generate_scenarios(batch_size)

    def parallel_portfolio_optimization(
        self,
        returns: object,
        risk_model: object = "markowitz",
        n_portfolios: int = 1000,
        risk_free_rate: object = 0.02,
        target_return: object = None,
        target_risk: object = None,
    ) -> Dict[str, object]:
        """
        Run portfolio optimization in parallel

        Args:
            returns: DataFrame of asset returns
            risk_model: Risk model to use ("markowitz", "cvar", "mad")
            n_portfolios: Number of portfolios to generate
            risk_free_rate: Risk-free rate (annualized)
            target_return: Target return for minimum risk portfolio (optional)
            target_risk: Target risk for maximum return portfolio (optional)

        Returns:
            results: Dictionary of optimization results
        """
        logger.info(
            f"Running parallel portfolio optimization with {n_portfolios} portfolios"
        )
        start_time = time.time()
        assets = returns.columns
        batch_size = max(100, n_portfolios // (self.n_jobs * 10))
        n_batches = n_portfolios // batch_size
        portfolio_batches = Parallel(
            n_jobs=self.n_jobs, backend=self.backend, verbose=self.verbose
        )(
            delayed(self._generate_portfolios_batch)(
                returns, risk_model, batch_size, risk_free_rate
            )
            for _ in range(n_batches)
        )
        all_portfolios = []
        for batch in portfolio_batches:
            all_portfolios.extend(batch)
        portfolios_df = pd.DataFrame(all_portfolios)
        required_cols = ["return", "volatility", "sharpe_ratio"]
        if not all(col in portfolios_df.columns for col in required_cols):
            logger.error("Missing required columns in generated portfolios DataFrame")
            return None
        efficient_frontier = self._find_efficient_frontier(portfolios_df)
        max_sharpe_idx = portfolios_df["sharpe_ratio"].idxmax()
        max_sharpe_portfolio = {
            "weights": dict(zip(assets, portfolios_df.loc[max_sharpe_idx, assets])),
            "return": portfolios_df.loc[max_sharpe_idx, "return"],
            "volatility": portfolios_df.loc[max_sharpe_idx, "volatility"],
            "sharpe_ratio": portfolios_df.loc[max_sharpe_idx, "sharpe_ratio"],
        }
        min_vol_idx = portfolios_df["volatility"].idxmin()
        min_volatility_portfolio = {
            "weights": dict(zip(assets, portfolios_df.loc[min_vol_idx, assets])),
            "return": portfolios_df.loc[min_vol_idx, "return"],
            "volatility": portfolios_df.loc[min_vol_idx, "volatility"],
            "sharpe_ratio": portfolios_df.loc[min_vol_idx, "sharpe_ratio"],
        }
        target_portfolios = {}
        if target_return is not None:
            target_portfolios["target_return"] = self._find_target_return_portfolio(
                portfolios_df, target_return, assets
            )
        if target_risk is not None:
            target_portfolios["target_risk"] = self._find_target_risk_portfolio(
                portfolios_df, target_risk, assets
            )
        time_taken = time.time() - start_time
        logger.info(f"Portfolio optimization completed in {time_taken:.2f} seconds")
        return {
            "efficient_frontier": efficient_frontier,
            "max_sharpe_portfolio": max_sharpe_portfolio,
            "min_volatility_portfolio": min_volatility_portfolio,
            "target_portfolios": target_portfolios,
            "all_portfolios": portfolios_df,
            "time_taken": time_taken,
        }

    def _generate_portfolios_batch(
        self,
        returns: object,
        risk_model: object,
        batch_size: object,
        risk_free_rate: object,
    ) -> object:
        """Generate a batch of random portfolios."""
        assets = returns.columns
        n_assets = len(assets)
        if isinstance(returns.index, pd.DatetimeIndex):
            if len(returns) >= 2:
                freq = pd.infer_freq(returns.index)
                if freq and "D" in freq:
                    annualization_factor = 252
                elif freq and "W" in freq:
                    annualization_factor = 52
                elif freq and "M" in freq:
                    annualization_factor = 12
                else:
                    annualization_factor = 252
            else:
                annualization_factor = 252
        else:
            annualization_factor = 252

        mean_returns = returns.mean() * annualization_factor
        cov_matrix = returns.cov() * annualization_factor
        portfolios = []
        for _ in range(batch_size):
            weights = np.random.random(n_assets)
            weights /= np.sum(weights)
            portfolio_return = np.sum(mean_returns * weights)
            portfolio_volatility = np.sqrt(
                np.dot(weights.T, np.dot(cov_matrix, weights))
            )
            if risk_model == "markowitz":
                risk_metric = portfolio_volatility
            elif risk_model == "cvar":
                portfolio_returns = returns.dot(weights)
                var_95 = -np.percentile(portfolio_returns, 5)
                cvar_95 = -portfolio_returns[portfolio_returns <= -var_95].mean()
                risk_metric = cvar_95 * np.sqrt(annualization_factor)
            elif risk_model == "mad":
                portfolio_returns = returns.dot(weights)
                mad = np.mean(np.abs(portfolio_returns - portfolio_returns.mean()))
                risk_metric = mad * np.sqrt(annualization_factor)
            else:
                risk_metric = portfolio_volatility

            sharpe_ratio = (
                (portfolio_return - risk_free_rate) / portfolio_volatility
                if portfolio_volatility > 0
                else 0
            )
            portfolio = {
                **dict(zip(assets, weights)),
                "return": portfolio_return,
                "volatility": portfolio_volatility,
                "risk_metric": risk_metric,
                "sharpe_ratio": sharpe_ratio,
            }
            portfolios.append(portfolio)
        return portfolios

    def _find_efficient_frontier(
        self, portfolios_df: object, n_points: int = 100
    ) -> object:
        """Find the efficient frontier from a set of portfolios."""
        sorted_portfolios = portfolios_df.sort_values("return")
        efficient_frontier = []
        min_return = sorted_portfolios["return"].min()
        max_return = sorted_portfolios["return"].max()
        return_range = np.linspace(min_return, max_return, n_points)
        for target_return in return_range:
            similar_return = sorted_portfolios[
                (sorted_portfolios["return"] >= target_return - 0.001)
                & (sorted_portfolios["return"] <= target_return + 0.001)
            ]
            if len(similar_return) > 0:
                min_risk_idx = similar_return["volatility"].idxmin()
                efficient_frontier.append(sorted_portfolios.loc[min_risk_idx])
        return pd.DataFrame(efficient_frontier)

    def _find_target_return_portfolio(
        self, portfolios_df: object, target_return: object, assets: object
    ) -> object:
        """Find portfolio with target return."""
        closest_idx = (portfolios_df["return"] - target_return).abs().idxmin()
        return {
            "weights": dict(zip(assets, portfolios_df.loc[closest_idx, assets])),
            "return": portfolios_df.loc[closest_idx, "return"],
            "volatility": portfolios_df.loc[closest_idx, "volatility"],
            "sharpe_ratio": portfolios_df.loc[closest_idx, "sharpe_ratio"],
        }

    def _find_target_risk_portfolio(
        self, portfolios_df: object, target_risk: object, assets: object
    ) -> object:
        """Find portfolio with target risk."""
        closest_idx = (portfolios_df["volatility"] - target_risk).abs().idxmin()
        return {
            "weights": dict(zip(assets, portfolios_df.loc[closest_idx, assets])),
            "return": portfolios_df.loc[closest_idx, "return"],
            "volatility": portfolios_df.loc[closest_idx, "volatility"],
            "sharpe_ratio": portfolios_df.loc[closest_idx, "sharpe_ratio"],
        }

    def parallel_batch_risk_calculation(
        self,
        returns: object,
        risk_models: Optional[List[str]] = None,
        confidence_levels: Optional[List[float]] = None,
    ) -> Dict[str, object]:
        """
        Run batch risk calculation in parallel

        Args:
            returns: Series or DataFrame of returns
            risk_models: List of risk models to use
            confidence_levels: List of confidence levels for VaR and ES

        Returns:
            results: Dictionary of risk calculation results
        """
        if risk_models is None:
            risk_models = ["parametric", "historical", "evt"]
        if confidence_levels is None:
            confidence_levels = [0.95, 0.99]
        logger.info(
            f"Running parallel batch risk calculation with {len(risk_models)} models"
        )
        start_time = time.time()
        if isinstance(returns, pd.DataFrame) and returns.shape[1] == 1:
            returns = returns.iloc[:, 0]
        risk_results = Parallel(
            n_jobs=self.n_jobs, backend=self.backend, verbose=self.verbose
        )(
            delayed(self._calculate_risk_metrics)(returns, model, confidence_levels)
            for model in risk_models
        )
        risk_metrics = {}
        for model, result in zip(risk_models, risk_results):
            risk_metrics[model] = result
        time_taken = time.time() - start_time
        logger.info(f"Batch risk calculation completed in {time_taken:.2f} seconds")
        return {"risk_metrics": risk_metrics, "time_taken": time_taken}

    def _calculate_risk_metrics(
        self, returns: object, model: object, confidence_levels: object
    ) -> object:
        """
        Calculate risk metrics for a specific model.

        Args:
            returns: Series or DataFrame of returns
            model: Risk model to use
            confidence_levels: List of confidence levels

        Returns:
            metrics: Dictionary of risk metrics
        """
        metrics = {}
        if isinstance(returns, (pd.Series, pd.DataFrame)):
            returns_array = returns.values
        else:
            returns_array = returns

        for conf in confidence_levels:
            if model == "parametric":
                mean = np.mean(returns_array)
                std = np.std(returns_array)
                # FIX: use ppf(1 - conf) so z_score is negative (left-tail), giving
                # var = -(mean + z_neg * std) = -mean + |z| * std  (positive VaR)
                z_score = stats.norm.ppf(1 - conf)
                var = -(mean + z_score * std)
                es = max(0.0, -(mean - std * stats.norm.pdf(-z_score) / (1 - conf)))
            elif model == "historical":
                var = -np.percentile(returns_array, 100 * (1 - conf))
                tail = returns_array[returns_array <= -var]
                es = -np.mean(tail) if len(tail) > 0 else var
            elif model == "evt":
                try:
                    from risk_models.extreme_value_theory import ExtremeValueRisk

                    evt_model = ExtremeValueRisk()
                    evt_model.fit_pot(returns_array, threshold_quantile=0.1)
                    var = evt_model.calculate_var(conf, method="evt")
                    es = evt_model.calculate_es(conf)
                except ImportError:
                    var = -np.percentile(returns_array, 100 * (1 - conf))
                    tail = returns_array[returns_array <= -var]
                    es = -np.mean(tail) if len(tail) > 0 else var
            else:
                var = -np.percentile(returns_array, 100 * (1 - conf))
                tail = returns_array[returns_array <= -var]
                es = -np.mean(tail) if len(tail) > 0 else var

            metrics[f"var_{int(conf * 100)}"] = max(0, var)
            metrics[f"es_{int(conf * 100)}"] = max(0, es)
        return metrics

    def parallel_stress_testing(
        self,
        returns: object,
        weights: object,
        predefined_scenarios: object = None,
        n_custom_scenarios: int = 100,
    ) -> Dict[str, object]:
        """
        Run stress testing in parallel

        Args:
            returns: DataFrame of asset returns
            weights: Portfolio weights
            predefined_scenarios: Dictionary of predefined scenarios
            n_custom_scenarios: Number of custom scenarios to generate

        Returns:
            results: Dictionary of stress testing results
        """
        logger.info(
            f"Running parallel stress testing with {n_custom_scenarios} custom scenarios"
        )
        start_time = time.time()
        if isinstance(weights, dict):
            assets = returns.columns
            weight_array = np.zeros(len(assets))
            for i, asset in enumerate(assets):
                if asset in weights:
                    weight_array[i] = weights[asset]
            weights = weight_array

        if predefined_scenarios is None:
            predefined_scenarios = {
                "market_crash": {
                    "description": "Market crash scenario",
                    "shocks": {"all": -0.15},
                },
                "interest_rate_spike": {
                    "description": "Interest rate spike",
                    "shocks": {"bonds": -0.05, "equities": -0.03},
                },
                "commodity_shock": {
                    "description": "Commodity price shock",
                    "shocks": {"commodities": -0.1, "energy": -0.15},
                },
                "currency_crisis": {
                    "description": "Currency crisis",
                    "shocks": {"emerging_markets": -0.12, "currencies": -0.08},
                },
                "liquidity_crunch": {
                    "description": "Liquidity crunch",
                    "shocks": {"credit": -0.08, "real_estate": -0.1},
                },
            }

        predefined_results = Parallel(
            n_jobs=self.n_jobs, backend=self.backend, verbose=self.verbose
        )(
            delayed(self._run_predefined_scenario)(
                returns, weights, scenario_name, scenario
            )
            for scenario_name, scenario in predefined_scenarios.items()
        )
        predefined_scenario_results = {
            name: result
            for name, result in zip(predefined_scenarios.keys(), predefined_results)
        }

        custom_results = Parallel(
            n_jobs=self.n_jobs, backend=self.backend, verbose=self.verbose
        )(
            delayed(self._generate_custom_scenario)(returns, weights)
            for _ in range(n_custom_scenarios)
        )
        custom_returns = [result["portfolio_return"] for result in custom_results]
        custom_vars = [result["var_95"] for result in custom_results]
        custom_summary = {
            "count": n_custom_scenarios,
            "avg_return": np.mean(custom_returns),
            "min_return": np.min(custom_returns),
            "max_return": np.max(custom_returns),
            "std_return": np.std(custom_returns),
            "avg_var_95": np.mean(custom_vars),
            "max_var_95": np.max(custom_vars),
        }
        worst_return_idx = int(np.argmin(custom_returns))
        worst_var_idx = int(np.argmax(custom_vars))
        worst_case = {
            "worst_return": custom_results[worst_return_idx],
            "worst_var": custom_results[worst_var_idx],
        }
        time_taken = time.time() - start_time
        logger.info(f"Stress testing completed in {time_taken:.2f} seconds")
        return {
            "predefined_scenarios": predefined_scenario_results,
            "custom_scenarios_summary": custom_summary,
            "worst_case_scenarios": worst_case,
            "time_taken": time_taken,
        }

    def _run_predefined_scenario(
        self, returns: object, weights: object, scenario_name: object, scenario: object
    ) -> object:
        """Run a predefined stress scenario."""
        shocked_returns = returns.copy()
        for asset_class, shock in scenario["shocks"].items():
            if asset_class == "all":
                shocked_returns = shocked_returns + shock
            else:
                for col in shocked_returns.columns:
                    if asset_class.lower() in col.lower():
                        shocked_returns[col] = shocked_returns[col] + shock
        portfolio_return = np.dot(shocked_returns.mean(), weights)
        portfolio_returns = shocked_returns.dot(weights)
        var_95 = -np.percentile(portfolio_returns, 5)
        var_99 = -np.percentile(portfolio_returns, 1)
        tail_95 = portfolio_returns[portfolio_returns <= -var_95]
        tail_99 = portfolio_returns[portfolio_returns <= -var_99]
        es_95 = -tail_95.mean() if len(tail_95) > 0 else var_95
        es_99 = -tail_99.mean() if len(tail_99) > 0 else var_99
        return {
            "scenario_name": scenario_name,
            "description": scenario["description"],
            "shocks": scenario["shocks"],
            "portfolio_return": portfolio_return,
            "var_95": var_95,
            "var_99": var_99,
            "es_95": es_95,
            "es_99": es_99,
        }

    def _generate_custom_scenario(self, returns: object, weights: object) -> object:
        """Generate a custom stress scenario."""
        cov_matrix = returns.cov()
        shock_factors = np.random.normal(0, 1, len(returns.columns))
        chol_decomp = np.linalg.cholesky(cov_matrix)
        shocks = np.dot(chol_decomp, shock_factors) * 3
        shocked_returns = returns.copy()
        for i, col in enumerate(shocked_returns.columns):
            shocked_returns[col] = shocked_returns[col] + shocks[i]
        portfolio_return = np.dot(shocked_returns.mean(), weights)
        portfolio_returns = shocked_returns.dot(weights)
        var_95 = -np.percentile(portfolio_returns, 5)
        var_99 = -np.percentile(portfolio_returns, 1)
        tail_95 = portfolio_returns[portfolio_returns <= -var_95]
        tail_99 = portfolio_returns[portfolio_returns <= -var_99]
        es_95 = -tail_95.mean() if len(tail_95) > 0 else var_95
        es_99 = -tail_99.mean() if len(tail_99) > 0 else var_99
        return {
            "scenario_type": "custom",
            "shocks": dict(zip(returns.columns, shocks)),
            "portfolio_return": portfolio_return,
            "var_95": var_95,
            "var_99": var_99,
            "es_95": es_95,
            "es_99": es_99,
        }

    def parallel_backtest(
        self,
        returns: object,
        risk_models: Optional[List[str]] = None,
        confidence_level: float = 0.95,
        window_size: int = 252,
        step_size: int = 20,
    ) -> Dict[str, object]:
        """
        Run backtesting of risk models in parallel.

        Args:
            returns: Series or DataFrame of returns
            risk_models: List of risk models to use
            confidence_level: Confidence level for VaR
            window_size: Size of rolling window
            step_size: Step size for rolling window

        Returns:
            results: Dictionary of backtesting results
        """
        if risk_models is None:
            risk_models = ["parametric", "historical", "evt"]
        logger.info(f"Running parallel backtesting with window size {window_size}")
        start_time = time.time()
        if isinstance(returns, pd.DataFrame) and returns.shape[1] == 1:
            returns = returns.iloc[:, 0]
        n_returns = len(returns)
        n_windows = (n_returns - window_size) // step_size + 1
        backtest_results = Parallel(
            n_jobs=self.n_jobs, backend=self.backend, verbose=self.verbose
        )(
            delayed(self._run_backtest_window)(
                returns, i, window_size, step_size, risk_models, confidence_level
            )
            for i in range(n_windows)
        )
        windows = []
        breaches = {model: 0 for model in risk_models}
        for result in backtest_results:
            windows.append(result)
            for model in risk_models:
                if result[f"{model}_breach"]:
                    breaches[model] += 1
        expected_breach_rate = 1 - confidence_level
        summary = {}
        for model in risk_models:
            breach_rate = breaches[model] / n_windows
            breach_ratio = breach_rate / expected_breach_rate
            summary[model] = {
                "breaches": breaches[model],
                "total": n_windows,
                "breach_rate": breach_rate,
                "expected_breach_rate": expected_breach_rate,
                "breach_ratio": breach_ratio,
            }
        time_taken = time.time() - start_time
        logger.info(f"Backtesting completed in {time_taken:.2f} seconds")
        return {"summary": summary, "windows": windows, "time_taken": time_taken}

    def _run_backtest_window(
        self,
        returns: object,
        window_idx: object,
        window_size: object,
        step_size: object,
        risk_models: object,
        confidence_level: object,
    ) -> object:
        """Run backtest for a specific window."""
        start_idx = window_idx * step_size
        end_idx = start_idx + window_size
        test_idx = end_idx
        window_returns = returns.iloc[start_idx:end_idx]
        test_return_value = np.nan
        if test_idx < len(returns):
            test_return_value = returns.iloc[test_idx]
            if isinstance(test_return_value, (pd.Series, pd.DataFrame)):
                test_return_value = test_return_value.iloc[0]
        result = {
            "window_idx": window_idx,
            "start_idx": start_idx,
            "end_idx": end_idx,
            "test_idx": test_idx,
            "test_return": test_return_value,
        }
        for model in risk_models:
            if model == "parametric":
                mean = np.mean(window_returns)
                std = np.std(window_returns)
                # consistent sign with _calculate_risk_metrics
                z_score = stats.norm.ppf(1 - confidence_level)
                var = -(mean + z_score * std)
            elif model == "historical":
                var = -np.percentile(window_returns, 100 * (1 - confidence_level))
            elif model == "evt":
                try:
                    from risk_models.extreme_value_theory import ExtremeValueRisk

                    evt_model = ExtremeValueRisk()
                    evt_model.fit_pot(window_returns, threshold_quantile=0.1)
                    var = evt_model.calculate_var(confidence_level, method="evt")
                except ImportError:
                    var = -np.percentile(window_returns, 100 * (1 - confidence_level))
            else:
                var = -np.percentile(window_returns, 100 * (1 - confidence_level))

            breach = False
            if not np.isnan(test_return_value):
                breach = test_return_value < -var
            result[f"{model}_var"] = var
            result[f"{model}_breach"] = breach
        return result

    def parallel_sensitivity_analysis(
        self,
        returns: object,
        weights: object,
        shock_range: object = (-0.1, 0.1),
        n_points: int = 10,
    ) -> Any:
        """
        Run sensitivity analysis in parallel.

        Args:
            returns: DataFrame of asset returns
            weights: Portfolio weights
            shock_range: Range of shocks to apply (min, max)
            n_points: Number of points in the shock range

        Returns:
            results: Dictionary of sensitivity analysis results
        """
        logger.info(f"Running parallel sensitivity analysis with {n_points} points")
        start_time = time.time()
        if isinstance(weights, np.ndarray):
            weights = dict(zip(returns.columns, weights))
        shock_points = np.linspace(shock_range[0], shock_range[1], n_points)
        factor_results = {}
        sensitivities = {}
        for factor in returns.columns:
            factor_result = self._analyze_factor_sensitivity(
                returns, weights, factor, shock_points
            )
            factor_results[factor] = factor_result
            denom = shock_points[-1] - shock_points[0]
            if abs(denom) > 1e-10:
                return_sensitivity = (
                    factor_result["portfolio_returns"][-1]
                    - factor_result["portfolio_returns"][0]
                ) / denom
                var_sensitivity = (
                    factor_result["var_95"][-1] - factor_result["var_95"][0]
                ) / denom
            else:
                return_sensitivity = 0.0
                var_sensitivity = 0.0
            sensitivities[factor] = {
                "return_sensitivity": return_sensitivity,
                "var_sensitivity": var_sensitivity,
            }
        time_taken = time.time() - start_time
        logger.info(f"Sensitivity analysis completed in {time_taken:.2f} seconds")
        return {
            "factor_results": factor_results,
            "sensitivities": sensitivities,
            "time_taken": time_taken,
        }

    def _analyze_factor_sensitivity(
        self, returns: object, weights: object, factor: object, shock_points: object
    ) -> object:
        """Analyze sensitivity to a specific factor."""
        n_points = len(shock_points)
        portfolio_returns = np.zeros(n_points)
        portfolio_volatilities = np.zeros(n_points)
        var_95 = np.zeros(n_points)
        es_95 = np.zeros(n_points)
        for i, shock in enumerate(shock_points):
            shocked_returns = returns.copy()
            shocked_returns[factor] = shocked_returns[factor] + shock
            portfolio_return = 0.0
            portfolio_volatility = 0.0
            portfolio_rets = pd.Series(
                np.zeros(len(shocked_returns)), index=shocked_returns.index
            )
            for asset, weight in weights.items():
                if asset in shocked_returns.columns:
                    portfolio_return += shocked_returns[asset].mean() * weight
                    portfolio_volatility += shocked_returns[asset].std() * weight
                    portfolio_rets += shocked_returns[asset] * weight
            var = -np.percentile(portfolio_rets, 5)
            tail = portfolio_rets[portfolio_rets <= -var]
            es = -tail.mean() if len(tail) > 0 else var
            portfolio_returns[i] = portfolio_return
            portfolio_volatilities[i] = portfolio_volatility
            var_95[i] = var
            es_95[i] = es
        return {
            "factor": factor,
            "shocks": shock_points,
            "portfolio_returns": portfolio_returns,
            "portfolio_volatilities": portfolio_volatilities,
            "var_95": var_95,
            "es_95": es_95,
        }

    def parallel_risk_decomposition(
        self, returns: object, weights: object, risk_measure: str = "volatility"
    ) -> Dict[str, object]:
        """
        Run risk decomposition in parallel.

        Args:
            returns: DataFrame of asset returns
            weights: Portfolio weights
            risk_measure: Risk measure to decompose ("volatility", "var", "es")

        Returns:
            results: Dictionary of risk decomposition results
        """
        logger.info(f"Running parallel risk decomposition for {risk_measure}")
        start_time = time.time()
        if isinstance(weights, np.ndarray):
            weights = dict(zip(returns.columns, weights))

        if risk_measure == "volatility":
            cov_matrix = returns.cov()
            weight_array = np.array(
                [weights.get(asset, 0) for asset in returns.columns]
            )
            portfolio_risk = np.sqrt(
                np.dot(weight_array.T, np.dot(cov_matrix, weight_array))
            )
            marginal_contributions = np.dot(cov_matrix, weight_array) / portfolio_risk
            component_contributions = weight_array * marginal_contributions
            percentage_contributions = component_contributions / portfolio_risk

        elif risk_measure in ("var", "es"):
            portfolio_returns_series = sum(
                returns[asset] * weights.get(asset, 0)
                for asset in returns.columns
                if asset in returns.columns
            )
            if risk_measure == "var":
                portfolio_risk = -np.percentile(portfolio_returns_series, 5)
            else:
                var_95 = -np.percentile(portfolio_returns_series, 5)
                tail = portfolio_returns_series[portfolio_returns_series <= -var_95]
                portfolio_risk = -tail.mean() if len(tail) > 0 else var_95

            contributions = Parallel(
                n_jobs=self.n_jobs, backend=self.backend, verbose=self.verbose
            )(
                delayed(self._calculate_risk_contribution)(
                    returns, weights, asset, risk_measure
                )
                for asset in returns.columns
            )
            marginal_contributions = np.array(
                [c["marginal_contribution"] for c in contributions]
            )
            component_contributions = np.array(
                [c["component_contribution"] for c in contributions]
            )
            percentage_contributions = np.array(
                [c["percentage_contribution"] for c in contributions]
            )
        else:
            raise ValueError(f"Unsupported risk measure: {risk_measure}")

        contributions_list = []
        for i, asset in enumerate(returns.columns):
            contributions_list.append(
                {
                    "asset": asset,
                    "weight": weights.get(asset, 0),
                    "marginal_contribution": float(marginal_contributions[i]),
                    "component_contribution": float(component_contributions[i]),
                    "percentage_contribution": float(percentage_contributions[i]),
                }
            )
        contributions_list.sort(
            key=lambda x: x["percentage_contribution"], reverse=True
        )
        time_taken = time.time() - start_time
        logger.info(f"Risk decomposition completed in {time_taken:.2f} seconds")
        return {
            "risk_measure": risk_measure,
            "portfolio_risk": float(portfolio_risk),
            "total_risk": float(portfolio_risk),
            "contributions": contributions_list,
            "component_contributions": [
                c["component_contribution"] for c in contributions_list
            ],
            "percentage_contributions": [
                c["percentage_contribution"] for c in contributions_list
            ],
            "time_taken": time_taken,
        }

    def _calculate_risk_contribution(
        self, returns: object, weights: object, asset: object, risk_measure: object
    ) -> object:
        """Calculate risk contribution for a specific asset."""
        portfolio_returns = sum(
            returns[a] * weights.get(a, 0) for a in weights if a in returns.columns
        )
        if risk_measure == "var":
            base_risk = -np.percentile(portfolio_returns, 5)
        else:
            var_95 = -np.percentile(portfolio_returns, 5)
            tail = portfolio_returns[portfolio_returns <= -var_95]
            base_risk = -tail.mean() if len(tail) > 0 else var_95

        delta = 0.0001
        modified_weights = weights.copy()
        modified_weights[asset] = weights.get(asset, 0) + delta
        total_weight = sum(modified_weights.values())
        if total_weight > 0:
            modified_weights = {
                a: v / total_weight for a, v in modified_weights.items()
            }

        modified_portfolio_returns = sum(
            returns[a] * modified_weights.get(a, 0)
            for a in modified_weights
            if a in returns.columns
        )
        if risk_measure == "var":
            modified_risk = -np.percentile(modified_portfolio_returns, 5)
        else:
            var_95 = -np.percentile(modified_portfolio_returns, 5)
            tail = modified_portfolio_returns[modified_portfolio_returns <= -var_95]
            modified_risk = -tail.mean() if len(tail) > 0 else var_95

        marginal_contribution = (modified_risk - base_risk) / delta
        component_contribution = weights.get(asset, 0) * marginal_contribution
        percentage_contribution = (
            component_contribution / base_risk if base_risk != 0 else 0
        )
        return {
            "asset": asset,
            "marginal_contribution": marginal_contribution,
            "component_contribution": component_contribution,
            "percentage_contribution": percentage_contribution,
        }

    def system_info(self) -> Dict[str, object]:
        """Get system information."""
        cpu_count = mp.cpu_count()
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
        except Exception:
            cpu_percent = None
        try:
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
            }
        except Exception:
            memory_info = None
        return {
            "cpu_count": cpu_count,
            "cpu_percent": cpu_percent,
            "memory": memory_info,
            "backend": self.backend,
            "n_jobs": self.n_jobs,
        }


if __name__ == "__main__":
    np.random.seed(42)
    n_days = 1000
    returns = pd.DataFrame(
        {
            "Asset_1": np.random.normal(0.001, 0.02, n_days),
            "Asset_2": np.random.normal(0.0005, 0.015, n_days),
            "Asset_3": np.random.normal(0.0008, 0.025, n_days),
        }
    )
    returns.index = pd.date_range(start="2020-01-01", periods=n_days, freq="B")
    weights = {"Asset_1": 0.4, "Asset_2": 0.3, "Asset_3": 0.3}
    engine = ParallelRiskEngine(n_jobs=4)
    result = engine.parallel_batch_risk_calculation(
        returns.mean(axis=1),
        risk_models=["parametric", "historical"],
        confidence_levels=[0.95, 0.99],
    )
    logger.info("Batch Risk Calculation Results:")
    for model, metrics in result["risk_metrics"].items():
        logger.info(f"  {model}:")
        for metric, value in metrics.items():
            logger.info(f"    {metric}: {value:.6f}")
    result = engine.parallel_portfolio_optimization(
        returns, risk_model="markowitz", n_portfolios=1000
    )
    logger.info("\nPortfolio Optimization Results:")
    logger.info(
        f"  Max Sharpe Ratio: {result['max_sharpe_portfolio']['sharpe_ratio']:.4f}"
    )
    logger.info(
        f"  Min Volatility: {result['min_volatility_portfolio']['volatility']:.4f}"
    )
    result = engine.parallel_risk_decomposition(
        returns, weights, risk_measure="volatility"
    )
    logger.info("\nRisk Decomposition Results:")
    for contribution in result["contributions"]:
        logger.info(
            f"  {contribution['asset']}: {contribution['percentage_contribution']:.2%}"
        )
    info = engine.system_info()
    logger.info(
        f"\nSystem Info: {info['cpu_count']} CPUs, {info['backend']} backend, {info['n_jobs']} jobs"
    )
