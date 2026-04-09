import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { usePortfolio } from "../context/PortfolioContext";
import { useRiskAnalysis } from "../context/RiskAnalysisContext";

export const useDashboardData = () => {
  const { user } = useAuth();
  const { fetchPortfolio, loading: portfolioLoading } = usePortfolio();
  const { loading: riskLoading } = useRiskAnalysis();
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
      if (user?.wallet_address || user?.address) {
        const address = user.wallet_address || user.address;
        await fetchPortfolio(address);
      }

      setDashboardData({
        portfolioValue: 124532.89,
        dailyChange: 1245.67,
        dailyChangePercent: 1.02,
        riskScore: 65,
        sharpeRatio: 1.87,
        performanceData: generateMockPerformanceData(),
        assetAllocation: generateMockAssetAllocation(),
        riskMetrics: {
          valueAtRisk: 4532.12,
          maxDrawdown: -12.4,
          volatility: 14.2,
          beta: 0.85,
        },
        recentTransactions: generateMockTransactions(),
      });
    } catch (err) {
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, [user, fetchPortfolio]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  return {
    loading: loading || portfolioLoading || riskLoading,
    error,
    dashboardData,
    reload: loadDashboardData,
  };
};

const generateMockPerformanceData = () => {
  const data = [];
  const now = new Date();
  let value = 100000;
  for (let i = 365; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    value = value + (Math.random() - 0.45) * 500;
    data.push({
      date: date.toISOString().split("T")[0],
      value: Math.max(value, 80000),
    });
  }
  return data;
};

const generateMockAssetAllocation = () => [
  { id: 0, name: "Stocks", value: 60, color: "#2196f3" },
  { id: 1, name: "Bonds", value: 20, color: "#4caf50" },
  { id: 2, name: "Crypto", value: 10, color: "#ff9800" },
  { id: 3, name: "Cash", value: 5, color: "#9e9e9e" },
  { id: 4, name: "Gold", value: 5, color: "#ffc107" },
];

const generateMockTransactions = () => [
  { date: "2026-04-05", asset: "AAPL", type: "Buy", amount: "$2,500.00" },
  { date: "2026-04-01", asset: "TSLA", type: "Sell", amount: "$1,800.00" },
  { date: "2026-03-28", asset: "BTC", type: "Buy", amount: "$1,000.00" },
  { date: "2026-03-15", asset: "MSFT", type: "Buy", amount: "$3,200.00" },
  { date: "2026-03-10", asset: "GLD", type: "Sell", amount: "$2,100.00" },
];

export default useDashboardData;
