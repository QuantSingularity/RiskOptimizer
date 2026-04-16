import { useCallback, useEffect, useState } from "react";

export const useDashboardData = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dashboardData, setDashboardData] = useState({
    portfolioValue: 0,
    dailyChange: 0,
    dailyChangePercent: 0,
    riskScore: 0,
    sharpeRatio: 0,
    performanceData: [],
    assetAllocation: [],
    riskMetrics: {},
    recentTransactions: [],
  });

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Simulate a brief load for realism
      await new Promise((r) => setTimeout(r, 400));
      setDashboardData({
        portfolioValue: 124532.89,
        dailyChange: 1245.67,
        dailyChangePercent: 1.02,
        riskScore: 65,
        sharpeRatio: 1.87,
        performanceData: generatePerformanceData(),
        assetAllocation: [
          { id: 0, name: "Stocks", value: 60, color: "#2196f3" },
          { id: 1, name: "Bonds", value: 20, color: "#4caf50" },
          { id: 2, name: "Crypto", value: 10, color: "#ff9800" },
          { id: 3, name: "Cash", value: 5, color: "#9e9e9e" },
          { id: 4, name: "Gold", value: 5, color: "#ffc107" },
        ],
        riskMetrics: {
          valueAtRisk: 4532.12,
          maxDrawdown: -12.4,
          volatility: 14.2,
          beta: 0.85,
        },
        recentTransactions: [
          {
            date: "2026-04-10",
            asset: "AAPL",
            type: "Buy",
            amount: "$2,500.00",
          },
          {
            date: "2026-04-07",
            asset: "TSLA",
            type: "Sell",
            amount: "$1,800.00",
          },
          {
            date: "2026-04-03",
            asset: "BTC",
            type: "Buy",
            amount: "$3,000.00",
          },
          {
            date: "2026-03-28",
            asset: "MSFT",
            type: "Buy",
            amount: "$3,200.00",
          },
          {
            date: "2026-03-20",
            asset: "GLD",
            type: "Sell",
            amount: "$2,100.00",
          },
        ],
      });
    } catch (err) {
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  return { loading, error, dashboardData, reload: loadDashboardData };
};

// ─── Data generators ──────────────────────────────────────────────────────────
function generatePerformanceData() {
  const data = [];
  const now = new Date();
  let value = 100000;
  for (let i = 365; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    value = Math.max(80000, value + (Math.random() - 0.45) * 500);
    data.push({
      date: d.toISOString().split("T")[0],
      value: Math.round(value * 100) / 100,
    });
  }
  return data;
}

export default useDashboardData;
