import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PortfolioProvider } from "../context/PortfolioContext";
import apiService from "../services/apiService";
import Optimization from "./Optimization";

vi.mock("../services/apiService", () => ({
  default: {
    optimization: {
      getSymbols: vi.fn(),
      optimize: vi.fn(),
      efficientFrontier: vi.fn(),
    },
  },
}));

vi.mock("recharts", async () => {
  const actual = await vi.importActual("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }) => <div>{children}</div>,
  };
});

const SYMBOLS = ["AAPL", "MSFT", "TSLA"];

const optimizeResponse = {
  status: "success",
  data: {
    optimized_allocation: { AAPL: 0.5, MSFT: 0.3, TSLA: 0.2 },
    performance_metrics: {
      expected_return: 0.123,
      volatility: 0.21,
      sharpe_ratio: 0.49,
    },
    model_type: "ml",
    method: "utility",
    risk_tolerance: 6,
  },
};

const frontierResponse = {
  status: "success",
  data: {
    frontier: [
      {
        volatility: 0.15,
        expected_return: 0.08,
        sharpe_ratio: 0.4,
        weights: {},
      },
      {
        volatility: 0.21,
        expected_return: 0.12,
        sharpe_ratio: 0.5,
        weights: {},
      },
    ],
  },
};

const renderPage = () =>
  render(
    <PortfolioProvider>
      <Optimization />
    </PortfolioProvider>,
  );

describe("Optimization page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiService.optimization.getSymbols.mockResolvedValue({
      data: { symbols: SYMBOLS },
    });
    apiService.optimization.optimize.mockResolvedValue(optimizeResponse);
    apiService.optimization.efficientFrontier.mockResolvedValue(
      frontierResponse,
    );
  });

  it("loads symbols from the API and selects them all", async () => {
    renderPage();
    expect(await screen.findByText("Assets (3 selected)")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
  });

  it("sends the selected symbols and renders real results", async () => {
    renderPage();
    await screen.findByText("Assets (3 selected)");
    fireEvent.click(screen.getByRole("button", { name: /run optimization/i }));

    expect(await screen.findByText("12.3%")).toBeInTheDocument();
    expect(screen.getByText("21.0%")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByText(/ML return model/)).toBeInTheDocument();

    expect(apiService.optimization.optimize).toHaveBeenCalledWith({
      symbols: SYMBOLS,
      risk_tolerance: 6,
      method: "utility",
      min_weight: 0,
      max_weight: 1,
    });
    expect(apiService.optimization.efficientFrontier).toHaveBeenCalledWith(
      expect.objectContaining({ symbols: SYMBOLS, points: 20 }),
    );
  });

  it("disables the run button below the minimum asset count", async () => {
    renderPage();
    await screen.findByText("Assets (3 selected)");
    fireEvent.click(screen.getByText("MSFT"));
    fireEvent.click(screen.getByText("TSLA"));
    expect(screen.getByText("Assets (1 selected)")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /run optimization/i }),
    ).toBeDisabled();
  });

  it("shows the backend error message and no results", async () => {
    apiService.optimization.optimize.mockRejectedValue(
      new Error("risk_tolerance must be between 1.0 and 10.0"),
    );
    renderPage();
    await screen.findByText("Assets (3 selected)");
    fireEvent.click(screen.getByRole("button", { name: /run optimization/i }));
    expect(
      await screen.findByText(/risk_tolerance must be between/),
    ).toBeInTheDocument();
    expect(screen.queryByText("Sharpe Ratio")).not.toBeInTheDocument();
  });

  it("reports a symbol loading failure", async () => {
    apiService.optimization.getSymbols.mockRejectedValue(
      new Error("Network error. Please check your connection."),
    );
    renderPage();
    await waitFor(() =>
      expect(screen.getByText(/Network error/)).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: /run optimization/i }),
    ).toBeDisabled();
  });
});
