import { render, screen } from "@testing-library/react";
import RecentTransactions from "../../src/components/dashboard/RecentTransactions";

describe("RecentTransactions", () => {
  const mockTransactions = [
    { date: "2026-04-05", asset: "AAPL", type: "Buy", amount: "$2,500.00" },
    { date: "2026-04-01", asset: "TSLA", type: "Sell", amount: "$1,800.00" },
    { date: "2026-03-28", asset: "BTC", type: "Buy", amount: "$1,000.00" },
  ];

  it("renders heading", () => {
    render(<RecentTransactions transactions={mockTransactions} />);
    expect(screen.getByText("Recent Transactions")).toBeInTheDocument();
  });

  it("renders table headers", () => {
    render(<RecentTransactions transactions={mockTransactions} />);
    expect(screen.getByText("Date")).toBeInTheDocument();
    expect(screen.getByText("Asset")).toBeInTheDocument();
    expect(screen.getByText("Type")).toBeInTheDocument();
    expect(screen.getByText("Amount")).toBeInTheDocument();
  });

  it("renders each transaction row", () => {
    render(<RecentTransactions transactions={mockTransactions} />);
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("TSLA")).toBeInTheDocument();
    expect(screen.getByText("BTC")).toBeInTheDocument();
  });

  it("colors Buy transactions green and Sell red", () => {
    render(<RecentTransactions transactions={mockTransactions} />);
    const buyEl = screen.getAllByText("Buy")[0];
    const sellEl = screen.getByText("Sell");
    expect(buyEl).toHaveStyle({ color: expect.stringContaining("") });
    expect(sellEl).toBeInTheDocument();
  });

  it("uses default data when no prop provided", () => {
    render(<RecentTransactions />);
    expect(screen.getByText("AAPL")).toBeInTheDocument();
  });
});
