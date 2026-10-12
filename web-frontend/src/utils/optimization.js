export const METHODS = [
  { value: "utility", label: "Risk Tolerance Utility" },
  { value: "max_sharpe", label: "Maximum Sharpe Ratio" },
  { value: "min_variance", label: "Minimum Risk" },
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
export const CAP_PER_ASSET = 0.2;

const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

export const sliderToTolerance = (slider) =>
  clamp(1 + Math.round((clamp(slider, 0, 100) / 100) * 9), 1, 10);

export const resolveMaxWeight = (assetCount, capEnabled) => {
  if (!capEnabled || assetCount < 1) return 1;
  if (assetCount * CAP_PER_ASSET >= 1) return CAP_PER_ASSET;
  return Math.min(1, Math.ceil(100 / assetCount) / 100);
};

export const buildOptimizationRequest = ({
  symbols,
  slider,
  method,
  capEnabled,
}) => ({
  symbols,
  risk_tolerance: sliderToTolerance(slider),
  method,
  min_weight: 0,
  max_weight: resolveMaxWeight(symbols.length, capEnabled),
});

export const currentAllocations = (assets, symbols) => {
  const held = {};
  let total = 0;
  (assets || []).forEach((asset) => {
    const key = String(asset.symbol || "")
      .toUpperCase()
      .replace(/-/g, "_");
    const value = Number(asset.totalValue);
    if (symbols.includes(key) && Number.isFinite(value) && value > 0) {
      held[key] = (held[key] || 0) + value;
      total += value;
    }
  });
  if (total > 0) {
    return {
      weights: Object.fromEntries(
        symbols.map((symbol) => [symbol, ((held[symbol] || 0) / total) * 100]),
      ),
      basis: "portfolio",
    };
  }
  return {
    weights: Object.fromEntries(
      symbols.map((symbol) => [symbol, 100 / symbols.length]),
    ),
    basis: "equal",
  };
};

const round = (value, digits = 1) => Number(Number(value).toFixed(digits));

export const buildResults = ({ optimization, frontier, symbols, assets }) => {
  const metrics = optimization.performance_metrics;
  const { weights: current, basis } = currentAllocations(assets, symbols);
  const allocations = symbols.map((symbol) => ({
    name: SYMBOL_NAMES[symbol] ? `${SYMBOL_NAMES[symbol]} (${symbol})` : symbol,
    symbol,
    current: round(current[symbol] || 0),
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
    results: {
      expected_return: round(metrics.expected_return * 100),
      expected_risk: round(metrics.volatility * 100),
      sharpe_ratio: round(metrics.sharpe_ratio, 2),
      allocations,
      model_type: optimization.model_type,
      method: optimization.method,
      current_basis: basis,
      weights: optimization.optimized_allocation,
    },
    frontierData: points.length ? { points, optimalIdx } : null,
  };
};
