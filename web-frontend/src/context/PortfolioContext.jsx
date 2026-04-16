import { createContext, useCallback, useContext, useState } from "react";

const PortfolioContext = createContext();

// Default demo assets for new users
const DEMO_ASSETS = [
  {
    id: 1,
    symbol: "AAPL",
    name: "Apple Inc.",
    quantity: 50,
    purchasePrice: 150.0,
    currentPrice: 178.5,
    totalValue: 8925,
    gain: 1425,
    gainPercent: 19.0,
  },
  {
    id: 2,
    symbol: "MSFT",
    name: "Microsoft Corp.",
    quantity: 30,
    purchasePrice: 280.0,
    currentPrice: 415.2,
    totalValue: 12456,
    gain: 4056,
    gainPercent: 48.3,
  },
  {
    id: 3,
    symbol: "TSLA",
    name: "Tesla Inc.",
    quantity: 20,
    purchasePrice: 220.0,
    currentPrice: 175.3,
    totalValue: 3506,
    gain: -894,
    gainPercent: -20.3,
  },
  {
    id: 4,
    symbol: "BTC",
    name: "Bitcoin",
    quantity: 0.5,
    purchasePrice: 42000.0,
    currentPrice: 67800.0,
    totalValue: 33900,
    gain: 12900,
    gainPercent: 61.4,
  },
  {
    id: 5,
    symbol: "SPY",
    name: "S&P 500 ETF",
    quantity: 40,
    purchasePrice: 440.0,
    currentPrice: 522.1,
    totalValue: 20884,
    gain: 3284,
    gainPercent: 18.6,
  },
];

export const PortfolioProvider = ({ children }) => {
  const [portfolio, setPortfolio] = useState({ assets: DEMO_ASSETS });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Simulate async fetch — returns demo data (no backend needed)
  const fetchPortfolio = useCallback(async (_address) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 300));
      const saved = localStorage.getItem("portfolio");
      if (saved) {
        const parsed = JSON.parse(saved);
        setPortfolio(parsed);
        return parsed;
      }
      setPortfolio({ assets: DEMO_ASSETS });
      return { assets: DEMO_ASSETS };
    } catch {
      setError("Failed to load portfolio");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPortfolioByUserId = useCallback(
    async (_userId) => {
      return fetchPortfolio(null);
    },
    [fetchPortfolio],
  );

  const savePortfolio = useCallback(
    async (portfolioData) => {
      setLoading(true);
      setError(null);
      try {
        await new Promise((r) => setTimeout(r, 200));
        const updated = { ...portfolio, ...portfolioData };
        setPortfolio(updated);
        localStorage.setItem("portfolio", JSON.stringify(updated));
        return true;
      } catch {
        setError("Failed to save portfolio");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [portfolio],
  );

  const createPortfolio = useCallback(async (portfolioData) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 200));
      const newPortfolio = {
        id: Date.now(),
        ...portfolioData,
        assets: portfolioData.assets || [],
      };
      setPortfolio(newPortfolio);
      localStorage.setItem("portfolio", JSON.stringify(newPortfolio));
      return newPortfolio;
    } catch {
      setError("Failed to create portfolio");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const updatePortfolio = useCallback(
    async (_id, portfolioData) => {
      return savePortfolio(portfolioData);
    },
    [savePortfolio],
  );

  const deletePortfolio = useCallback(async (_id) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 200));
      setPortfolio(null);
      localStorage.removeItem("portfolio");
      return true;
    } catch {
      setError("Failed to delete portfolio");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  // Mock portfolio optimization
  const optimizePortfolio = useCallback(async (_params) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 1200));
      return null; // Optimization page falls back to mock results when null is returned
    } catch {
      setError("Failed to optimize portfolio");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const value = {
    portfolio,
    loading,
    error,
    fetchPortfolio,
    fetchPortfolioByUserId,
    savePortfolio,
    createPortfolio,
    updatePortfolio,
    deletePortfolio,
    optimizePortfolio,
    clearError,
  };

  return (
    <PortfolioContext.Provider value={value}>
      {children}
    </PortfolioContext.Provider>
  );
};

export const usePortfolio = () => {
  const context = useContext(PortfolioContext);
  if (context === undefined) {
    throw new Error("usePortfolio must be used within a PortfolioProvider");
  }
  return context;
};

export default PortfolioContext;
