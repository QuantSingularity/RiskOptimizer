import { describe, expect, it } from "vitest";
import {
  buildOptimizationRequest,
  buildResults,
  currentAllocations,
  resolveMaxWeight,
  sliderToTolerance,
} from "./optimization";

describe("sliderToTolerance", () => {
  it("maps the 0-100 slider onto the 1-10 backend scale", () => {
    expect(sliderToTolerance(0)).toBe(1);
    expect(sliderToTolerance(50)).toBe(6);
    expect(sliderToTolerance(100)).toBe(10);
  });

  it("clamps out of range input", () => {
    expect(sliderToTolerance(-20)).toBe(1);
    expect(sliderToTolerance(500)).toBe(10);
  });
});

describe("resolveMaxWeight", () => {
  it("returns the cap only when feasible", () => {
    expect(resolveMaxWeight(7, true)).toBe(0.2);
    expect(resolveMaxWeight(5, true)).toBe(0.2);
  });

  it("raises the cap to the smallest feasible value for few assets", () => {
    expect(resolveMaxWeight(3, true)).toBe(0.34);
    expect(resolveMaxWeight(2, true)).toBe(0.5);
    expect(resolveMaxWeight(3, true) * 3).toBeGreaterThanOrEqual(1);
  });

  it("is unconstrained when disabled", () => {
    expect(resolveMaxWeight(3, false)).toBe(1);
  });
});

describe("buildOptimizationRequest", () => {
  it("produces a backend compatible payload", () => {
    expect(
      buildOptimizationRequest({
        symbols: ["AAPL", "MSFT", "BTC_USD"],
        slider: 100,
        method: "max_sharpe",
        capEnabled: true,
      }),
    ).toEqual({
      symbols: ["AAPL", "MSFT", "BTC_USD"],
      risk_tolerance: 10,
      method: "max_sharpe",
      min_weight: 0,
      max_weight: 0.34,
    });
  });
});

describe("currentAllocations", () => {
  it("uses portfolio holdings when they overlap the selection", () => {
    const { weights, basis } = currentAllocations(
      [
        { symbol: "AAPL", totalValue: 750 },
        { symbol: "msft", totalValue: 250 },
        { symbol: "ZZZ", totalValue: 9999 },
      ],
      ["AAPL", "MSFT", "TSLA"],
    );
    expect(basis).toBe("portfolio");
    expect(weights.AAPL).toBeCloseTo(75);
    expect(weights.MSFT).toBeCloseTo(25);
    expect(weights.TSLA).toBe(0);
  });

  it("falls back to equal weights", () => {
    const { weights, basis } = currentAllocations([], ["AAPL", "MSFT"]);
    expect(basis).toBe("equal");
    expect(weights.AAPL).toBe(50);
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

  it("converts fractions to percentages and marks the nearest frontier point", () => {
    const { results, frontierData } = buildResults({
      optimization,
      frontier,
      symbols: ["AAPL", "MSFT"],
      assets: [],
    });
    expect(results.expected_return).toBe(12.3);
    expect(results.expected_risk).toBe(21);
    expect(results.sharpe_ratio).toBe(0.46);
    expect(results.allocations[0]).toMatchObject({
      symbol: "AAPL",
      current: 50,
      optimized: 60,
    });
    expect(frontierData.optimalIdx).toBe(1);
  });

  it("returns no frontier when none was computed", () => {
    const { frontierData } = buildResults({
      optimization,
      frontier: [],
      symbols: ["AAPL", "MSFT"],
      assets: [],
    });
    expect(frontierData).toBeNull();
  });
});
