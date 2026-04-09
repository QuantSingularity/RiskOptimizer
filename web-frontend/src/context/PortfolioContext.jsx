import { createContext, useCallback, useContext, useState } from "react";
import apiService from "../services/apiService";

const PortfolioContext = createContext();

export const PortfolioProvider = ({ children }) => {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPortfolio = useCallback(async (address) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.portfolio.getByAddress(address);
      if (response?.status === "success") {
        setPortfolio(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to fetch portfolio");
      return null;
    } catch (err) {
      setError(err.message || "An error occurred while fetching portfolio");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPortfolioByUserId = useCallback(async (userId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.portfolio.getByUserId(userId);
      if (response?.status === "success") {
        setPortfolio(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to fetch portfolio");
      return null;
    } catch (err) {
      setError(err.message || "An error occurred while fetching portfolio");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const savePortfolio = useCallback(async (portfolioData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.portfolio.save(portfolioData);
      if (response?.status === "success") {
        setPortfolio(response.data || portfolioData);
        return true;
      }
      setError(response?.message || "Failed to save portfolio");
      return false;
    } catch (err) {
      setError(err.message || "An error occurred while saving portfolio");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const createPortfolio = useCallback(async (portfolioData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.portfolio.create(portfolioData);
      if (response?.status === "success") {
        setPortfolio(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to create portfolio");
      return null;
    } catch (err) {
      setError(err.message || "An error occurred while creating portfolio");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const updatePortfolio = useCallback(async (id, portfolioData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.portfolio.update(id, portfolioData);
      if (response?.status === "success") {
        setPortfolio(response.data || portfolioData);
        return true;
      }
      setError(response?.message || "Failed to update portfolio");
      return false;
    } catch (err) {
      setError(err.message || "An error occurred while updating portfolio");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const deletePortfolio = useCallback(async (id) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.portfolio.delete(id);
      if (response?.status === "success") {
        setPortfolio(null);
        return true;
      }
      setError(response?.message || "Failed to delete portfolio");
      return false;
    } catch (err) {
      setError(err.message || "An error occurred while deleting portfolio");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const optimizePortfolio = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.optimization.optimize(params);
      if (response?.status === "success") {
        return response.data;
      }
      setError(response?.message || "Failed to optimize portfolio");
      return null;
    } catch (err) {
      setError(err.message || "An error occurred while optimizing portfolio");
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
