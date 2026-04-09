import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import PerformanceChart from "../../src/components/dashboard/PerformanceChart";

vi.mock("@mui/x-charts/LineChart", () => ({
  LineChart: ({ series, xAxis }) => (
    <div data-testid="line-chart">
      <span data-testid="series-count">{series.length}</span>
      <span data-testid="x-labels-count">{xAxis[0].data.length}</span>
    </div>
  ),
}));

describe("PerformanceChart", () => {
  const mockData = Array.from({ length: 30 }, (_, i) => ({
    date: `2026-01-${String(i + 1).padStart(2, "0")}`,
    value: 100000 + i * 500,
  }));

  it("renders the heading", () => {
    render(<PerformanceChart performanceData={mockData} />);
    expect(screen.getByText("Portfolio Performance")).toBeInTheDocument();
  });

  it("renders the line chart", () => {
    render(<PerformanceChart performanceData={mockData} />);
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("renders with exactly one series", () => {
    render(<PerformanceChart performanceData={mockData} />);
    expect(screen.getByTestId("series-count").textContent).toBe("1");
  });

  it("uses default data when no prop provided", () => {
    render(<PerformanceChart />);
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("renders at most 30 x-axis labels", () => {
    render(<PerformanceChart performanceData={mockData} />);
    const count = parseInt(
      screen.getByTestId("x-labels-count").textContent,
      10,
    );
    expect(count).toBeLessThanOrEqual(30);
  });
});
