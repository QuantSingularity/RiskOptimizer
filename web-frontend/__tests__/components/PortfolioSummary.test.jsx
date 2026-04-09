import { render, screen } from "@testing-library/react";
import PortfolioSummary from "../../src/components/dashboard/PortfolioSummary";

describe("PortfolioSummary", () => {
  it("renders heading", () => {
    render(<PortfolioSummary />);
    expect(screen.getByText("Portfolio Summary")).toBeInTheDocument();
  });

  it("shows no-data message when portfolioData is null", () => {
    render(<PortfolioSummary portfolioData={null} />);
    expect(screen.getByText(/no portfolio data/i)).toBeInTheDocument();
  });

  it("displays asset count from portfolioData", () => {
    const data = { assets: [{ id: 1 }, { id: 2 }], totalValue: 50000 };
    render(<PortfolioSummary portfolioData={data} />);
    expect(screen.getByText(/total assets: 2/i)).toBeInTheDocument();
  });

  it("displays total value from portfolioData", () => {
    const data = { assets: [], totalValue: "12345.67" };
    render(<PortfolioSummary portfolioData={data} />);
    expect(screen.getByText(/12345.67/)).toBeInTheDocument();
  });
});
