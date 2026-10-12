jest.mock("axios", () => {
  const instance = {
    post: jest.fn(() => Promise.resolve({ data: {} })),
    get: jest.fn(() => Promise.resolve({ data: {} })),
    defaults: { headers: { common: {} } },
    interceptors: {
      request: { use: jest.fn(), eject: jest.fn() },
      response: { use: jest.fn(), eject: jest.fn() },
    },
  };
  return { create: jest.fn(() => instance), __instance: instance };
});

import axios from "axios";
import apiService from "../../src/services/apiService";

const mockPost = axios.__instance.post;
const mockGet = axios.__instance.get;

describe("optimization and quant API client", () => {
  beforeEach(() => {
    mockPost.mockClear();
    mockGet.mockClear();
  });

  it("posts optimization requests to the optimization routes", async () => {
    await apiService.optimizePortfolio({ symbols: ["A", "B"] });
    expect(mockPost).toHaveBeenCalledWith("/optimization/optimize", {
      symbols: ["A", "B"],
    });
    await apiService.getEfficientFrontier({ symbols: ["A", "B"] });
    expect(mockPost).toHaveBeenCalledWith("/optimization/efficient-frontier", {
      symbols: ["A", "B"],
    });
    await apiService.simulateRisk({ weights: {} });
    expect(mockPost).toHaveBeenCalledWith("/optimization/simulate", {
      weights: {},
    });
    await apiService.analyzeSentiment(["x"]);
    expect(mockPost).toHaveBeenCalledWith("/optimization/sentiment", {
      texts: ["x"],
    });
  });

  it("reads symbols, model info and encodes forecast tickers", async () => {
    await apiService.getOptimizationSymbols();
    expect(mockGet).toHaveBeenCalledWith("/optimization/symbols");
    await apiService.getOptimizationModelInfo();
    expect(mockGet).toHaveBeenCalledWith("/optimization/model");
    await apiService.getPriceForecast("BTC_USD", 7);
    expect(mockGet).toHaveBeenCalledWith("/optimization/forecast/BTC_USD", {
      params: { periods: 7, model: "auto" },
    });
    await apiService.getPriceForecast("A/B");
    expect(mockGet).toHaveBeenLastCalledWith("/optimization/forecast/A%2FB", {
      params: { periods: 30, model: "auto" },
    });
  });

  it("routes quant operations to their endpoints", async () => {
    const cases = {
      evt: "/quant/risk/evt",
      copula: "/quant/risk/copula",
      monteCarlo: "/quant/risk/monte-carlo",
      stressTest: "/quant/risk/stress-test",
      portfolioSearch: "/quant/portfolio/search",
      report: "/quant/reports/risk",
    };
    for (const [operation, path] of Object.entries(cases)) {
      await apiService.runQuantAnalysis(operation, { symbols: ["A"] });
      expect(mockPost).toHaveBeenLastCalledWith(path, { symbols: ["A"] });
    }
  });

  it("rejects unknown quant operations without a request", async () => {
    await expect(apiService.runQuantAnalysis("nope", {})).rejects.toThrow(
      "Unknown quant operation: nope",
    );
    expect(mockPost).not.toHaveBeenCalled();
  });

  it("reads quant info and reports", async () => {
    await apiService.getQuantInfo();
    expect(mockGet).toHaveBeenCalledWith("/quant/info");
    await apiService.listQuantReports(5);
    expect(mockGet).toHaveBeenCalledWith("/quant/reports", {
      params: { limit: 5 },
    });
    await apiService.getQuantReport("risk_1.html");
    expect(mockGet).toHaveBeenCalledWith("/quant/reports/risk_1.html");
  });
});
