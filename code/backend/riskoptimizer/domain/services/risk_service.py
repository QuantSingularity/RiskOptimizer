import logging
from decimal import Decimal, getcontext
from typing import Any, Dict, List

import numpy as np
from riskoptimizer.core.exceptions import CalculationError, ValidationError
from riskoptimizer.infrastructure.cache.redis_cache import redis_cache
from riskoptimizer.services.quant_analysis import RiskMetrics
from riskoptimizer.utils.cache_utils import memoize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


getcontext().prec = 28


class RiskService:
    """
    Service for performing various financial risk calculations.

    This service provides methods for calculating Value at Risk (VaR),
    Conditional Value at Risk (CVaR), Sharpe Ratio, Maximum Drawdown,
    comprehensive portfolio risk metrics, and the efficient frontier.
    It leverages the `quant_analysis` module for core mathematical operations
    and includes caching for performance optimization.
    """

    def __init__(self) -> None:
        """
        Initializes the RiskService with a Redis cache instance.
        """
        self.cache = redis_cache

    def _validate_returns(self, returns: List[float]) -> None:
        """
        Validates the input list of financial returns.

        Args:
            returns: A list of numerical returns.

        Raises:
            ValidationError: If `returns` is not a list of numbers or has fewer than two elements.
        """
        if not isinstance(returns, list) or not all(
            (isinstance(r, (int, float)) for r in returns)
        ):
            raise ValidationError(
                "Returns must be a list of numbers.", "returns", returns
            )
        if len(returns) < 2:
            raise ValidationError(
                "Returns list must contain at least two elements for meaningful calculation.",
                "returns",
                returns,
            )

    def _validate_confidence(self, confidence: float) -> None:
        """
        Validates the confidence level for VaR and CVaR calculations.

        Args:
            confidence: The confidence level as a float.

        Raises:
            ValidationError: If `confidence` is not a float between 0 and 1 (exclusive).
        """
        if not isinstance(confidence, (int, float)) or not 0 < confidence < 1:
            raise ValidationError(
                "Confidence level must be a float between 0 and 1 (exclusive).",
                "confidence",
                confidence,
            )

    @memoize(ttl=3600)
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> Decimal:
        """
        Calculates the Value at Risk (VaR) for a given set of returns.

        VaR quantifies the potential loss in value of a portfolio or asset
        over a defined period for a given confidence level.

        Args:
            returns: A list of historical returns (e.g., daily, weekly).
            confidence: The confidence level (e.g., 0.95 for 95% VaR). Defaults to 0.95.

        Returns:
            A Decimal representing the calculated Value at Risk.

        Raises:
            ValidationError: If input data is invalid.
            CalculationError: If the VaR calculation fails.
        """
        self._validate_returns(returns)
        self._validate_confidence(confidence)
        try:
            cache_key = f"var:{hash(tuple(returns))}:{confidence}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(
                    f"VaR cache hit for {len(returns)} returns at {confidence} confidence"
                )
                return Decimal(cached_result)
            var = RiskMetrics.calculate_var(returns, confidence)
            self.cache.set(cache_key, str(var), ttl=3600)
            logger.info(
                f"Calculated VaR: {var} for {len(returns)} returns at {confidence} confidence"
            )
            return var
        except Exception as e:
            logger.error(f"Error calculating VaR: {str(e)}", exc_info=True)
            raise CalculationError(f"Failed to calculate VaR: {str(e)}", "var")

    @memoize(ttl=3600)
    def calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> Decimal:
        """
        Calculates the Conditional Value at Risk (CVaR) for a given set of returns.

        CVaR, also known as Expected Shortfall, measures the expected loss
        if the VaR threshold is breached.

        Args:
            returns: A list of historical returns.
            confidence: The confidence level (e.g., 0.95 for 95% CVaR). Defaults to 0.95.

        Returns:
            A Decimal representing the calculated Conditional Value at Risk.

        Raises:
            ValidationError: If input data is invalid.
            CalculationError: If the CVaR calculation fails.
        """
        self._validate_returns(returns)
        self._validate_confidence(confidence)
        try:
            cache_key = f"cvar:{hash(tuple(returns))}:{confidence}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(
                    f"CVaR cache hit for {len(returns)} returns at {confidence} confidence"
                )
                return Decimal(cached_result)
            cvar = RiskMetrics.calculate_cvar(returns, confidence)
            self.cache.set(cache_key, str(cvar), ttl=3600)
            logger.info(
                f"Calculated CVaR: {cvar} for {len(returns)} returns at {confidence} confidence"
            )
            return cvar
        except Exception as e:
            logger.error(f"Error calculating CVaR: {str(e)}", exc_info=True)
            raise CalculationError(f"Failed to calculate CVaR: {str(e)}", "cvar")

    @memoize(ttl=3600)
    def calculate_sharpe_ratio(
        self, returns: List[float], risk_free_rate: float = 0.0
    ) -> Decimal:
        """
        Calculates the Sharpe Ratio for a given set of returns.

        The Sharpe Ratio measures the risk-adjusted return of an investment.

        Args:
            returns: A list of historical returns.
            risk_free_rate: The risk-free rate of return. Defaults to 0.0.

        Returns:
            A Decimal representing the calculated Sharpe Ratio.

        Raises:
            ValidationError: If input data is invalid.
            CalculationError: If the Sharpe Ratio calculation fails.
        """
        self._validate_returns(returns)
        if not isinstance(risk_free_rate, (int, float)):
            raise ValidationError(
                "Risk-free rate must be a number", "risk_free_rate", risk_free_rate
            )
        try:
            cache_key = f"sharpe:{hash(tuple(returns))}:{risk_free_rate}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(
                    f"Sharpe ratio cache hit for {len(returns)} returns with {risk_free_rate} risk-free rate"
                )
                return Decimal(cached_result)
            sharpe_ratio = RiskMetrics.calculate_sharpe_ratio(returns, risk_free_rate)
            self.cache.set(cache_key, str(sharpe_ratio), ttl=3600)
            logger.info(
                f"Calculated Sharpe ratio: {sharpe_ratio} for {len(returns)} returns"
            )
            return sharpe_ratio
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}", exc_info=True)
            raise CalculationError(
                f"Failed to calculate Sharpe ratio: {str(e)}", "sharpe_ratio"
            )

    @memoize(ttl=3600)
    def calculate_max_drawdown(self, returns: List[float]) -> Decimal:
        """
        Calculates the Maximum Drawdown for a given set of returns.

        Maximum Drawdown is the largest drop from a peak to a trough in a portfolio's value.

        Args:
            returns: A list of historical returns.

        Returns:
            A Decimal representing the calculated Maximum Drawdown.

        Raises:
            ValidationError: If input data is invalid.
            CalculationError: If the Maximum Drawdown calculation fails.
        """
        self._validate_returns(returns)
        try:
            cache_key = f"max_drawdown:{hash(tuple(returns))}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Max drawdown cache hit for {len(returns)} returns")
                return Decimal(cached_result)
            max_drawdown = RiskMetrics.calculate_max_drawdown(returns)
            self.cache.set(cache_key, str(max_drawdown), ttl=3600)
            logger.info(
                f"Calculated max drawdown: {max_drawdown} for {len(returns)} returns"
            )
            return max_drawdown
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {str(e)}", exc_info=True)
            raise CalculationError(
                f"Failed to calculate max drawdown: {str(e)}", "max_drawdown"
            )

    def calculate_portfolio_risk_metrics(
        self,
        returns: List[float],
        confidence: float = 0.95,
        risk_free_rate: float = 0.0,
    ) -> Dict[str, Decimal]:
        """
        Calculates a comprehensive set of risk metrics for a portfolio.

        This includes expected return, volatility, VaR, CVaR, Sharpe Ratio, and Maximum Drawdown.

        Args:
            returns: A list of historical returns for the portfolio.
            confidence: The confidence level for VaR and CVaR. Defaults to 0.95.
            risk_free_rate: The risk-free rate for Sharpe Ratio. Defaults to 0.0.

        Returns:
            A dictionary containing all calculated risk metrics.

        Raises:
            ValidationError: If input data is invalid.
            CalculationError: If any of the risk metric calculations fail.
        """
        self._validate_returns(returns)
        self._validate_confidence(confidence)
        if not isinstance(risk_free_rate, (int, float)):
            raise ValidationError(
                "Risk-free rate must be a number", "risk_free_rate", risk_free_rate
            )
        try:
            cache_key = (
                f"risk_metrics:{hash(tuple(returns))}:{confidence}:{risk_free_rate}"
            )
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Risk metrics cache hit for {len(returns)} returns")
                return {k: Decimal(v) for k, v in cached_result.items()}
            mean_return = RiskMetrics.calculate_expected_return(returns)
            volatility = RiskMetrics.calculate_volatility(returns)
            var = self.calculate_var(returns, confidence)
            cvar = self.calculate_cvar(returns, confidence)
            sharpe_ratio = self.calculate_sharpe_ratio(returns, risk_free_rate)
            max_drawdown = self.calculate_max_drawdown(returns)
            metrics = {
                "expected_return": mean_return,
                "volatility": volatility,
                "value_at_risk": var,
                "conditional_var": cvar,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
            }
            self.cache.set(cache_key, {k: str(v) for k, v in metrics.items()}, ttl=3600)
            logger.info(f"Calculated risk metrics for {len(returns)} returns")
            return metrics
        except (ValidationError, CalculationError):
            raise
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}", exc_info=True)
            raise CalculationError(
                f"Failed to calculate risk metrics: {str(e)}", "risk_metrics"
            )

    @memoize(ttl=86400)
    def calculate_efficient_frontier(
        self,
        returns: Dict[str, List[float]],
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        risk_free_rate: float = 0.0,
        points: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Calculates the efficient frontier for a set of assets.

        The efficient frontier represents a set of optimal portfolios that offer the
        highest expected return for a given level of risk, or the lowest risk for a
        given level of expected return.

        Args:
            returns: A dictionary where keys are asset symbols (e.g., "AAPL") and
                     values are lists of historical returns for each asset.
            min_weight: The minimum weight allowed for any single asset in a portfolio.
                        Defaults to 0.0 (no short selling).
            max_weight: The maximum weight allowed for any single asset in a portfolio.
                        Defaults to 1.0 (no leverage).
            risk_free_rate: The risk-free rate of return, used for Sharpe Ratio calculation.
                            Defaults to 0.0.
            points: The number of points to generate along the efficient frontier.
                    Defaults to 20.

        Returns:
            A list of dictionaries, where each dictionary represents a point on the
            efficient frontier, including expected return, volatility, Sharpe Ratio,
            and asset weights.

        Raises:
            ValidationError: If input data is invalid (e.g., insufficient assets, invalid weights).
            CalculationError: If the efficient frontier calculation fails (e.g., missing library).
        """
        try:
            import pandas as pd
            from pypfopt import EfficientFrontier, expected_returns, risk_models
        except ImportError:
            logger.error(
                "PyPortfolioOpt library not installed. Please install it using 'pip install PyPortfolioOpt'",
                exc_info=True,
            )
            raise CalculationError(
                "Required library PyPortfolioOpt not installed", "efficient_frontier"
            )
        if not returns or not isinstance(returns, dict):
            raise ValidationError("Returns dictionary is required", "returns", returns)
        if len(returns) < 2:
            raise ValidationError(
                "At least two assets are required to calculate an efficient frontier.",
                "returns",
                returns,
            )
        for asset, asset_returns in returns.items():
            self._validate_returns(asset_returns)
        if not isinstance(min_weight, (int, float)) or not 0 <= min_weight <= 1:
            raise ValidationError(
                "Minimum weight must be a number between 0 and 1 (inclusive).",
                "min_weight",
                min_weight,
            )
        if not isinstance(max_weight, (int, float)) or not 0 <= max_weight <= 1:
            raise ValidationError(
                "Maximum weight must be a number between 0 and 1 (inclusive).",
                "max_weight",
                max_weight,
            )
        if min_weight > max_weight:
            raise ValidationError(
                "Minimum weight cannot be greater than maximum weight.",
                "min_weight",
                min_weight,
            )
        if not isinstance(points, int) or points < 2:
            raise ValidationError(
                "Number of points for efficient frontier must be an integer of at least 2.",
                "points",
                points,
            )
        try:
            cache_key = f"efficient_frontier:{hash(tuple(((k, tuple(v)) for k, v in sorted(returns.items()))))}:{min_weight}:{max_weight}:{risk_free_rate}:{points}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Efficient frontier cache hit for {len(returns)} assets")
                for point in cached_result:
                    point["expected_return"] = Decimal(point["expected_return"])
                    point["volatility"] = Decimal(point["volatility"])
                    point["sharpe_ratio"] = Decimal(point["sharpe_ratio"])
                    point["weights"] = {
                        k: Decimal(v) for k, v in point["weights"].items()
                    }
                return cached_result
            returns_df = pd.DataFrame(returns)
            mu = expected_returns.mean_historical_return(returns_df)
            S = risk_models.sample_cov(returns_df)
            ef = EfficientFrontier(mu, S)
            ef.add_constraint(lambda w: w >= min_weight)
            ef.add_constraint(lambda w: w <= max_weight)
            frontier_points = []
            ef.min_volatility()
            min_vol_weights = ef.clean_weights()
            min_vol_performance = ef.portfolio_performance()
            frontier_points.append(
                {
                    "type": "min_volatility",
                    "expected_return": Decimal(str(min_vol_performance[0])),
                    "volatility": Decimal(str(min_vol_performance[1])),
                    "sharpe_ratio": Decimal(str(min_vol_performance[2])),
                    "weights": {
                        asset: Decimal(str(weight))
                        for asset, weight in min_vol_weights.items()
                    },
                }
            )
            ef = EfficientFrontier(mu, S)
            ef.add_constraint(lambda w: w >= min_weight)
            ef.add_constraint(lambda w: w <= max_weight)
            ef.max_sharpe(risk_free_rate=risk_free_rate)
            max_sharpe_weights = ef.clean_weights()
            max_sharpe_performance = ef.portfolio_performance()
            frontier_points.append(
                {
                    "type": "max_sharpe",
                    "expected_return": Decimal(str(max_sharpe_performance[0])),
                    "volatility": Decimal(str(max_sharpe_performance[1])),
                    "sharpe_ratio": Decimal(str(max_sharpe_performance[2])),
                    "weights": {
                        asset: Decimal(str(weight))
                        for asset, weight in max_sharpe_weights.items()
                    },
                }
            )
            ef = EfficientFrontier(mu, S)
            ef.add_constraint(lambda w: w >= min_weight)
            ef.add_constraint(lambda w: w <= max_weight)
            min_ret = min((p["expected_return"] for p in frontier_points))
            max_ret = max((p["expected_return"] for p in frontier_points))
            if min_ret == max_ret:
                logger.warning(
                    "Cannot generate diverse efficient frontier points: all assets have similar returns."
                )
                self.cache.set(
                    cache_key,
                    [
                        {
                            k: (
                                str(v)
                                if isinstance(v, Decimal)
                                else (
                                    {wk: str(wv) for wk, wv in v.items()}
                                    if isinstance(v, dict)
                                    else v
                                )
                            )
                            for k, v in p.items()
                        }
                        for p in frontier_points
                    ],
                    ttl=86400,
                )
                return frontier_points
            target_returns = np.linspace(
                float(min_ret), float(max_ret), points
            ).tolist()
            for target_ret in target_returns:
                try:
                    ef_point = EfficientFrontier(mu, S)
                    ef_point.add_constraint(lambda w: w >= min_weight)
                    ef_point.add_constraint(lambda w: w <= max_weight)
                    ef_point.efficient_return(target_ret)
                    weights = ef_point.clean_weights()
                    performance = ef_point.portfolio_performance()
                    frontier_points.append(
                        {
                            "type": "efficient_portfolio",
                            "expected_return": Decimal(str(performance[0])),
                            "volatility": Decimal(str(performance[1])),
                            "sharpe_ratio": Decimal(str(performance[2])),
                            "weights": {
                                asset: Decimal(str(weight))
                                for asset, weight in weights.items()
                            },
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not find portfolio for target return {target_ret}: {e}"
                    )
                    continue
            self.cache.set(
                cache_key,
                [
                    {
                        k: (
                            str(v)
                            if isinstance(v, Decimal)
                            else (
                                {wk: str(wv) for wk, wv in v.items()}
                                if isinstance(v, dict)
                                else v
                            )
                        )
                        for k, v in p.items()
                    }
                    for p in frontier_points
                ],
                ttl=86400,
            )
            logger.info(
                f"Efficient frontier calculated successfully with {len(frontier_points)} points"
            )
            return frontier_points
        except (ValidationError, CalculationError):
            raise
        except Exception as e:
            logger.error(
                f"Error calculating efficient frontier: {str(e)}", exc_info=True
            )
            raise CalculationError(
                f"Failed to calculate efficient frontier: {str(e)}",
                "efficient_frontier",
            )


risk_service = RiskService()
