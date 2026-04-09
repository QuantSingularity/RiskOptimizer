import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import {
  PortfolioProvider,
  usePortfolio,
} from "../../src/context/PortfolioContext";
import apiService from "../../src/services/apiService";

vi.mock("../../src/services/apiService", () => ({
  default: {
    portfolio: {
      getByAddress: vi.fn(),
      getByUserId: vi.fn(),
      create: vi.fn(),
      save: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      getAll: vi.fn(),
    },
    optimization: { optimize: vi.fn() },
  },
}));

const TestConsumer = () => {
  const {
    portfolio,
    loading,
    error,
    fetchPortfolio,
    createPortfolio,
    deletePortfolio,
    clearError,
  } = usePortfolio();
  return (
    <div>
      {loading && <span>Loading</span>}
      {error && <span data-testid="error">{error}</span>}
      {portfolio && (
        <span data-testid="portfolio">{JSON.stringify(portfolio)}</span>
      )}
      <button onClick={() => fetchPortfolio("0xabc")}>Fetch</button>
      <button
        onClick={() => createPortfolio({ user_address: "0xabc", assets: [] })}
      >
        Create
      </button>
      <button onClick={() => deletePortfolio(1)}>Delete</button>
      <button onClick={clearError}>ClearError</button>
    </div>
  );
};

const renderWithProvider = () =>
  render(
    <PortfolioProvider>
      <TestConsumer />
    </PortfolioProvider>,
  );

describe("PortfolioContext", () => {
  beforeEach(() => vi.clearAllMocks());

  it("throws if used outside provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow(
      "usePortfolio must be used within a PortfolioProvider",
    );
    spy.mockRestore();
  });

  it("starts with null portfolio and no error", () => {
    renderWithProvider();
    expect(screen.queryByTestId("portfolio")).not.toBeInTheDocument();
    expect(screen.queryByTestId("error")).not.toBeInTheDocument();
  });

  it("sets portfolio on successful fetchPortfolio", async () => {
    apiService.portfolio.getByAddress.mockResolvedValue({
      status: "success",
      data: { id: 1, assets: [{ id: 1, symbol: "AAPL" }] },
    });
    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Fetch"));
    await waitFor(() =>
      expect(screen.getByTestId("portfolio")).toHaveTextContent("AAPL"),
    );
  });

  it("sets error on failed fetchPortfolio", async () => {
    apiService.portfolio.getByAddress.mockRejectedValue(
      new Error("Network error"),
    );
    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Fetch"));
    await waitFor(() =>
      expect(screen.getByTestId("error")).toHaveTextContent("Network error"),
    );
  });

  it("calls correct endpoint for createPortfolio", async () => {
    apiService.portfolio.create.mockResolvedValue({
      status: "success",
      data: { id: 2, assets: [] },
    });
    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Create"));
    await waitFor(() =>
      expect(apiService.portfolio.create).toHaveBeenCalledWith({
        user_address: "0xabc",
        assets: [],
      }),
    );
  });

  it("calls correct endpoint for deletePortfolio", async () => {
    apiService.portfolio.delete.mockResolvedValue({ status: "success" });
    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Delete"));
    await waitFor(() =>
      expect(apiService.portfolio.delete).toHaveBeenCalledWith(1),
    );
  });

  it("clearError resets error state", async () => {
    apiService.portfolio.getByAddress.mockRejectedValue(new Error("err"));
    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Fetch"));
    await waitFor(() =>
      expect(screen.getByTestId("error")).toBeInTheDocument(),
    );
    await user.click(screen.getByText("ClearError"));
    await waitFor(() =>
      expect(screen.queryByTestId("error")).not.toBeInTheDocument(),
    );
  });
});
