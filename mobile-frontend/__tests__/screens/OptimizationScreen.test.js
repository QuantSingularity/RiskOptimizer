import { fireEvent, render, waitFor } from "@testing-library/react-native";
import OptimizationScreen from "../../src/screens/Optimize/OptimizationScreen";
import apiService from "../../src/services/apiService";

jest.mock("react-native-chart-kit", () => ({
  LineChart: () => null,
}));

jest.mock("../../src/services/apiService", () => ({
  __esModule: true,
  default: {
    getOptimizationSymbols: jest.fn(),
    optimizePortfolio: jest.fn(),
    getEfficientFrontier: jest.fn(),
  },
}));

const SYMBOLS = ["AAPL", "MSFT", "TSLA"];

const optimizeResponse = {
  data: {
    data: {
      optimized_allocation: { AAPL: 0.5, MSFT: 0.3, TSLA: 0.2 },
      performance_metrics: {
        expected_return: 0.123,
        volatility: 0.21,
        sharpe_ratio: 0.49,
      },
      model_type: "ml",
      method: "utility",
    },
  },
};

const frontierResponse = {
  data: {
    data: {
      frontier: [
        { volatility: 0.15, expected_return: 0.08 },
        { volatility: 0.21, expected_return: 0.12 },
      ],
    },
  },
};

describe("OptimizationScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    apiService.getOptimizationSymbols.mockResolvedValue({
      data: { data: { symbols: SYMBOLS } },
    });
    apiService.optimizePortfolio.mockResolvedValue(optimizeResponse);
    apiService.getEfficientFrontier.mockResolvedValue(frontierResponse);
  });

  it("loads symbols from the API and selects them all", async () => {
    const { findByText, getByTestId } = render(<OptimizationScreen />);
    expect(await findByText("Assets (3 selected)")).toBeTruthy();
    expect(getByTestId("asset-AAPL")).toBeTruthy();
  });

  it("sends the selection and renders real results", async () => {
    const { findByText, getByText } = render(<OptimizationScreen />);
    await findByText("Assets (3 selected)");
    fireEvent.press(getByText("Run Optimization"));

    expect(await findByText("12.3%")).toBeTruthy();
    expect(getByText("21%")).toBeTruthy();
    expect(getByText("33.3% to 50%")).toBeTruthy();
    expect(getByText(/ML return model/)).toBeTruthy();

    expect(apiService.optimizePortfolio).toHaveBeenCalledWith({
      symbols: SYMBOLS,
      risk_tolerance: 5,
      method: "utility",
      min_weight: 0,
      max_weight: 1,
    });
    expect(apiService.getEfficientFrontier).toHaveBeenCalledWith(
      expect.objectContaining({ symbols: SYMBOLS, points: 20 }),
    );
  });

  it("switches method and sends it", async () => {
    const { findByText, getByTestId, getByText } = render(
      <OptimizationScreen />,
    );
    await findByText("Assets (3 selected)");
    fireEvent.press(getByTestId("method-max_sharpe"));
    fireEvent.press(getByText("Run Optimization"));
    await waitFor(() =>
      expect(apiService.optimizePortfolio).toHaveBeenCalledWith(
        expect.objectContaining({ method: "max_sharpe" }),
      ),
    );
  });

  it("requires at least two assets", async () => {
    const { findByText, getByTestId, queryByText } = render(
      <OptimizationScreen />,
    );
    await findByText("Assets (3 selected)");
    fireEvent.press(getByTestId("asset-MSFT"));
    fireEvent.press(getByTestId("asset-TSLA"));
    expect(await findByText("Select at least 2 assets")).toBeTruthy();
    fireEvent.press(queryByText("Run Optimization"));
    expect(apiService.optimizePortfolio).not.toHaveBeenCalled();
  });

  it("shows the backend error message", async () => {
    apiService.optimizePortfolio.mockRejectedValue({
      response: { data: { error: { message: "weights are infeasible" } } },
    });
    const { findByText, getByText, queryByText } = render(
      <OptimizationScreen />,
    );
    await findByText("Assets (3 selected)");
    fireEvent.press(getByText("Run Optimization"));
    expect(await findByText("weights are infeasible")).toBeTruthy();
    expect(queryByText("Results")).toBeNull();
  });

  it("reports a failure to load symbols", async () => {
    apiService.getOptimizationSymbols.mockRejectedValue(
      new Error("Network Error"),
    );
    const { findByText } = render(<OptimizationScreen />);
    expect(await findByText("Network Error")).toBeTruthy();
  });
});
