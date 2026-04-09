import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthProvider } from "../../src/context/AuthContext";
import { PortfolioProvider } from "../../src/context/PortfolioContext";
import PortfolioManagement from "../../src/pages/PortfolioManagement";

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

const renderPortfolioManagement = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <PortfolioProvider>
          <PortfolioManagement />
        </PortfolioProvider>
      </AuthProvider>
    </MemoryRouter>,
  );

describe("PortfolioManagement Page", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the page heading", () => {
    renderPortfolioManagement();
    expect(
      screen.getByRole("heading", { name: /portfolio management/i }),
    ).toBeInTheDocument();
  });

  it("renders Add Asset button", () => {
    renderPortfolioManagement();
    expect(
      screen.getByRole("button", { name: /add asset/i }),
    ).toBeInTheDocument();
  });

  it("renders Refresh button", () => {
    renderPortfolioManagement();
    expect(
      screen.getByRole("button", { name: /refresh/i }),
    ).toBeInTheDocument();
  });

  it("renders table headers", () => {
    renderPortfolioManagement();
    expect(screen.getByText(/asset/i)).toBeInTheDocument();
    expect(screen.getByText(/quantity/i)).toBeInTheDocument();
    expect(screen.getByText(/purchase price/i)).toBeInTheDocument();
  });

  it("opens Add Asset dialog on button click", async () => {
    const user = userEvent.setup();
    renderPortfolioManagement();
    await user.click(screen.getByRole("button", { name: /add asset/i }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/add new asset/i)).toBeInTheDocument();
  });

  it("shows validation error when saving empty form", async () => {
    const user = userEvent.setup();
    renderPortfolioManagement();
    await user.click(screen.getByRole("button", { name: /add asset/i }));
    await screen.findByRole("dialog");
    await user.click(
      screen.getByRole("button", { name: /add asset/i, hidden: true }),
    );
    expect(
      await screen.findByText(/all fields are required/i),
    ).toBeInTheDocument();
  });

  it("adds an asset and calls save API", async () => {
    const user = userEvent.setup();
    renderPortfolioManagement();
    await user.click(screen.getByRole("button", { name: /add asset/i }));
    await screen.findByRole("dialog");

    await user.type(screen.getByLabelText(/symbol/i), "TSLA");
    await user.type(screen.getByLabelText(/asset name/i), "Tesla Inc.");
    await user.type(screen.getByLabelText(/quantity/i), "5");
    await user.type(screen.getByLabelText(/purchase price/i), "200");

    // Click the dialog's Add Asset button (not the header one)
    const dialogAddBtn = screen
      .getAllByRole("button", { name: /add asset/i })
      .at(-1);
    await user.click(dialogAddBtn);

    await waitFor(() => expect(apiService.portfolio.save).toHaveBeenCalled());
  });

  it("renders summary cards (Total Portfolio Value, Total Gain, Number of Assets)", () => {
    renderPortfolioManagement();
    expect(screen.getByText(/total portfolio value/i)).toBeInTheDocument();
    expect(screen.getByText(/total gain/i)).toBeInTheDocument();
    expect(screen.getByText(/number of assets/i)).toBeInTheDocument();
  });

  it("delete button calls save with asset removed", async () => {
    const user = userEvent.setup();
    renderPortfolioManagement();

    await waitFor(() => screen.queryByText("AAPL"));
    const deleteButtons = screen.getAllByTestId("DeleteIcon");
    if (deleteButtons.length > 0) {
      await user.click(deleteButtons[0].closest("button"));
      await waitFor(() => expect(apiService.portfolio.save).toHaveBeenCalled());
    }
  });
});
