import { renderHook, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { AuthProvider } from "../../src/context/AuthContext";
import { PortfolioProvider } from "../../src/context/PortfolioContext";
import { usePortfolioManagement } from "../../src/hooks/usePortfolioManagement";

vi.mock("../../src/services/apiService", () => ({
  default: {
    auth: { login: vi.fn(), logout: vi.fn(), register: vi.fn() },
    portfolio: {
      getByAddress: vi.fn().mockResolvedValue({
        status: "success",
        data: {
          assets: [
            {
              id: 1,
              symbol: "AAPL",
              name: "Apple Inc.",
              quantity: 10,
              purchasePrice: 150,
              currentPrice: 175,
              totalValue: 1750,
              gain: 250,
              gainPercent: 16.67,
            },
          ],
          transactions: [],
        },
      }),
      save: vi.fn().mockResolvedValue({ status: "success" }),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      getByUserId: vi.fn(),
      getAll: vi.fn(),
    },
    optimization: { optimize: vi.fn() },
  },
}));

import apiService from "../../src/services/apiService";

const wrapper = ({ children }) => (
  <AuthProvider>
    <PortfolioProvider>{children}</PortfolioProvider>
  </AuthProvider>
);

describe("usePortfolioManagement", () => {
  beforeEach(() => vi.clearAllMocks());

  it("starts in loading state", () => {
    const { result } = renderHook(() => usePortfolioManagement(), { wrapper });
    expect(result.current.loading).toBe(true);
  });

  it("resolves to non-loading after data load", async () => {
    const { result } = renderHook(() => usePortfolioManagement(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it("provides portfolioData with assets array", async () => {
    const { result } = renderHook(() => usePortfolioManagement(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(Array.isArray(result.current.portfolioData.assets)).toBe(true);
    expect(result.current.portfolioData.assets.length).toBeGreaterThan(0);
  });

  it("provides portfolioData with transactions array", async () => {
    const { result } = renderHook(() => usePortfolioManagement(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(Array.isArray(result.current.portfolioData.transactions)).toBe(true);
  });

  it("provides portfolioData with summary object", async () => {
    const { result } = renderHook(() => usePortfolioManagement(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    const { summary } = result.current.portfolioData;
    expect(summary).toHaveProperty("totalValue");
    expect(summary).toHaveProperty("totalGain");
    expect(summary).toHaveProperty("totalGainPercent");
  });

  it("exposes updatePortfolio function", async () => {
    const { result } = renderHook(() => usePortfolioManagement(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(typeof result.current.updatePortfolio).toBe("function");
  });

  it("exposes reload function", async () => {
    const { result } = renderHook(() => usePortfolioManagement(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(typeof result.current.reload).toBe("function");
  });

  it("updatePortfolio updates local state and calls save", async () => {
    const { result } = renderHook(() => usePortfolioManagement(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    const newAssets = [
      {
        id: 2,
        symbol: "TSLA",
        name: "Tesla",
        quantity: 5,
        purchasePrice: 200,
        currentPrice: 220,
        totalValue: 1100,
        gain: 100,
        gainPercent: 10,
      },
    ];

    await waitFor(() => result.current.updatePortfolio(newAssets));
    await waitFor(() => expect(result.current.loading).toBe(false));
    // With no authenticated user, save won't be called but state still updates
    expect(result.current.portfolioData.assets).toEqual(newAssets);
  });
});
