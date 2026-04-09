import { renderHook, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { useDashboardData } from "../../src/hooks/useDashboardData";
import { AuthProvider } from "../../src/context/AuthContext";
import { PortfolioProvider } from "../../src/context/PortfolioContext";
import { RiskAnalysisProvider } from "../../src/context/RiskAnalysisContext";

vi.mock("../../src/services/apiService", () => ({
  default: {
    auth: { login: vi.fn(), logout: vi.fn(), register: vi.fn() },
    portfolio: {
      getByAddress: vi
        .fn()
        .mockResolvedValue({ status: "success", data: { assets: [] } }),
      save: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      getByUserId: vi.fn(),
      getAll: vi.fn(),
    },
    risk: {
      calculateVaR: vi.fn(),
      calculateCVaR: vi.fn(),
      calculateSharpeRatio: vi.fn(),
      calculateMaxDrawdown: vi.fn(),
      getMetrics: vi.fn(),
      getEfficientFrontier: vi.fn(),
    },
    optimization: {
      optimize: vi.fn(),
      efficientFrontier: vi.fn(),
      getConstraints: vi.fn(),
    },
  },
}));

const wrapper = ({ children }) => (
  <AuthProvider>
    <PortfolioProvider>
      <RiskAnalysisProvider>{children}</RiskAnalysisProvider>
    </PortfolioProvider>
  </AuthProvider>
);

describe("useDashboardData", () => {
  it("starts in loading state", () => {
    const { result } = renderHook(() => useDashboardData(), { wrapper });
    expect(result.current.loading).toBe(true);
  });

  it("resolves to non-loading after data fetch", async () => {
    const { result } = renderHook(() => useDashboardData(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it("provides portfolioValue in dashboardData", async () => {
    const { result } = renderHook(() => useDashboardData(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(typeof result.current.dashboardData.portfolioValue).toBe("number");
  });

  it("provides assetAllocation array", async () => {
    const { result } = renderHook(() => useDashboardData(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(Array.isArray(result.current.dashboardData.assetAllocation)).toBe(
      true,
    );
    expect(result.current.dashboardData.assetAllocation.length).toBeGreaterThan(
      0,
    );
  });

  it("provides recentTransactions array", async () => {
    const { result } = renderHook(() => useDashboardData(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(Array.isArray(result.current.dashboardData.recentTransactions)).toBe(
      true,
    );
  });

  it("provides performanceData array with date/value", async () => {
    const { result } = renderHook(() => useDashboardData(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    const perf = result.current.dashboardData.performanceData;
    expect(Array.isArray(perf)).toBe(true);
    if (perf.length > 0) {
      expect(perf[0]).toHaveProperty("date");
      expect(perf[0]).toHaveProperty("value");
    }
  });

  it("exposes a reload function", async () => {
    const { result } = renderHook(() => useDashboardData(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(typeof result.current.reload).toBe("function");
  });
});
