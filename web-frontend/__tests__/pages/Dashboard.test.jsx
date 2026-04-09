import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthProvider } from "../../src/context/AuthContext";
import { PortfolioProvider } from "../../src/context/PortfolioContext";
import { RiskAnalysisProvider } from "../../src/context/RiskAnalysisContext";
import Dashboard from "../../src/pages/Dashboard";

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

vi.mock("@mui/x-charts/PieChart", () => ({
  PieChart: () => <div data-testid="pie-chart" />,
}));

vi.mock("@mui/x-charts/LineChart", () => ({
  LineChart: () => <div data-testid="line-chart" />,
}));

const renderDashboard = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <PortfolioProvider>
          <RiskAnalysisProvider>
            <Dashboard />
          </RiskAnalysisProvider>
        </PortfolioProvider>
      </AuthProvider>
    </MemoryRouter>,
  );

describe("Dashboard Page", () => {
  it("renders loading spinner initially", () => {
    renderDashboard();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("renders the Dashboard heading after loading", async () => {
    renderDashboard();
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: /dashboard/i }),
      ).toBeInTheDocument(),
    );
  });

  it("renders portfolio value card", async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/total portfolio value/i)).toBeInTheDocument(),
    );
  });

  it("renders daily change card", async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/daily change/i)).toBeInTheDocument(),
    );
  });

  it("renders risk score card", async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/risk score/i)).toBeInTheDocument(),
    );
  });

  it("renders sharpe ratio card", async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/sharpe ratio/i)).toBeInTheDocument(),
    );
  });

  it("renders performance chart component", async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByTestId("line-chart")).toBeInTheDocument(),
    );
  });

  it("renders asset allocation pie chart", async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByTestId("pie-chart")).toBeInTheDocument(),
    );
  });

  it("renders Refresh Data button", async () => {
    renderDashboard();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /refresh data/i }),
      ).toBeInTheDocument(),
    );
  });

  it("uses Link for navigation (no full page reload)", async () => {
    renderDashboard();
    await waitFor(() => screen.getByText(/view detailed analysis/i));
    const link = screen.getByText(/view detailed analysis/i).closest("a");
    expect(link).toHaveAttribute("href", "/risk-analysis");
  });

  it("Refresh Data button triggers reload", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await waitFor(() => screen.getByRole("button", { name: /refresh data/i }));
    await user.click(screen.getByRole("button", { name: /refresh data/i }));
    // Should not crash, reload runs again
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: /dashboard/i }),
      ).toBeInTheDocument(),
    );
  });
});
