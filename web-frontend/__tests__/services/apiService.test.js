import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// We test the real apiService by mocking axios at module level
vi.mock("axios", async () => {
  const mockInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    defaults: { headers: { common: {} } },
  };
  return {
    default: {
      create: vi.fn(() => mockInstance),
      ...mockInstance,
    },
  };
});

// Import after mock to get the mocked version
import axios from "axios";
import apiService from "../../src/services/apiService";

const mockAxiosInstance = axios.create();

describe("apiService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe("auth", () => {
    it("calls POST /api/v1/auth/login", async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { status: "success", data: { token: "tok", user: { id: 1 } } },
      });
      const result = await apiService.auth.login({ wallet_address: "0xabc" });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/auth/login",
        { wallet_address: "0xabc" },
      );
      expect(result.status).toBe("success");
    });

    it("calls POST /api/v1/auth/register", async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { status: "success", data: { token: "tok2", user: { id: 2 } } },
      });
      await apiService.auth.register({ username: "u", email: "e@e.com" });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/auth/register",
        { username: "u", email: "e@e.com" },
      );
    });

    it("calls POST /api/v1/auth/logout", async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: { status: "success" } });
      await apiService.auth.logout();
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/auth/logout",
      );
    });

    it("calls POST /api/v1/auth/refresh", async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: { status: "success" } });
      await apiService.auth.refresh("refresh_tok");
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/auth/refresh",
        {
          refresh_token: "refresh_tok",
        },
      );
    });
  });

  describe("portfolio", () => {
    it("calls GET /api/v1/portfolios/address/:address", async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { status: "success", data: {} },
      });
      await apiService.portfolio.getByAddress("0xabc");
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        "/api/v1/portfolios/address/0xabc",
      );
    });

    it("calls GET /api/v1/portfolios/user/:userId", async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { status: "success", data: {} },
      });
      await apiService.portfolio.getByUserId(42);
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        "/api/v1/portfolios/user/42",
      );
    });

    it("calls POST /api/v1/portfolios for create", async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { status: "success", data: {} },
      });
      await apiService.portfolio.create({ user_address: "0xabc", assets: [] });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/portfolios",
        { user_address: "0xabc", assets: [] },
      );
    });

    it("calls POST /api/v1/portfolios/save for save", async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: { status: "success" } });
      await apiService.portfolio.save({ user_address: "0xabc", assets: [] });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/portfolios/save",
        { user_address: "0xabc", assets: [] },
      );
    });

    it("calls PUT /api/v1/portfolios/:id for update", async () => {
      mockAxiosInstance.put.mockResolvedValue({ data: { status: "success" } });
      await apiService.portfolio.update(5, { assets: [] });
      expect(mockAxiosInstance.put).toHaveBeenCalledWith(
        "/api/v1/portfolios/5",
        { assets: [] },
      );
    });

    it("calls DELETE /api/v1/portfolios/:id", async () => {
      mockAxiosInstance.delete.mockResolvedValue({
        data: { status: "success" },
      });
      await apiService.portfolio.delete(5);
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith(
        "/api/v1/portfolios/5",
      );
    });
  });

  describe("risk", () => {
    const mockReturns = [0.01, -0.02, 0.005];

    it("calls POST /api/v1/risk/var", async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { status: "success", data: {} },
      });
      await apiService.risk.calculateVaR({
        returns: mockReturns,
        confidence_level: 0.95,
      });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/risk/var",
        expect.any(Object),
      );
    });

    it("calls POST /api/v1/risk/cvar", async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { status: "success", data: {} },
      });
      await apiService.risk.calculateCVaR({
        returns: mockReturns,
        confidence_level: 0.95,
      });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/risk/cvar",
        expect.any(Object),
      );
    });

    it("calls POST /api/v1/risk/sharpe-ratio", async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { status: "success", data: {} },
      });
      await apiService.risk.calculateSharpeRatio({ returns: mockReturns });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/risk/sharpe-ratio",
        expect.any(Object),
      );
    });

    it("calls POST /api/v1/risk/max-drawdown", async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { status: "success", data: {} },
      });
      await apiService.risk.calculateMaxDrawdown({ returns: mockReturns });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/risk/max-drawdown",
        expect.any(Object),
      );
    });

    it("calls POST /api/v1/risk/metrics (not GET)", async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { status: "success", data: {} },
      });
      await apiService.risk.getMetrics({ portfolio_id: 1 });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/risk/metrics",
        { portfolio_id: 1 },
      );
      expect(mockAxiosInstance.get).not.toHaveBeenCalled();
    });

    it("calls POST /api/v1/risk/efficient-frontier", async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { status: "success", data: {} },
      });
      await apiService.risk.getEfficientFrontier({ returns: mockReturns });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/risk/efficient-frontier",
        expect.any(Object),
      );
    });
  });

  describe("optimization", () => {
    it("calls POST /api/v1/optimization/optimize", async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { status: "success", data: {} },
      });
      await apiService.optimization.optimize({ risk_tolerance: 50 });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/v1/optimization/optimize",
        { risk_tolerance: 50 },
      );
    });
  });
});
