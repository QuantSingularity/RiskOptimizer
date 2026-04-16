import { createContext, useCallback, useContext, useState } from "react";

const RiskAnalysisContext = createContext();

// ─── Mock calculation helpers ─────────────────────────────────────────────────
function calcVaR(returns, confidenceLevel, timeHorizon) {
  const sorted = [...returns].sort((a, b) => a - b);
  const idx = Math.floor((1 - confidenceLevel) * sorted.length);
  const dailyVaR = -sorted[idx];
  const scaledVaR = dailyVaR * Math.sqrt(timeHorizon);
  const portfolioValue = 124532.89;
  return {
    var_percent: scaledVaR * 100,
    var_amount: scaledVaR * portfolioValue,
    confidence_level: confidenceLevel,
    time_horizon: timeHorizon,
    volatility:
      Math.sqrt(returns.reduce((s, r) => s + r * r, 0) / returns.length) *
      Math.sqrt(252) *
      100,
  };
}

function calcCVaR(returns, confidenceLevel) {
  const sorted = [...returns].sort((a, b) => a - b);
  const cutoff = Math.floor((1 - confidenceLevel) * sorted.length);
  const tailReturns = sorted.slice(0, cutoff);
  const avgTailLoss =
    tailReturns.length > 0
      ? -tailReturns.reduce((s, r) => s + r, 0) / tailReturns.length
      : 0;
  const portfolioValue = 124532.89;
  return {
    cvar_percent: avgTailLoss * 100,
    cvar_amount: avgTailLoss * portfolioValue,
    confidence_level: confidenceLevel,
  };
}

// ─── Provider ─────────────────────────────────────────────────────────────────
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
      await new Promise((r) => setTimeout(r, 500));
      const result = calcVaR(
        params.returns || [],
        params.confidence_level ?? 0.95,
        params.time_horizon ?? 1,
      );
      setVarData(result);
      return result;
    } catch (err) {
      setError(err.message || "Failed to calculate VaR");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const calculateCVaR = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 400));
      const result = calcCVaR(
        params.returns || [],
        params.confidence_level ?? 0.95,
      );
      setCvarData(result);
      return result;
    } catch (err) {
      setError(err.message || "Failed to calculate CVaR");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const calculateSharpeRatio = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 300));
      const returns = params.returns || [];
      const mean = returns.reduce((s, r) => s + r, 0) / (returns.length || 1);
      const std = Math.sqrt(
        returns.reduce((s, r) => s + (r - mean) ** 2, 0) /
          (returns.length || 1),
      );
      const sharpe =
        std > 0
          ? (mean * 252 - (params.risk_free_rate ?? 0.04)) /
            (std * Math.sqrt(252))
          : 0;
      const result = { sharpe_ratio: sharpe };
      setSharpeData(result);
      return result;
    } catch (err) {
      setError(err.message || "Failed to calculate Sharpe Ratio");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const calculateMaxDrawdown = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 300));
      const prices = params.prices || [];
      let peak = -Infinity;
      let maxDD = 0;
      for (const p of prices) {
        if (p > peak) peak = p;
        const dd = (peak - p) / peak;
        if (dd > maxDD) maxDD = dd;
      }
      const result = { max_drawdown: -maxDD * 100 };
      setMaxDrawdownData(result);
      return result;
    } catch (err) {
      setError(err.message || "Failed to calculate Max Drawdown");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRiskMetrics = useCallback(async (_params) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 500));
      const result = {
        valueAtRisk: 4532.12,
        cvar: 5821.45,
        volatility: 14.2,
        sharpeRatio: 1.87,
        maxDrawdown: -12.4,
        beta: 0.85,
      };
      setRiskMetrics(result);
      return result;
    } catch (err) {
      setError(err.message || "Failed to fetch risk metrics");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const getEfficientFrontier = useCallback(async (_params) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 800));
      const points = Array.from({ length: 20 }, (_, i) => ({
        risk: 5 + i * 1.5,
        return: 3 + i * 0.9 - (i > 10 ? (i - 10) * 0.3 : 0),
      }));
      const result = { points };
      setEfficientFrontierData(result);
      return result;
    } catch (err) {
      setError(err.message || "Failed to calculate efficient frontier");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const runStressTest = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 600));
      const result = { stress_loss: params.equity_shock * 0.6 };
      setStressTestResults(result);
      return result;
    } catch (err) {
      setError(err.message || "Failed to run stress test");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const analyzeCorrelation = useCallback(async (_params) => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 500));
      const result = { matrix: [] };
      setCorrelationData(result);
      return result;
    } catch (err) {
      setError(err.message || "Failed to analyze correlation");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

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
    clearError,
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
