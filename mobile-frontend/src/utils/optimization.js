export const METHODS = [
  { value: "utility", label: "Risk Utility" },
  { value: "max_sharpe", label: "Max Sharpe" },
  { value: "min_variance", label: "Min Risk" },
];

export const SYMBOL_NAMES = {
  AAPL: "Apple Inc.",
  MSFT: "Microsoft Corp.",
  AMZN: "Amazon.com Inc.",
  TSLA: "Tesla Inc.",
  GOOGL: "Alphabet Inc.",
  BTC_USD: "Bitcoin",
  ETH_USD: "Ethereum",
};

export const MIN_ASSETS = 2;

export const resolveMaxWeight = (assetCount, requested) => {
  if (assetCount < 1) return 1;
  const feasibleFloor = Math.ceil(100 / assetCount) / 100;
  return Math.min(1, Math.max(Number(requested) || 1, feasibleFloor));
};

export const buildOptimizationRequest = ({
  symbols,
  tolerance,
  method,
  maxWeight,
}) => ({
  symbols,
  risk_tolerance: Math.min(10, Math.max(1, Math.round(tolerance))),
  method,
  min_weight: 0,
  max_weight: resolveMaxWeight(symbols.length, maxWeight),
});

const round = (value, digits = 1) => Number(Number(value).toFixed(digits));

export const buildResults = ({ optimization, frontier, symbols }) => {
  const metrics = optimization.performance_metrics;
  const equal = 100 / symbols.length;
  const allocations = symbols.map((symbol) => ({
    symbol,
    name: SYMBOL_NAMES[symbol] || symbol,
    baseline: round(equal),
    optimized: round((optimization.optimized_allocation[symbol] || 0) * 100),
  }));
  const points = (frontier || []).map((point) => ({
    risk: round(point.volatility * 100, 2),
    return: round(point.expected_return * 100, 2),
  }));
  const optimalRisk = metrics.volatility * 100;
  let optimalIdx = 0;
  points.forEach((point, index) => {
    if (
      Math.abs(point.risk - optimalRisk) <
      Math.abs(points[optimalIdx].risk - optimalRisk)
    ) {
      optimalIdx = index;
    }
  });
  return {
    summary: {
      expectedReturn: round(metrics.expected_return * 100),
      expectedRisk: round(metrics.volatility * 100),
      sharpeRatio: round(metrics.sharpe_ratio, 2),
      modelType: optimization.model_type,
      method: optimization.method,
    },
    allocations,
    frontier: points,
    optimalIdx,
  };
};

export const extractErrorMessage = (error) =>
  error?.response?.data?.error?.message ||
  error?.response?.data?.message ||
  error?.message ||
  "Something went wrong";
