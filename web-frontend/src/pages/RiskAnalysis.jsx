import CalculateIcon from "@mui/icons-material/Calculate";
import DownloadIcon from "@mui/icons-material/Download";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  Divider,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { useRiskAnalysis } from "../context/RiskAnalysisContext";
import { formatCurrency, formatPercentage } from "../utils/formatters";

const RiskAnalysis = () => {
  const [tabValue, setTabValue] = useState(0);
  const {
    varData,
    cvarData,
    loading,
    error,
    calculateVaR,
    calculateCVaR,
    calculateSharpeRatio,
    calculateMaxDrawdown,
    clearRiskData,
  } = useRiskAnalysis();

  const [varParams, setVarParams] = useState({
    confidence_level: 0.95,
    time_horizon: 1,
    method: "historical",
  });
  const [stressScenario, setStressScenario] = useState("2008_crisis");
  const [stressParams, setStressParams] = useState({
    equity_shock: -30,
    bond_shock: 1.5,
    crypto_shock: -45,
  });
  const [stressResult, setStressResult] = useState(null);

  const handleTabChange = (_event, newValue) => {
    setTabValue(newValue);
  };

  const handleVarCalculate = async () => {
    const mockReturns = Array.from(
      { length: 252 },
      () => (Math.random() - 0.5) * 0.02,
    );
    await calculateVaR({
      returns: mockReturns,
      confidence_level: varParams.confidence_level,
      time_horizon: varParams.time_horizon,
      method: varParams.method,
    });
    await calculateCVaR({
      returns: mockReturns,
      confidence_level: varParams.confidence_level,
    });
  };

  const handleStressTest = async () => {
    const totalShock =
      stressParams.equity_shock * 0.6 +
      stressParams.bond_shock * -2 * 0.2 +
      stressParams.crypto_shock * 0.1;
    setStressResult({
      portfolioLoss: totalShock,
      equityImpact: stressParams.equity_shock,
      bondImpact: stressParams.bond_shock * -2,
      cryptoImpact: stressParams.crypto_shock,
      goldImpact: 12.3,
    });
  };

  const handleExport = () => {
    const data = {
      varData,
      cvarData,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "risk-analysis-report.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const riskSummary = {
    valueAtRisk: varData?.var_amount ?? 4532.12,
    cvar: cvarData?.cvar_amount ?? 5821.45,
    volatility: varData?.volatility ?? 14.2,
    sharpeRatio: 1.87,
    maxDrawdown: -12.4,
  };

  return (
    <Box className="fade-in">
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Typography variant="h4" component="h1" gutterBottom>
          Risk Analysis
        </Typography>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={handleExport}
        >
          Export Report
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={clearRiskData}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Risk Metrics Summary */}
        <Grid item xs={12}>
          <Card>
            <CardHeader
              title="Risk Metrics Summary"
              action={
                <IconButton>
                  <MoreVertIcon />
                </IconButton>
              }
            />
            <Divider />
            <CardContent>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6} md={3} lg={2.4}>
                  <Box sx={{ textAlign: "center", p: 2 }}>
                    <Typography
                      variant="subtitle2"
                      color="text.secondary"
                      gutterBottom
                    >
                      Value at Risk (95%)
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 600 }}>
                      {formatCurrency(riskSummary.valueAtRisk)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {formatPercentage(
                        (riskSummary.valueAtRisk / 124532.89) * 100,
                      )}{" "}
                      of portfolio
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3} lg={2.4}>
                  <Box sx={{ textAlign: "center", p: 2 }}>
                    <Typography
                      variant="subtitle2"
                      color="text.secondary"
                      gutterBottom
                    >
                      CVaR (Expected Shortfall)
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 600 }}>
                      {formatCurrency(riskSummary.cvar)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Expected tail loss
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3} lg={2.4}>
                  <Box sx={{ textAlign: "center", p: 2 }}>
                    <Typography
                      variant="subtitle2"
                      color="text.secondary"
                      gutterBottom
                    >
                      Volatility (Annualized)
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 600 }}>
                      {formatPercentage(riskSummary.volatility)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Moderate volatility
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3} lg={2.4}>
                  <Box sx={{ textAlign: "center", p: 2 }}>
                    <Typography
                      variant="subtitle2"
                      color="text.secondary"
                      gutterBottom
                    >
                      Sharpe Ratio
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 600 }}>
                      {riskSummary.sharpeRatio}
                    </Typography>
                    <Typography variant="body2" color="success.main">
                      Good risk-adjusted return
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3} lg={2.4}>
                  <Box sx={{ textAlign: "center", p: 2 }}>
                    <Typography
                      variant="subtitle2"
                      color="text.secondary"
                      gutterBottom
                    >
                      Maximum Drawdown
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 600 }}>
                      {formatPercentage(riskSummary.maxDrawdown)}
                    </Typography>
                    <Typography variant="body2" color="warning.main">
                      Moderate risk
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Risk Analysis Tools */}
        <Grid item xs={12}>
          <Card>
            <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
              <Tabs
                value={tabValue}
                onChange={handleTabChange}
                aria-label="risk analysis tabs"
                variant="scrollable"
                scrollButtons="auto"
              >
                <Tab label="Value at Risk (VaR)" />
                <Tab label="CVaR / Expected Shortfall" />
                <Tab label="Stress Testing" />
                <Tab label="Correlation Analysis" />
                <Tab label="Risk Contribution" />
              </Tabs>
            </Box>
            <CardContent>
              {/* VaR Tab */}
              {tabValue === 0 && (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Value at Risk (VaR) Calculator
                  </Typography>
                  <Typography variant="body2" paragraph>
                    VaR estimates the maximum potential loss over a specific
                    time period at a given confidence level.
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={5}>
                      <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                        <InputLabel>Confidence Level</InputLabel>
                        <Select
                          value={varParams.confidence_level}
                          label="Confidence Level"
                          onChange={(e) =>
                            setVarParams((p) => ({
                              ...p,
                              confidence_level: e.target.value,
                            }))
                          }
                        >
                          <MenuItem value={0.9}>90%</MenuItem>
                          <MenuItem value={0.95}>95%</MenuItem>
                          <MenuItem value={0.99}>99%</MenuItem>
                        </Select>
                      </FormControl>
                      <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                        <InputLabel>Time Horizon</InputLabel>
                        <Select
                          value={varParams.time_horizon}
                          label="Time Horizon"
                          onChange={(e) =>
                            setVarParams((p) => ({
                              ...p,
                              time_horizon: e.target.value,
                            }))
                          }
                        >
                          <MenuItem value={1}>1 Day</MenuItem>
                          <MenuItem value={5}>1 Week (5 Days)</MenuItem>
                          <MenuItem value={20}>1 Month (20 Days)</MenuItem>
                          <MenuItem value={60}>3 Months (60 Days)</MenuItem>
                        </Select>
                      </FormControl>
                      <FormControl fullWidth size="small" sx={{ mb: 3 }}>
                        <InputLabel>Calculation Method</InputLabel>
                        <Select
                          value={varParams.method}
                          label="Calculation Method"
                          onChange={(e) =>
                            setVarParams((p) => ({
                              ...p,
                              method: e.target.value,
                            }))
                          }
                        >
                          <MenuItem value="historical">
                            Historical Simulation
                          </MenuItem>
                          <MenuItem value="parametric">
                            Parametric (Variance-Covariance)
                          </MenuItem>
                          <MenuItem value="montecarlo">
                            Monte Carlo Simulation
                          </MenuItem>
                        </Select>
                      </FormControl>
                      <Button
                        variant="contained"
                        fullWidth
                        startIcon={
                          loading ? (
                            <CircularProgress size={16} color="inherit" />
                          ) : (
                            <CalculateIcon />
                          )
                        }
                        onClick={handleVarCalculate}
                        disabled={loading}
                      >
                        {loading ? "Calculating..." : "Calculate VaR"}
                      </Button>
                    </Grid>
                    <Grid item xs={12} md={7}>
                      <Card
                        variant="outlined"
                        sx={{ backgroundColor: "background.default" }}
                      >
                        <CardContent>
                          <Typography variant="subtitle2" gutterBottom>
                            VaR Results
                          </Typography>
                          <Grid container spacing={2}>
                            <Grid item xs={6}>
                              <Typography
                                variant="body2"
                                color="text.secondary"
                              >
                                Value at Risk
                              </Typography>
                              <Typography
                                variant="h5"
                                color="error.main"
                                sx={{ fontWeight: 600 }}
                              >
                                {varData
                                  ? formatCurrency(
                                      varData.var_amount ??
                                        riskSummary.valueAtRisk,
                                    )
                                  : formatCurrency(riskSummary.valueAtRisk)}
                              </Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography
                                variant="body2"
                                color="text.secondary"
                              >
                                CVaR (Expected Shortfall)
                              </Typography>
                              <Typography
                                variant="h5"
                                color="error.main"
                                sx={{ fontWeight: 600 }}
                              >
                                {cvarData
                                  ? formatCurrency(
                                      cvarData.cvar_amount ?? riskSummary.cvar,
                                    )
                                  : formatCurrency(riskSummary.cvar)}
                              </Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography
                                variant="body2"
                                color="text.secondary"
                              >
                                Confidence Level
                              </Typography>
                              <Typography
                                variant="body1"
                                sx={{ fontWeight: 500 }}
                              >
                                {(varParams.confidence_level * 100).toFixed(0)}%
                              </Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography
                                variant="body2"
                                color="text.secondary"
                              >
                                Time Horizon
                              </Typography>
                              <Typography
                                variant="body1"
                                sx={{ fontWeight: 500 }}
                              >
                                {varParams.time_horizon} day
                                {varParams.time_horizon > 1 ? "s" : ""}
                              </Typography>
                            </Grid>
                          </Grid>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </Box>
              )}

              {/* CVaR Tab */}
              {tabValue === 1 && (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    CVaR / Expected Shortfall
                  </Typography>
                  <Typography variant="body2" paragraph>
                    Conditional Value at Risk (CVaR), also known as Expected
                    Shortfall, measures the expected loss beyond the VaR
                    threshold — giving a fuller picture of tail risk.
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={5}>
                      <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                        <InputLabel>Confidence Level</InputLabel>
                        <Select
                          value={varParams.confidence_level}
                          label="Confidence Level"
                          onChange={(e) =>
                            setVarParams((p) => ({
                              ...p,
                              confidence_level: e.target.value,
                            }))
                          }
                        >
                          <MenuItem value={0.9}>90%</MenuItem>
                          <MenuItem value={0.95}>95%</MenuItem>
                          <MenuItem value={0.99}>99%</MenuItem>
                        </Select>
                      </FormControl>
                      <Button
                        variant="contained"
                        fullWidth
                        startIcon={
                          loading ? (
                            <CircularProgress size={16} color="inherit" />
                          ) : (
                            <CalculateIcon />
                          )
                        }
                        onClick={handleVarCalculate}
                        disabled={loading}
                      >
                        {loading ? "Calculating..." : "Calculate CVaR"}
                      </Button>
                    </Grid>
                    <Grid item xs={12} md={7}>
                      <Card
                        variant="outlined"
                        sx={{ backgroundColor: "background.default" }}
                      >
                        <CardContent>
                          <Typography variant="subtitle2" gutterBottom>
                            CVaR Results
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Expected Shortfall
                          </Typography>
                          <Typography
                            variant="h4"
                            color="error.main"
                            sx={{ fontWeight: 600, my: 1 }}
                          >
                            {cvarData
                              ? formatCurrency(
                                  cvarData.cvar_amount ?? riskSummary.cvar,
                                )
                              : formatCurrency(riskSummary.cvar)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            This is the average loss expected in the worst{" "}
                            {(100 - varParams.confidence_level * 100).toFixed(
                              0,
                            )}
                            % of scenarios.
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </Box>
              )}

              {/* Stress Testing Tab */}
              {tabValue === 2 && (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Stress Testing
                  </Typography>
                  <Typography variant="body2" paragraph>
                    Simulate how your portfolio performs under extreme market
                    conditions.
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                        <InputLabel>Scenario</InputLabel>
                        <Select
                          value={stressScenario}
                          label="Scenario"
                          onChange={(e) => setStressScenario(e.target.value)}
                        >
                          <MenuItem value="2008_crisis">
                            2008 Financial Crisis
                          </MenuItem>
                          <MenuItem value="covid_crash">
                            COVID-19 Market Crash (2020)
                          </MenuItem>
                          <MenuItem value="dot_com">
                            Dot-com Bubble Burst (2000)
                          </MenuItem>
                          <MenuItem value="custom">Custom Scenario</MenuItem>
                        </Select>
                      </FormControl>
                      <Typography variant="subtitle2" gutterBottom>
                        Shock Parameters
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={8}>
                          <Typography variant="body2">
                            Equity Markets
                          </Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <TextField
                            size="small"
                            value={stressParams.equity_shock}
                            onChange={(e) =>
                              setStressParams((p) => ({
                                ...p,
                                equity_shock: parseFloat(e.target.value) || 0,
                              }))
                            }
                            InputProps={{ endAdornment: "%" }}
                            type="number"
                          />
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body2">Bond Yields</Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <TextField
                            size="small"
                            value={stressParams.bond_shock}
                            onChange={(e) =>
                              setStressParams((p) => ({
                                ...p,
                                bond_shock: parseFloat(e.target.value) || 0,
                              }))
                            }
                            InputProps={{ endAdornment: "%" }}
                            type="number"
                          />
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body2">
                            Cryptocurrency
                          </Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <TextField
                            size="small"
                            value={stressParams.crypto_shock}
                            onChange={(e) =>
                              setStressParams((p) => ({
                                ...p,
                                crypto_shock: parseFloat(e.target.value) || 0,
                              }))
                            }
                            InputProps={{ endAdornment: "%" }}
                            type="number"
                          />
                        </Grid>
                      </Grid>
                      <Button
                        variant="contained"
                        fullWidth
                        startIcon={
                          loading ? (
                            <CircularProgress size={16} color="inherit" />
                          ) : (
                            <CalculateIcon />
                          )
                        }
                        onClick={handleStressTest}
                        disabled={loading}
                        sx={{ mt: 2 }}
                      >
                        {loading ? "Running..." : "Run Stress Test"}
                      </Button>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Card
                        variant="outlined"
                        sx={{ backgroundColor: "background.default" }}
                      >
                        <CardContent>
                          <Typography variant="subtitle2" gutterBottom>
                            Stress Test Results:{" "}
                            {stressScenario === "2008_crisis"
                              ? "2008 Financial Crisis"
                              : stressScenario === "covid_crash"
                                ? "COVID-19 Crash"
                                : stressScenario === "dot_com"
                                  ? "Dot-com Bubble"
                                  : "Custom Scenario"}
                          </Typography>
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="body2" color="text.secondary">
                              Estimated Portfolio Loss
                            </Typography>
                            <Typography
                              variant="h5"
                              color="error.main"
                              sx={{ fontWeight: 600 }}
                            >
                              {stressResult
                                ? formatPercentage(
                                    stressResult.portfolioLoss,
                                    1,
                                  )
                                : "—"}
                            </Typography>
                          </Box>
                          {stressResult && (
                            <>
                              <Typography variant="subtitle2" gutterBottom>
                                Impact by Asset Class
                              </Typography>
                              {[
                                {
                                  label: "Equities",
                                  value: stressResult.equityImpact,
                                },
                                {
                                  label: "Bonds",
                                  value: stressResult.bondImpact,
                                },
                                {
                                  label: "Crypto",
                                  value: stressResult.cryptoImpact,
                                },
                                {
                                  label: "Gold",
                                  value: stressResult.goldImpact,
                                },
                              ].map(({ label, value }) => (
                                <Box key={label} sx={{ mb: 1 }}>
                                  <Typography variant="body2" display="inline">
                                    {label}:
                                  </Typography>
                                  <Typography
                                    variant="body2"
                                    color={
                                      value >= 0 ? "success.main" : "error.main"
                                    }
                                    display="inline"
                                    sx={{ ml: 1 }}
                                  >
                                    {formatPercentage(value, 1, true)}
                                  </Typography>
                                </Box>
                              ))}
                            </>
                          )}
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </Box>
              )}

              {tabValue === 3 && (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Correlation Analysis
                  </Typography>
                  <Typography variant="body2" paragraph>
                    Correlation analysis helps understand how assets move in
                    relation to each other, crucial for portfolio
                    diversification.
                  </Typography>
                  <Box
                    sx={{
                      height: 400,
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                    }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      Correlation matrix heatmap — connect backend for live data
                    </Typography>
                  </Box>
                </Box>
              )}

              {tabValue === 4 && (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Risk Contribution
                  </Typography>
                  <Typography variant="body2" paragraph>
                    Risk contribution analysis shows how much each asset
                    contributes to overall portfolio risk.
                  </Typography>
                  <Box
                    sx={{
                      height: 400,
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                    }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      Risk contribution chart — connect backend for live data
                    </Typography>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default RiskAnalysis;
