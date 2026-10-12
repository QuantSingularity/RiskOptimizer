import axios from "axios";
import { Alert } from "react-native";

// --- Backend API Configuration ---
const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:5000/api/v1";
const API_TIMEOUT = process.env.API_TIMEOUT || 30000;

const backendApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// Token refresh interceptor variables
let tokenRefreshInterceptor = null;

// Set environment-specific base URL
const setEnvironment = (env) => {
  const urls = {
    development: "http://localhost:5000/api/v1",
    staging: "https://staging-api.riskoptimizer.com/api/v1",
    production: "https://api.riskoptimizer.com/api/v1",
  };
  backendApi.defaults.baseURL = urls[env] || urls.development;
};

// Set auth header
const setAuthHeader = (token) => {
  if (token) {
    backendApi.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete backendApi.defaults.headers.common.Authorization;
  }
};

// Setup token refresh interceptor
const setupTokenRefreshInterceptor = (
  _getAccessToken,
  refreshTokenCallback,
) => {
  // Remove existing interceptor if any
  if (tokenRefreshInterceptor !== null) {
    backendApi.interceptors.response.eject(tokenRefreshInterceptor);
  }

  tokenRefreshInterceptor = backendApi.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;

      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;

        try {
          const newAccessToken = await refreshTokenCallback();
          if (newAccessToken) {
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            return backendApi(originalRequest);
          }
        } catch (refreshError) {
          return Promise.reject(refreshError);
        }
      }

      return Promise.reject(error);
    },
  );
};

// Remove token refresh interceptor
const removeTokenRefreshInterceptor = () => {
  if (tokenRefreshInterceptor !== null) {
    backendApi.interceptors.response.eject(tokenRefreshInterceptor);
    tokenRefreshInterceptor = null;
  }
};

// --- Authentication API ---
const login = (email, password) => {
  return backendApi.post("/auth/login", { email, password });
};

const register = (userData) => {
  return backendApi.post("/auth/register", userData);
};

const refreshToken = (refreshToken) => {
  return backendApi.post("/auth/refresh", { refresh_token: refreshToken });
};

const logout = () => {
  return backendApi.post("/auth/logout");
};

// --- User Profile API ---
const getUserProfile = () => {
  return backendApi.get("/users/profile");
};

const updateUserProfile = (profileData) => {
  return backendApi.put("/users/profile", profileData);
};

// --- Portfolios API ---
const getPortfolios = () => {
  return backendApi.get("/portfolios");
};

const getPortfolioDetails = (portfolioId) => {
  return backendApi.get(`/portfolios/${portfolioId}`);
};

const createPortfolio = (portfolioData) => {
  return backendApi.post("/portfolios", portfolioData);
};

const updatePortfolio = (portfolioId, portfolioData) => {
  return backendApi.put(`/portfolios/${portfolioId}`, portfolioData);
};

const deletePortfolio = (portfolioId) => {
  return backendApi.delete(`/portfolios/${portfolioId}`);
};

const addAssetToPortfolio = (portfolioId, assetData) => {
  return backendApi.post(`/portfolios/${portfolioId}/assets`, assetData);
};

const updateAsset = (portfolioId, assetId, assetData) => {
  return backendApi.put(
    `/portfolios/${portfolioId}/assets/${assetId}`,
    assetData,
  );
};

const deleteAsset = (portfolioId, assetId) => {
  return backendApi.delete(`/portfolios/${portfolioId}/assets/${assetId}`);
};

// --- Optimization API ---
const optimizePortfolio = (params) => {
  return backendApi.post("/optimization/optimize", params);
};

const getEfficientFrontier = (params) => {
  return backendApi.post("/optimization/efficient-frontier", params);
};

const getOptimizationSymbols = () => {
  return backendApi.get("/optimization/symbols");
};

const simulateRisk = (params) => {
  return backendApi.post("/optimization/simulate", params);
};

const getPriceForecast = (ticker, periods = 30, model = "auto") => {
  return backendApi.get(
    `/optimization/forecast/${encodeURIComponent(ticker)}`,
    { params: { periods, model } },
  );
};

const analyzeSentiment = (texts) => {
  return backendApi.post("/optimization/sentiment", { texts });
};

const getOptimizationModelInfo = () => {
  return backendApi.get("/optimization/model");
};

// --- Quant risk API ---
const QUANT_OPERATIONS = {
  evt: "/quant/risk/evt",
  ml: "/quant/risk/ml",
  copula: "/quant/risk/copula",
  hybrid: "/quant/risk/hybrid",
  monteCarlo: "/quant/risk/monte-carlo",
  batch: "/quant/risk/batch",
  stressTest: "/quant/risk/stress-test",
  backtest: "/quant/risk/backtest",
  sensitivity: "/quant/risk/sensitivity",
  decomposition: "/quant/risk/decomposition",
  analysis: "/quant/risk/analysis",
  portfolioSearch: "/quant/portfolio/search",
  meanVariance: "/quant/portfolio/mean-variance",
  report: "/quant/reports/risk",
};

const runQuantAnalysis = (operation, params) => {
  const path = QUANT_OPERATIONS[operation];
  if (!path) {
    return Promise.reject(new Error(`Unknown quant operation: ${operation}`));
  }
  return backendApi.post(path, params);
};

const getQuantInfo = () => {
  return backendApi.get("/quant/info");
};

const listQuantReports = (limit = 20) => {
  return backendApi.get("/quant/reports", { params: { limit } });
};

const getQuantReport = (reportId) => {
  return backendApi.get(`/quant/reports/${encodeURIComponent(reportId)}`);
};

// --- Risk Analysis API ---
const getRiskMetrics = (portfolioId) => {
  return backendApi.get(`/risk/metrics/${portfolioId}`);
};

const calculateVaR = (portfolioId, params) => {
  return backendApi.post(`/risk/var/${portfolioId}`, params);
};

const performStressTest = (portfolioId, scenarios) => {
  return backendApi.post(`/risk/stress-test/${portfolioId}`, scenarios);
};

// --- Blockchain API ---
const getTransactionHistory = (portfolioId) => {
  return backendApi.get(`/blockchain/transactions/${portfolioId}`);
};

const verifyPortfolioIntegrity = (portfolioId) => {
  return backendApi.get(`/blockchain/verify/${portfolioId}`);
};

// --- Market Data API (with simulation fallback) ---
const getAssetPriceHistory = async (symbol, range = "1y", interval = "1d") => {
  try {
    // Try to fetch from backend
    const response = await backendApi.get(`/market/history/${symbol}`, {
      params: { range, interval },
    });
    return response;
  } catch (_error) {
    console.warn(
      `Backend market data unavailable for ${symbol}, using simulation`,
    );
    // Fallback to simulation
    return simulateMarketData(symbol, range, interval);
  }
};

const searchAssets = async (query) => {
  try {
    const response = await backendApi.get("/market/search", {
      params: { q: query },
    });
    return response;
  } catch (_error) {
    console.warn("Backend asset search unavailable, using simulation");
    return simulateAssetSearch(query);
  }
};

const getMarketOverview = async () => {
  try {
    return await backendApi.get("/market/overview");
  } catch (_error) {
    console.warn("Backend market overview unavailable, using simulation");
    return simulateMarketOverview();
  }
};

// --- Simulation Functions (Fallback for development) ---
const simulateMarketData = async (symbol, range, _interval) => {
  await new Promise((resolve) => setTimeout(resolve, 500));

  const generateMockData = (numPoints) => {
    const timestamps = [];
    const closes = [];
    const opens = [];
    const highs = [];
    const lows = [];
    const volumes = [];
    let lastClose = Math.random() * 200 + 50;
    const now = Date.now();
    const timeStep = range === "1d" ? 5 * 60 * 1000 : 24 * 60 * 60 * 1000;

    for (let i = 0; i < numPoints; i++) {
      timestamps.push(
        Math.floor((now - (numPoints - 1 - i) * timeStep) / 1000),
      );
      const change = (Math.random() - 0.48) * (lastClose * 0.05);
      const open = lastClose;
      const close = Math.max(1, lastClose + change);
      const high = Math.max(open, close) * (1 + Math.random() * 0.02);
      const low = Math.min(open, close) * (1 - Math.random() * 0.02);
      const volume = Math.floor(Math.random() * 1000000 + 50000);

      opens.push(open);
      closes.push(close);
      highs.push(high);
      lows.push(low);
      volumes.push(volume);
      lastClose = close;
    }
    return { timestamps, closes, opens, highs, lows, volumes };
  };

  const numPoints =
    { "1d": 78, "5d": 5, "1mo": 22, "6mo": 126, "1y": 252 }[range] || 50;
  const mock = generateMockData(numPoints);

  return {
    data: {
      symbol,
      timestamps: mock.timestamps,
      prices: mock.closes,
      opens: mock.opens,
      highs: mock.highs,
      lows: mock.lows,
      volumes: mock.volumes,
      regularMarketPrice: mock.closes[mock.closes.length - 1],
      previousClose: mock.opens[0],
    },
  };
};

const simulateAssetSearch = async (query) => {
  await new Promise((resolve) => setTimeout(resolve, 300));
  const mockAssets = [
    { symbol: "AAPL", name: "Apple Inc.", type: "stock" },
    { symbol: "MSFT", name: "Microsoft Corporation", type: "stock" },
    { symbol: "GOOGL", name: "Alphabet Inc. (Class A)", type: "stock" },
    { symbol: "AMZN", name: "Amazon.com, Inc.", type: "stock" },
    { symbol: "TSLA", name: "Tesla, Inc.", type: "stock" },
    { symbol: "NVDA", name: "NVIDIA Corporation", type: "stock" },
    { symbol: "BTC-USD", name: "Bitcoin USD", type: "crypto" },
    { symbol: "ETH-USD", name: "Ethereum USD", type: "crypto" },
  ];

  const results = mockAssets.filter(
    (asset) =>
      asset.symbol.toLowerCase().includes(query.toLowerCase()) ||
      asset.name.toLowerCase().includes(query.toLowerCase()),
  );

  return { data: { assets: results.slice(0, 10) } };
};

const simulateMarketOverview = async () => {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return {
    data: {
      indices: [
        { name: "S&P 500", value: 4783.45, change: 0.85 },
        { name: "NASDAQ", value: 15043.2, change: 1.23 },
        { name: "DOW", value: 37305.16, change: 0.42 },
      ],
      topGainers: [
        { symbol: "NVDA", name: "NVIDIA", change: 5.2 },
        { symbol: "TSLA", name: "Tesla", change: 4.8 },
      ],
      topLosers: [
        { symbol: "META", name: "Meta", change: -2.1 },
        { symbol: "NFLX", name: "Netflix", change: -1.8 },
      ],
    },
  };
};

// --- Error handling interceptor ---
backendApi.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.message || error.message || "An error occurred";
    console.error("API Error:", message, error.response?.data);

    if (error.response?.status === 500) {
      Alert.alert(
        "Server Error",
        "An unexpected error occurred. Please try again later.",
      );
    } else if (!error.response) {
      Alert.alert(
        "Network Error",
        "Unable to connect to the server. Please check your connection.",
      );
    }

    return Promise.reject(error);
  },
);

export default {
  // Configuration
  setEnvironment,
  setAuthHeader,
  setupTokenRefreshInterceptor,
  removeTokenRefreshInterceptor,

  // Auth
  login,
  register,
  refreshToken,
  logout,

  // User
  getUserProfile,
  updateUserProfile,

  // Portfolios
  getPortfolios,
  getPortfolioDetails,
  createPortfolio,
  updatePortfolio,
  deletePortfolio,
  addAssetToPortfolio,
  updateAsset,
  deleteAsset,

  // Optimization & Risk
  optimizePortfolio,
  getEfficientFrontier,
  getOptimizationSymbols,
  simulateRisk,
  getPriceForecast,
  analyzeSentiment,
  getOptimizationModelInfo,
  runQuantAnalysis,
  getQuantInfo,
  listQuantReports,
  getQuantReport,
  getRiskMetrics,
  calculateVaR,
  performStressTest,

  // Blockchain
  getTransactionHistory,
  verifyPortfolioIntegrity,

  // Market Data
  getAssetPriceHistory,
  searchAssets,
  getMarketOverview,
};
