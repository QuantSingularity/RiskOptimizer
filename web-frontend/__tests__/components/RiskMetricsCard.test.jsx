import { render, screen } from "@testing-library/react";
import RiskMetricsCard from "../../src/components/dashboard/RiskMetricsCard";

describe("RiskMetricsCard", () => {
  const mockMetrics = {
    valueAtRisk: "$5,000.00",
    maxDrawdown: "-15.0%",
    volatility: "18.5%",
    beta: "1.10",
  };

  it("renders heading", () => {
    render(<RiskMetricsCard />);
    expect(screen.getByText("Risk Metrics")).toBeInTheDocument();
  });

  it("renders all four metric labels", () => {
    render(<RiskMetricsCard />);
    expect(screen.getByText(/value at risk/i)).toBeInTheDocument();
    expect(screen.getByText(/max drawdown/i)).toBeInTheDocument();
    expect(screen.getByText(/volatility/i)).toBeInTheDocument();
    expect(screen.getByText(/beta/i)).toBeInTheDocument();
  });

  it("renders provided metric values", () => {
    render(<RiskMetricsCard riskMetrics={mockMetrics} />);
    expect(screen.getByText("$5,000.00")).toBeInTheDocument();
    expect(screen.getByText("-15.0%")).toBeInTheDocument();
    expect(screen.getByText("18.5%")).toBeInTheDocument();
    expect(screen.getByText("1.10")).toBeInTheDocument();
  });

  it("renders default values when no prop provided", () => {
    render(<RiskMetricsCard />);
    expect(screen.getByText("$4,532.12")).toBeInTheDocument();
  });
});
