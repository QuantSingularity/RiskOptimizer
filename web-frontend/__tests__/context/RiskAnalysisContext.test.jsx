import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import {
  RiskAnalysisProvider,
  useRiskAnalysis,
} from "../../src/context/RiskAnalysisContext";
import apiService from "../../src/services/apiService";

vi.mock("../../src/services/apiService", () => ({
  default: {
    risk: {
      calculateVaR: vi.fn(),
      calculateCVaR: vi.fn(),
      calculateSharpeRatio: vi.fn(),
      calculateMaxDrawdown: vi.fn(),
      getMetrics: vi.fn(),
      getEfficientFrontier: vi.fn(),
    },
  },
}));

const TestConsumer = () => {
  const {
    varData,
    cvarData,
    sharpeData,
    maxDrawdownData,
    loading,
    error,
    calculateVaR,
    calculateCVaR,
    calculateSharpeRatio,
    calculateMaxDrawdown,
    clearRiskData,
  } = useRiskAnalysis();
  return (
    <div>
      {loading && <span>Loading</span>}
      {error && <span data-testid="error">{error}</span>}
      {varData && (
        <span data-testid="var-result">{JSON.stringify(varData)}</span>
      )}
      {cvarData && (
        <span data-testid="cvar-result">{JSON.stringify(cvarData)}</span>
      )}
      {sharpeData && (
        <span data-testid="sharpe-result">{JSON.stringify(sharpeData)}</span>
      )}
      {maxDrawdownData && (
        <span data-testid="drawdown-result">
          {JSON.stringify(maxDrawdownData)}
        </span>
      )}
      <button
        onClick={() => calculateVaR({ returns: [], confidence_level: 0.95 })}
      >
        Calc VaR
      </button>
      <button
        onClick={() => calculateCVaR({ returns: [], confidence_level: 0.95 })}
      >
        Calc CVaR
      </button>
      <button onClick={() => calculateSharpeRatio({ returns: [] })}>
        Calc Sharpe
      </button>
      <button onClick={() => calculateMaxDrawdown({ returns: [] })}>
        Calc Drawdown
      </button>
      <button onClick={clearRiskData}>Clear</button>
    </div>
  );
};

const renderWithProvider = () =>
  render(
    <RiskAnalysisProvider>
      <TestConsumer />
    </RiskAnalysisProvider>,
  );

describe("RiskAnalysisContext", () => {
  beforeEach(() => vi.clearAllMocks());

  it("provides initial empty state", () => {
    renderWithProvider();
    expect(screen.queryByTestId("var-result")).not.toBeInTheDocument();
    expect(screen.queryByTestId("error")).not.toBeInTheDocument();
  });

  it("calculateVaR sets varData on success", async () => {
    const mockData = { var_amount: 4532.12, confidence_level: 0.95 };
    apiService.risk.calculateVaR.mockResolvedValue({
      status: "success",
      data: mockData,
    });

    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Calc VaR"));

    await waitFor(() =>
      expect(screen.getByTestId("var-result")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("var-result").textContent).toContain("4532.12");
  });

  it("calculateVaR sets error on failure", async () => {
    apiService.risk.calculateVaR.mockRejectedValue(
      new Error("VaR calc failed"),
    );

    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Calc VaR"));

    await waitFor(() =>
      expect(screen.getByTestId("error")).toHaveTextContent("VaR calc failed"),
    );
  });

  it("calculateCVaR sets cvarData on success", async () => {
    const mockData = { cvar_amount: 5821.45 };
    apiService.risk.calculateCVaR.mockResolvedValue({
      status: "success",
      data: mockData,
    });

    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Calc CVaR"));

    await waitFor(() =>
      expect(screen.getByTestId("cvar-result")).toBeInTheDocument(),
    );
  });

  it("calculateSharpeRatio sets sharpeData on success", async () => {
    const mockData = { sharpe_ratio: 1.87 };
    apiService.risk.calculateSharpeRatio.mockResolvedValue({
      status: "success",
      data: mockData,
    });

    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Calc Sharpe"));

    await waitFor(() =>
      expect(screen.getByTestId("sharpe-result")).toBeInTheDocument(),
    );
  });

  it("calculateMaxDrawdown sets maxDrawdownData on success", async () => {
    const mockData = { max_drawdown: -0.124 };
    apiService.risk.calculateMaxDrawdown.mockResolvedValue({
      status: "success",
      data: mockData,
    });

    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Calc Drawdown"));

    await waitFor(() =>
      expect(screen.getByTestId("drawdown-result")).toBeInTheDocument(),
    );
  });

  it("clearRiskData removes all stored results and errors", async () => {
    const mockData = { var_amount: 4000 };
    apiService.risk.calculateVaR.mockResolvedValue({
      status: "success",
      data: mockData,
    });

    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Calc VaR"));
    await waitFor(() =>
      expect(screen.getByTestId("var-result")).toBeInTheDocument(),
    );

    await user.click(screen.getByText("Clear"));
    expect(screen.queryByTestId("var-result")).not.toBeInTheDocument();
    expect(screen.queryByTestId("error")).not.toBeInTheDocument();
  });

  it("throws when useRiskAnalysis used outside provider", () => {
    const BadComponent = () => {
      useRiskAnalysis();
      return null;
    };
    expect(() => render(<BadComponent />)).toThrow(
      "useRiskAnalysis must be used within a RiskAnalysisProvider",
    );
  });
});
