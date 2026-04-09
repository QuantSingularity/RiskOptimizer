import { createContext, useCallback, useContext, useState } from "react";
import apiService from "../services/apiService";

const RiskAnalysisContext = createContext();

export const RiskAnalysisProvider = ({ children }) => {
  const [riskMetrics, setRiskMetrics] = useState(null);
  const [varData, setVarData] = useState(null);
  const [cvarData, setCvarData] = useState(null);
  const [sharpeData, setSharpeData] = useState(null);
  const [maxDrawdownData, setMaxDrawdownData] = useState(null);
  const [stressTestResults, setStressTestResults] = useState(null);
  const [correlationData, setCorrelationData] = useState(null);
  const [efficientFrontierData, setEfficientFrontierData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const calculateVaR = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.risk.calculateVaR(params);
      if (response?.status === "success") {
        setVarData(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to calculate VaR");
      return null;
    } catch (err) {
      setError(err.message || "An error occurred while calculating VaR");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const calculateCVaR = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.risk.calculateCVaR(params);
      if (response?.status === "success") {
        setCvarData(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to calculate CVaR");
      return null;
    } catch (err) {
      setError(err.message || "An error occurred while calculating CVaR");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const calculateSharpeRatio = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.risk.calculateSharpeRatio(params);
      if (response?.status === "success") {
        setSharpeData(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to calculate Sharpe Ratio");
      return null;
    } catch (err) {
      setError(
        err.message || "An error occurred while calculating Sharpe Ratio",
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const calculateMaxDrawdown = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.risk.calculateMaxDrawdown(params);
      if (response?.status === "success") {
        setMaxDrawdownData(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to calculate Max Drawdown");
      return null;
    } catch (err) {
      setError(
        err.message || "An error occurred while calculating Max Drawdown",
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRiskMetrics = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.risk.getMetrics(params);
      if (response?.status === "success") {
        setRiskMetrics(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to fetch risk metrics");
      return null;
    } catch (err) {
      setError(err.message || "An error occurred while fetching risk metrics");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const getEfficientFrontier = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.risk.getEfficientFrontier(params);
      if (response?.status === "success") {
        setEfficientFrontierData(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to calculate efficient frontier");
      return null;
    } catch (err) {
      setError(
        err.message || "An error occurred while calculating efficient frontier",
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const runStressTest = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.risk.calculateVaR(params);
      if (response?.status === "success") {
        setStressTestResults(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to run stress test");
      return null;
    } catch (err) {
      setError(err.message || "An error occurred while running stress test");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const analyzeCorrelation = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.risk.calculateVaR(params);
      if (response?.status === "success") {
        setCorrelationData(response.data);
        return response.data;
      }
      setError(response?.message || "Failed to analyze correlation");
      return null;
    } catch (err) {
      setError(err.message || "An error occurred while analyzing correlation");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const clearRiskData = useCallback(() => {
    setRiskMetrics(null);
    setVarData(null);
    setCvarData(null);
    setSharpeData(null);
    setMaxDrawdownData(null);
    setStressTestResults(null);
    setCorrelationData(null);
    setEfficientFrontierData(null);
    setError(null);
  }, []);

  const value = {
    riskMetrics,
    varData,
    cvarData,
    sharpeData,
    maxDrawdownData,
    stressTestResults,
    correlationData,
    efficientFrontierData,
    loading,
    error,
    calculateVaR,
    calculateCVaR,
    calculateSharpeRatio,
    calculateMaxDrawdown,
    fetchRiskMetrics,
    getEfficientFrontier,
    runStressTest,
    analyzeCorrelation,
    clearRiskData,
  };

  return (
    <RiskAnalysisContext.Provider value={value}>
      {children}
    </RiskAnalysisContext.Provider>
  );
};

export const useRiskAnalysis = () => {
  const context = useContext(RiskAnalysisContext);
  if (context === undefined) {
    throw new Error(
      "useRiskAnalysis must be used within a RiskAnalysisProvider",
    );
  }
  return context;
};

export default RiskAnalysisContext;
