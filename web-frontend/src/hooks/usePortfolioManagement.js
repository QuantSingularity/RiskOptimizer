import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { usePortfolio } from "../context/PortfolioContext";

export const usePortfolioManagement = () => {
  const { user } = useAuth();
  const {
    portfolio,
    fetchPortfolio,
    savePortfolio,
    loading: portfolioLoading,
    error: portfolioError,
  } = usePortfolio();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [portfolioData, setPortfolioData] = useState({
    assets: [],
    transactions: [],
    summary: {
      totalValue: 0,
      totalGain: 0,
      totalGainPercent: 0,
    },
  });

  const computeSummary = useCallback((assets) => {
    const totalValue = assets.reduce((s, a) => s + (a.totalValue || 0), 0);
    const totalCost = assets.reduce(
      (s, a) => s + (a.quantity * a.purchasePrice || 0),
      0,
    );
    const totalGain = totalValue - totalCost;
    const totalGainPercent = totalCost > 0 ? (totalGain / totalCost) * 100 : 0;
    return { totalValue, totalGain, totalGainPercent };
  }, []);

  const loadPortfolioData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const address = user?.wallet_address || user?.address;
      if (address) {
        await fetchPortfolio(address);
      }

      const assets = portfolio?.assets ?? generateMockAssets();
      const transactions =
        portfolio?.transactions ?? generateMockTransactions();

      setPortfolioData({
        assets,
        transactions,
        summary: computeSummary(assets),
      });
    } catch (err) {
      setError(err.message || "Failed to load portfolio data");
    } finally {
      setLoading(false);
    }
  }, [user, fetchPortfolio, portfolio, computeSummary]);

  useEffect(() => {
    loadPortfolioData();
  }, [loadPortfolioData]);

  const updatePortfolio = useCallback(
    async (updatedAssets) => {
      setLoading(true);
      setError(null);
      try {
        const address = user?.wallet_address || user?.address;
        if (address) {
          await savePortfolio({ user_address: address, assets: updatedAssets });
        }
        setPortfolioData((prev) => ({
          ...prev,
          assets: updatedAssets,
          summary: computeSummary(updatedAssets),
        }));
        return true;
      } catch (err) {
        setError(err.message || "Failed to update portfolio");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [user, savePortfolio, computeSummary],
  );

  return {
    loading: loading || portfolioLoading,
    error: error || portfolioError,
    portfolioData,
    updatePortfolio,
    reload: loadPortfolioData,
  };
};

const generateMockAssets = () => [
  {
    id: 1,
    name: "Apple Inc.",
    symbol: "AAPL",
    quantity: 50,
    purchasePrice: 150,
    currentPrice: 178.5,
    totalValue: 8925,
    gain: 1425,
    gainPercent: 19.0,
    allocation: 15,
  },
  {
    id: 2,
    name: "Microsoft Corp.",
    symbol: "MSFT",
    quantity: 30,
    purchasePrice: 280,
    currentPrice: 415.2,
    totalValue: 12456,
    gain: 4056,
    gainPercent: 48.3,
    allocation: 12,
  },
  {
    id: 3,
    name: "Amazon.com Inc.",
    symbol: "AMZN",
    quantity: 25,
    purchasePrice: 180,
    currentPrice: 198.7,
    totalValue: 4967.5,
    gain: 467.5,
    gainPercent: 10.4,
    allocation: 10,
  },
  {
    id: 4,
    name: "Tesla Inc.",
    symbol: "TSLA",
    quantity: 40,
    purchasePrice: 220,
    currentPrice: 175.3,
    totalValue: 7012,
    gain: -1788,
    gainPercent: -20.3,
    allocation: 8,
  },
  {
    id: 5,
    name: "S&P 500 ETF",
    symbol: "SPY",
    quantity: 60,
    purchasePrice: 420,
    currentPrice: 512.8,
    totalValue: 30768,
    gain: 5568,
    gainPercent: 22.1,
    allocation: 20,
  },
  {
    id: 6,
    name: "Bitcoin",
    symbol: "BTC",
    quantity: 0.15,
    purchasePrice: 42000,
    currentPrice: 71250,
    totalValue: 10687.5,
    gain: 4387.5,
    gainPercent: 69.6,
    allocation: 5,
  },
  {
    id: 7,
    name: "Gold ETF",
    symbol: "GLD",
    quantity: 80,
    purchasePrice: 175,
    currentPrice: 223.5,
    totalValue: 17880,
    gain: 3880,
    gainPercent: 27.7,
    allocation: 10,
  },
];

const generateMockTransactions = () => [
  {
    id: 1,
    date: "2026-04-05",
    asset: "AAPL",
    type: "Buy",
    quantity: 10,
    price: 178.5,
    amount: 1785,
  },
  {
    id: 2,
    date: "2026-04-01",
    asset: "TSLA",
    type: "Sell",
    quantity: 5,
    price: 175.3,
    amount: 876.5,
  },
  {
    id: 3,
    date: "2026-03-28",
    asset: "BTC",
    type: "Buy",
    quantity: 0.02,
    price: 71250,
    amount: 1425,
  },
  {
    id: 4,
    date: "2026-03-15",
    asset: "MSFT",
    type: "Buy",
    quantity: 5,
    price: 415.2,
    amount: 2076,
  },
  {
    id: 5,
    date: "2026-03-10",
    asset: "GLD",
    type: "Sell",
    quantity: 10,
    price: 223.5,
    amount: 2235,
  },
  {
    id: 6,
    date: "2026-03-01",
    asset: "SPY",
    type: "Buy",
    quantity: 8,
    price: 512.8,
    amount: 4102.4,
  },
  {
    id: 7,
    date: "2026-02-22",
    asset: "AMZN",
    type: "Buy",
    quantity: 5,
    price: 198.7,
    amount: 993.5,
  },
  {
    id: 8,
    date: "2026-02-15",
    asset: "AAPL",
    type: "Sell",
    quantity: 3,
    price: 175.2,
    amount: 525.6,
  },
];

export default usePortfolioManagement;
