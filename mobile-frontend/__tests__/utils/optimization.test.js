import {
  buildOptimizationRequest,
  buildResults,
  extractErrorMessage,
  resolveMaxWeight,
} from "../../src/utils/optimization";

describe("resolveMaxWeight", () => {
  it("keeps a feasible cap", () => {
    expect(resolveMaxWeight(7, 0.2)).toBe(0.2);
    expect(resolveMaxWeight(5, 0.2)).toBe(0.2);
  });

  it("raises an infeasible cap to the smallest feasible value", () => {
    expect(resolveMaxWeight(3, 0.2)).toBe(0.34);
    expect(resolveMaxWeight(2, 0.1)).toBe(0.5);
    expect(resolveMaxWeight(3, 0.2) * 3).toBeGreaterThanOrEqual(1);
  });

  it("defaults to unconstrained", () => {
    expect(resolveMaxWeight(4, undefined)).toBe(1);
    expect(resolveMaxWeight(4, 5)).toBe(1);
  });
});

describe("buildOptimizationRequest", () => {
  it("builds a backend compatible payload", () => {
    expect(
      buildOptimizationRequest({
        symbols: ["AAPL", "MSFT", "TSLA"],
        tolerance: 12.4,
        method: "max_sharpe",
        maxWeight: 0.2,
      }),
    ).toEqual({
      symbols: ["AAPL", "MSFT", "TSLA"],
      risk_tolerance: 10,
      method: "max_sharpe",
      min_weight: 0,
      max_weight: 0.34,
    });
  });

  it("clamps tolerance from below", () => {
    expect(
      buildOptimizationRequest({
        symbols: ["A", "B"],
        tolerance: -3,
        method: "utility",
        maxWeight: 1,
      }).risk_tolerance,
    ).toBe(1);
  });
});

describe("buildResults", () => {
  const optimization = {
    optimized_allocation: { AAPL: 0.6, MSFT: 0.4 },
    performance_metrics: {
      expected_return: 0.123,
      volatility: 0.21,
      sharpe_ratio: 0.4567,
    },
    model_type: "ml",
    method: "utility",
  };
  const frontier = [
    { volatility: 0.15, expected_return: 0.08 },
    { volatility: 0.2, expected_return: 0.11 },
    { volatility: 0.3, expected_return: 0.15 },
  ];

  it("converts fractions to percentages", () => {
    const built = buildResults({
      optimization,
      frontier,
      symbols: ["AAPL", "MSFT"],
    });
    expect(built.summary).toEqual({
      expectedReturn: 12.3,
      expectedRisk: 21,
      sharpeRatio: 0.46,
      modelType: "ml",
      method: "utility",
    });
    expect(built.allocations[0]).toMatchObject({
      symbol: "AAPL",
      baseline: 50,
      optimized: 60,
    });
    expect(built.optimalIdx).toBe(1);
  });

  it("handles a missing frontier", () => {
    const built = buildResults({
      optimization,
      frontier: undefined,
      symbols: ["AAPL", "MSFT"],
    });
    expect(built.frontier).toEqual([]);
  });
});

describe("extractErrorMessage", () => {
  it("prefers the backend message", () => {
    expect(
      extractErrorMessage({
        response: { data: { error: { message: "bad input" } } },
        message: "Request failed",
      }),
    ).toBe("bad input");
  });

  it("falls back gracefully", () => {
    expect(extractErrorMessage({ message: "Network Error" })).toBe(
      "Network Error",
    );
    expect(extractErrorMessage(undefined)).toBe("Something went wrong");
  });
});
