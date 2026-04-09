import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthProvider } from "../../src/context/AuthContext";
import { PortfolioProvider } from "../../src/context/PortfolioContext";
import { RiskAnalysisProvider } from "../../src/context/RiskAnalysisContext";
import Optimization from "../../src/pages/Optimization";

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
    optimization: {
      optimize: vi
        .fn()
        .mockResolvedValue({ status: "success", data: { sharpe: 1.9 } }),
      efficientFrontier: vi.fn(),
      getConstraints: vi.fn(),
    },
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

const renderOptimization = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <PortfolioProvider>
          <RiskAnalysisProvider>
            <Optimization />
          </RiskAnalysisProvider>
        </PortfolioProvider>
      </AuthProvider>
    </MemoryRouter>,
  );

describe("Optimization Page", () => {
  it("renders the page heading", () => {
    renderOptimization();
    expect(
      screen.getByRole("heading", { name: /portfolio optimization/i }),
    ).toBeInTheDocument();
  });

  it("renders optimization parameters card", () => {
    renderOptimization();
    expect(screen.getByText(/optimization parameters/i)).toBeInTheDocument();
  });

  it("renders risk tolerance slider", () => {
    renderOptimization();
    expect(screen.getByRole("slider")).toBeInTheDocument();
  });

  it("renders Run Optimization button", () => {
    renderOptimization();
    expect(
      screen.getByRole("button", { name: /run optimization/i }),
    ).toBeInTheDocument();
  });

  it("renders Save Optimization button", () => {
    renderOptimization();
    expect(
      screen.getByRole("button", { name: /save optimization/i }),
    ).toBeInTheDocument();
  });

  it("shows risk tolerance label based on slider value", () => {
    renderOptimization();
    expect(screen.getByText(/moderate/i)).toBeInTheDocument();
  });

  it("renders optimization results card", () => {
    renderOptimization();
    expect(screen.getByText(/optimization results/i)).toBeInTheDocument();
  });

  it("renders expected return, risk, and sharpe metrics", () => {
    renderOptimization();
    expect(screen.getByText(/expected return/i)).toBeInTheDocument();
    expect(screen.getByText(/expected risk/i)).toBeInTheDocument();
    expect(screen.getByText(/sharpe ratio/i)).toBeInTheDocument();
  });

  it("renders optimization method selector", () => {
    renderOptimization();
    expect(screen.getByText(/optimization method/i)).toBeInTheDocument();
  });

  it("renders time horizon selector", () => {
    renderOptimization();
    expect(screen.getByText(/time horizon/i)).toBeInTheDocument();
  });

  it("renders Apply Optimization button", () => {
    renderOptimization();
    expect(
      screen.getByRole("button", { name: /apply optimization/i }),
    ).toBeInTheDocument();
  });
});
