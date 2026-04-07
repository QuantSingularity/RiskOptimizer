import logging
from decimal import Decimal, getcontext
from typing import Any, Dict, List

import numpy as np
from src.core.exceptions import CalculationError, ValidationError
from src.infrastructure.cache.redis_cache import redis_cache
from src.services.quant_analysis import RiskMetrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

getcontext().prec = 28


class RiskService:
    """
    Service for performing various financial risk calculations.

    Provides methods for calculating Value at Risk (VaR), Conditional Value at Risk
    (CVaR), Sharpe Ratio, Maximum Drawdown, comprehensive portfolio risk metrics,
    and the efficient frontier. Includes Redis caching for performance optimization.
    """

    def __init__(self) -> None:
        self.cache = redis_cache

    def _validate_returns(self, returns: List[float]) -> None:
        """
        Validates the input list of financial returns.

        Raises:
            ValidationError: If returns is not a list of numbers or has fewer than two elements.
        """
        if not isinstance(returns, list) or not all(
            isinstance(r, (int, float, Decimal)) for r in returns
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

        Raises:
            ValidationError: If confidence is not a float between 0 and 1 (exclusive).
        """
        if not isinstance(confidence, (int, float)) or not (0 < confidence < 1):
            raise ValidationError(
                "Confidence level must be a float between 0 and 1 (exclusive).",
                "confidence",
                confidence,
            )

    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> Decimal:
        """
        Calculates the Value at Risk (VaR) for a given set of returns.

        Args:
            returns: A list of historical returns.
            confidence: The confidence level. Defaults to 0.95.

        Returns:
            A Decimal representing the calculated Value at Risk (positive).

        Raises:
            ValidationError: If input data is invalid.
            CalculationError: If the VaR calculation fails.
        """
        self._validate_returns(returns)
        self._validate_confidence(confidence)
        try:
            cache_key = f"var:{hash(tuple(float(r) for r in returns))}:{confidence}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(
                    f"VaR cache hit for {len(returns)} returns at {confidence} confidence"
                )
                return Decimal(str(cached_result))
            var = RiskMetrics.calculate_var(returns, confidence)
            self.cache.set(cache_key, str(var), ttl=3600)
            logger.info(
                f"Calculated VaR: {var} for {len(returns)} returns at {confidence} confidence"
            )
            return var
        except (ValidationError, CalculationError):
            raise
        except Exception as e:
            logger.error(f"Error calculating VaR: {str(e)}", exc_info=True)
            raise CalculationError(f"Failed to calculate VaR: {str(e)}", "var")

    def calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> Decimal:
        """
        Calculates the Conditional Value at Risk (CVaR) for a given set of returns.

        Args:
            returns: A list of historical returns.
            confidence: The confidence level. Defaults to 0.95.

        Returns:
            A Decimal representing the calculated Conditional Value at Risk (positive).

        Raises:
            ValidationError: If input data is invalid.
            CalculationError: If the CVaR calculation fails.
        """
        self._validate_returns(returns)
        self._validate_confidence(confidence)
        try:
            cache_key = f"cvar:{hash(tuple(float(r) for r in returns))}:{confidence}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(
                    f"CVaR cache hit for {len(returns)} returns at {confidence} confidence"
                )
                return Decimal(str(cached_result))
            cvar = RiskMetrics.calculate_cvar(returns, confidence)
            self.cache.set(cache_key, str(cvar), ttl=3600)
            logger.info(
                f"Calculated CVaR: {cvar} for {len(returns)} returns at {confidence} confidence"
            )
            return cvar
        except (ValidationError, CalculationError):
            raise
        except Exception as e:
            logger.error(f"Error calculating CVaR: {str(e)}", exc_info=True)
            raise CalculationError(f"Failed to calculate CVaR: {str(e)}", "cvar")

    def calculate_sharpe_ratio(
        self, returns: List[float], risk_free_rate: float = 0.0
    ) -> Decimal:
        """
        Calculates the Sharpe Ratio for a given set of returns.

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
            cache_key = (
                f"sharpe:{hash(tuple(float(r) for r in returns))}:{risk_free_rate}"
            )
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Sharpe ratio cache hit for {len(returns)} returns")
                return Decimal(str(cached_result))
            sharpe_ratio = RiskMetrics.calculate_sharpe_ratio(returns, risk_free_rate)
            self.cache.set(cache_key, str(sharpe_ratio), ttl=3600)
            logger.info(
                f"Calculated Sharpe ratio: {sharpe_ratio} for {len(returns)} returns"
            )
            return sharpe_ratio
        except (ValidationError, CalculationError):
            raise
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}", exc_info=True)
            raise CalculationError(
                f"Failed to calculate Sharpe ratio: {str(e)}", "sharpe_ratio"
            )

    def calculate_max_drawdown(self, returns: List[float]) -> Decimal:
        """
        Calculates the Maximum Drawdown for a given set of returns.
        Returns a negative Decimal representing the worst drawdown (loss convention).

        Args:
            returns: A list of historical returns.

        Returns:
            A Decimal representing the Maximum Drawdown (negative value).

        Raises:
            ValidationError: If input data is invalid.
            CalculationError: If the calculation fails.
        """
        self._validate_returns(returns)
        try:
            cache_key = f"max_drawdown:{hash(tuple(float(r) for r in returns))}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Max drawdown cache hit for {len(returns)} returns")
                return Decimal(str(cached_result))
            max_drawdown_abs = RiskMetrics.calculate_max_drawdown(returns)
            max_drawdown = -max_drawdown_abs
            self.cache.set(cache_key, str(max_drawdown), ttl=3600)
            logger.info(
                f"Calculated max drawdown: {max_drawdown} for {len(returns)} returns"
            )
            return max_drawdown
        except (ValidationError, CalculationError):
            raise
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

        Args:
            returns: A list of historical returns for the portfolio.
            confidence: The confidence level for VaR and CVaR. Defaults to 0.95.
            risk_free_rate: The risk-free rate for Sharpe Ratio. Defaults to 0.0.

        Returns:
            A dictionary containing all calculated risk metrics.

        Raises:
            ValidationError: If input data is invalid.
            CalculationError: If any calculation fails.
        """
        self._validate_returns(returns)
        self._validate_confidence(confidence)
        if not isinstance(risk_free_rate, (int, float)):
            raise ValidationError(
                "Risk-free rate must be a number", "risk_free_rate", risk_free_rate
            )
        try:
            cache_key = f"risk_metrics:{hash(tuple(float(r) for r in returns))}:{confidence}:{risk_free_rate}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None and isinstance(cached_result, dict):
                logger.debug(f"Risk metrics cache hit for {len(returns)} returns")
                return {k: Decimal(str(v)) for k, v in cached_result.items()}
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

        Args:
            returns: A dictionary of asset symbols to lists of historical returns.
            min_weight: Minimum weight per asset. Defaults to 0.0.
            max_weight: Maximum weight per asset. Defaults to 1.0.
            risk_free_rate: The risk-free rate. Defaults to 0.0.
            points: Number of points on the frontier. Defaults to 20.

        Returns:
            A list of dictionaries representing points on the efficient frontier.

        Raises:
            ValidationError: If input data is invalid.
            CalculationError: If the calculation fails.
        """
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
        if not isinstance(min_weight, (int, float)) or not (0 <= min_weight <= 1):
            raise ValidationError(
                "Minimum weight must be a number between 0 and 1 (inclusive).",
                "min_weight",
                min_weight,
            )
        if not isinstance(max_weight, (int, float)) or not (0 <= max_weight <= 1):
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
            import pandas as pd
            from pypfopt import EfficientFrontier, expected_returns, risk_models
        except ImportError:
            logger.error("PyPortfolioOpt library not installed.", exc_info=True)
            raise CalculationError(
                "Required library PyPortfolioOpt not installed", "efficient_frontier"
            )

        try:
            cache_key = f"efficient_frontier:{hash(tuple(sorted((k, tuple(v)) for k, v in returns.items())))}:{min_weight}:{max_weight}:{risk_free_rate}:{points}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None and isinstance(cached_result, list):
                logger.debug(f"Efficient frontier cache hit for {len(returns)} assets")
                for point in cached_result:
                    point["expected_return"] = Decimal(str(point["expected_return"]))
                    point["volatility"] = Decimal(str(point["volatility"]))
                    point["sharpe_ratio"] = Decimal(str(point["sharpe_ratio"]))
                    point["weights"] = {
                        k: Decimal(str(v)) for k, v in point["weights"].items()
                    }
                return cached_result

            returns_df = pd.DataFrame(returns)
            mu = expected_returns.mean_historical_return(returns_df)
            S = risk_models.sample_cov(returns_df)

            frontier_points = []

            ef = EfficientFrontier(mu, S)
            ef.add_constraint(lambda w: w >= min_weight)
            ef.add_constraint(lambda w: w <= max_weight)
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
                        asset: Decimal(str(w)) for asset, w in min_vol_weights.items()
                    },
                }
            )

            ef2 = EfficientFrontier(mu, S)
            ef2.add_constraint(lambda w: w >= min_weight)
            ef2.add_constraint(lambda w: w <= max_weight)
            ef2.max_sharpe(risk_free_rate=risk_free_rate)
            max_sharpe_weights = ef2.clean_weights()
            max_sharpe_performance = ef2.portfolio_performance()
            frontier_points.append(
                {
                    "type": "max_sharpe",
                    "expected_return": Decimal(str(max_sharpe_performance[0])),
                    "volatility": Decimal(str(max_sharpe_performance[1])),
                    "sharpe_ratio": Decimal(str(max_sharpe_performance[2])),
                    "weights": {
                        asset: Decimal(str(w))
                        for asset, w in max_sharpe_weights.items()
                    },
                }
            )

            min_ret = min(p["expected_return"] for p in frontier_points)
            max_ret = max(p["expected_return"] for p in frontier_points)

            if min_ret != max_ret:
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
                                    asset: Decimal(str(w))
                                    for asset, w in weights.items()
                                },
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            f"Could not find portfolio for target return {target_ret}: {e}"
                        )

            serializable = [
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
            ]
            self.cache.set(cache_key, serializable, ttl=86400)
            logger.info(
                f"Efficient frontier calculated with {len(frontier_points)} points"
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
