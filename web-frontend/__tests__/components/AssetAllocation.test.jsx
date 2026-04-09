import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import AssetAllocation from "../../src/components/dashboard/AssetAllocation";

vi.mock("@mui/x-charts/PieChart", () => ({
  PieChart: ({ series }) => (
    <div data-testid="pie-chart">
      {series[0].data.map((item) => (
        <span key={item.id ?? item.name} data-testid={`slice-${item.name}`}>
          {item.name}:{item.value}
        </span>
      ))}
    </div>
  ),
}));

describe("AssetAllocation", () => {
  const mockAllocation = [
    { id: 0, name: "Stocks", value: 60, color: "#2196f3" },
    { id: 1, name: "Bonds", value: 30, color: "#4caf50" },
    { id: 2, name: "Cash", value: 10, color: "#9e9e9e" },
  ];

  it("renders the heading", () => {
    render(<AssetAllocation allocation={mockAllocation} />);
    expect(screen.getByText("Asset Allocation")).toBeInTheDocument();
  });

  it("renders a pie chart", () => {
    render(<AssetAllocation allocation={mockAllocation} />);
    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
  });

  it("renders each allocation item in the legend", () => {
    render(<AssetAllocation allocation={mockAllocation} />);
    expect(screen.getByText(/Stocks: 60%/)).toBeInTheDocument();
    expect(screen.getByText(/Bonds: 30%/)).toBeInTheDocument();
    expect(screen.getByText(/Cash: 10%/)).toBeInTheDocument();
  });

  it("renders default allocation when no prop provided", () => {
    render(<AssetAllocation />);
    expect(screen.getByText(/Stocks: 60%/)).toBeInTheDocument();
    expect(screen.getByText(/Crypto: 10%/)).toBeInTheDocument();
  });
});
