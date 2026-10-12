import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("axios", () => {
  const instance = {
    post: vi.fn(() => Promise.resolve({ data: { status: "success" } })),
    get: vi.fn(() => Promise.resolve({ data: { status: "success" } })),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    defaults: { headers: { common: {} } },
  };
  return {
    default: {
      create: vi.fn(() => instance),
      post: vi.fn(),
      __instance: instance,
    },
  };
});

import apiService, { QUANT_OPERATIONS } from "./apiService";

const instance = axios.__instance;

describe("quant API client", () => {
  beforeEach(() => {
    instance.post.mockClear();
    instance.get.mockClear();
  });

  it("routes every named operation to a quant endpoint", async () => {
    for (const [operation, path] of Object.entries(QUANT_OPERATIONS)) {
      expect(path.startsWith("/api/v1/quant/")).toBe(true);
      await apiService.quant.run(operation, { symbols: ["AAPL"] });
      expect(instance.post).toHaveBeenLastCalledWith(path, {
        symbols: ["AAPL"],
      });
    }
  });

  it("rejects unknown operations without sending a request", async () => {
    await expect(apiService.quant.run("nope", {})).rejects.toThrow(
      "Unknown quant operation: nope",
    );
    expect(instance.post).not.toHaveBeenCalled();
  });

  it("reads info and reports with encoded identifiers", async () => {
    await apiService.quant.getInfo();
    expect(instance.get).toHaveBeenCalledWith("/api/v1/quant/info");
    await apiService.quant.listReports(5);
    expect(instance.get).toHaveBeenCalledWith("/api/v1/quant/reports", {
      params: { limit: 5 },
    });
    await apiService.quant.getReport("a/b.html");
    expect(instance.get).toHaveBeenLastCalledWith(
      "/api/v1/quant/reports/a%2Fb.html",
    );
  });

  it("encodes forecast tickers", async () => {
    await apiService.optimization.forecast("BTC_USD", 7);
    expect(instance.get).toHaveBeenCalledWith(
      "/api/v1/optimization/forecast/BTC_USD",
      { params: { periods: 7, model: "auto" } },
    );
  });
});
