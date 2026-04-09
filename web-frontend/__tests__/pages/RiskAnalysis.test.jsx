import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthProvider } from "../../src/context/AuthContext";
import { PortfolioProvider } from "../../src/context/PortfolioContext";
import { RiskAnalysisProvider } from "../../src/context/RiskAnalysisContext";
import RiskAnalysis from "../../src/pages/RiskAnalysis";

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
      calculateVaR: vi
        .fn()
        .mockResolvedValue({ status: "success", data: { var_amount: 4000 } }),
      calculateCVaR: vi
        .fn()
        .mockResolvedValue({ status: "success", data: { cvar_amount: 5000 } }),
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

import apiService from "../../src/services/apiService";

const renderRiskAnalysis = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <PortfolioProvider>
          <RiskAnalysisProvider>
            <RiskAnalysis />
          </RiskAnalysisProvider>
        </PortfolioProvider>
      </AuthProvider>
    </MemoryRouter>,
  );

describe("RiskAnalysis Page", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the page heading", () => {
    renderRiskAnalysis();
    expect(
      screen.getByRole("heading", { name: /risk analysis/i }),
    ).toBeInTheDocument();
  });

  it("renders risk metrics summary section", () => {
    renderRiskAnalysis();
    expect(screen.getByText(/risk metrics summary/i)).toBeInTheDocument();
  });

  it("renders Value at Risk in summary", () => {
    renderRiskAnalysis();
    expect(screen.getAllByText(/value at risk/i).length).toBeGreaterThan(0);
  });

  it("renders CVaR in summary", () => {
    renderRiskAnalysis();
    expect(screen.getByText(/cvar/i)).toBeInTheDocument();
  });

  it("renders all 5 tabs", () => {
    renderRiskAnalysis();
    expect(
      screen.getByRole("tab", { name: /value at risk/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /cvar/i })).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /stress testing/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /correlation/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /risk contribution/i }),
    ).toBeInTheDocument();
  });

  it("renders Export Report button", () => {
    renderRiskAnalysis();
    expect(
      screen.getByRole("button", { name: /export report/i }),
    ).toBeInTheDocument();
  });

  it("VaR tab: renders Calculate VaR button", () => {
    renderRiskAnalysis();
    expect(
      screen.getByRole("button", { name: /calculate var/i }),
    ).toBeInTheDocument();
  });

  it("VaR tab: Calculate VaR calls both VaR and CVaR APIs", async () => {
    const user = userEvent.setup();
    renderRiskAnalysis();
    await user.click(screen.getByRole("button", { name: /calculate var/i }));
    await waitFor(() => {
      expect(apiService.risk.calculateVaR).toHaveBeenCalledOnce();
      expect(apiService.risk.calculateCVaR).toHaveBeenCalledOnce();
    });
  });

  it("switches to CVaR tab on click", async () => {
    const user = userEvent.setup();
    renderRiskAnalysis();
    await user.click(screen.getByRole("tab", { name: /cvar/i }));
    await waitFor(() =>
      expect(screen.getByText(/expected shortfall/i)).toBeInTheDocument(),
    );
  });

  it("switches to Stress Testing tab on click", async () => {
    const user = userEvent.setup();
    renderRiskAnalysis();
    await user.click(screen.getByRole("tab", { name: /stress testing/i }));
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /run stress test/i }),
      ).toBeInTheDocument(),
    );
  });

  it("Stress test run updates result display", async () => {
    const user = userEvent.setup();
    renderRiskAnalysis();
    await user.click(screen.getByRole("tab", { name: /stress testing/i }));
    await user.click(screen.getByRole("button", { name: /run stress test/i }));
    await waitFor(() =>
      expect(screen.getAllByText(/equities/i).length).toBeGreaterThan(0),
    );
  });
});
