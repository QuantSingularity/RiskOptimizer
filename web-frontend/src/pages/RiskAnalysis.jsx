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
  useTheme,
} from "@mui/material";
import React, { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useRiskAnalysis } from "../context/RiskAnalysisContext";
import { formatCurrency, formatPercentage } from "../utils/formatters";

// ─── Correlation matrix data ──────────────────────────────────────────────────
const ASSETS_CORR = ["AAPL", "MSFT", "AMZN", "TSLA", "BTC", "GLD", "SPY"];
const correlationMatrix = [
  [1.0, 0.82, 0.75, 0.61, 0.38, -0.15, 0.9],
  [0.82, 1.0, 0.79, 0.55, 0.32, -0.12, 0.88],
  [0.75, 0.79, 1.0, 0.58, 0.41, -0.1, 0.83],
  [0.61, 0.55, 0.58, 1.0, 0.52, 0.05, 0.67],
  [0.38, 0.32, 0.41, 0.52, 1.0, 0.12, 0.44],
  [-0.15, -0.12, -0.1, 0.05, 0.12, 1.0, -0.18],
  [0.9, 0.88, 0.83, 0.67, 0.44, -0.18, 1.0],
];

// ─── Risk contribution data ───────────────────────────────────────────────────
const riskContributionData = [
  { name: "AAPL", riskContrib: 22.4, weight: 15, fill: "#61dafb" },
  { name: "MSFT", riskContrib: 18.1, weight: 12, fill: "#4caf50" },
  { name: "AMZN", riskContrib: 15.6, weight: 10, fill: "#ff9800" },
  { name: "TSLA", riskContrib: 14.2, weight: 8, fill: "#e91e63" },
  { name: "GOOGL", riskContrib: 12.8, weight: 10, fill: "#9c27b0" },
  { name: "BTC", riskContrib: 8.7, weight: 5, fill: "#f44336" },
  { name: "SPY", riskContrib: 5.3, weight: 20, fill: "#00bcd4" },
  { name: "GLD", riskContrib: 2.9, weight: 10, fill: "#ffc107" },
];

// ─── Stress scenario presets ──────────────────────────────────────────────────
const SCENARIO_PRESETS = {
  "2008_crisis": { equity_shock: -38, bond_shock: 3.2, crypto_shock: -60 },
  covid_crash: { equity_shock: -34, bond_shock: -1.0, crypto_shock: -50 },
  dot_com: { equity_shock: -49, bond_shock: 6.8, crypto_shock: 0 },
  custom: null,
};

const SCENARIO_LABELS = {
  "2008_crisis": "2008 Financial Crisis",
  covid_crash: "COVID-19 Crash (2020)",
  dot_com: "Dot-com Bubble (2000)",
  custom: "Custom Scenario",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
function corrColor(val) {
  if (val >= 0.8) return "#f44336";
  if (val >= 0.6) return "#ff7043";
  if (val >= 0.4) return "#ffa726";
  if (val >= 0.2) return "#ffee58";
  if (val >= 0) return "#c8e6c9";
  if (val >= -0.2) return "#b2dfdb";
  return "#26c6da";
}

// ─── Correlation Heatmap ──────────────────────────────────────────────────────
const CorrelationHeatmap = () => {
  const cellSize = 46;

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Correlation Matrix
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Values near 1 indicate strong positive correlation; values near −1
        indicate inverse movement. Diversification benefits are highest when
        asset correlations are low or negative.
      </Typography>

      <Box sx={{ overflowX: "auto" }}>
        <Box
          sx={{
            display: "inline-grid",
            gridTemplateColumns: `72px repeat(${ASSETS_CORR.length}, ${cellSize}px)`,
            gap: "2px",
            mt: 1,
          }}
        >
          {/* Header row */}
          <Box />
          {ASSETS_CORR.map((a) => (
            <Box
              key={`hdr-${a}`}
              sx={{
                width: cellSize,
                textAlign: "center",
                fontSize: "0.65rem",
                fontWeight: 700,
                color: "text.secondary",
                pb: 0.5,
              }}
            >
              {a}
            </Box>
          ))}

          {/* Data rows — use React.Fragment with key instead of <> */}
          {ASSETS_CORR.map((rowAsset, ri) => (
            <React.Fragment key={`row-${rowAsset}`}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  fontSize: "0.65rem",
                  fontWeight: 700,
                  color: "text.secondary",
                  pr: 1,
                }}
              >
                {rowAsset}
              </Box>
              {ASSETS_CORR.map((_, ci) => {
                const val = correlationMatrix[ri][ci];
                return (
                  <Box
                    key={`cell-${ri}-${ci}`}
                    sx={{
                      width: cellSize,
                      height: cellSize,
                      backgroundColor: corrColor(val),
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: "4px",
                      fontSize: "0.65rem",
                      fontWeight: 600,
                      color: "#1a1a1a",
                      cursor: "default",
                      transition: "transform 0.15s",
                      "&:hover": {
                        transform: "scale(1.15)",
                        zIndex: 10,
                        position: "relative",
                      },
                    }}
                  >
                    {val.toFixed(2)}
                  </Box>
                );
              })}
            </React.Fragment>
          ))}
        </Box>
      </Box>

      {/* Legend */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          mt: 3,
          flexWrap: "wrap",
        }}
      >
        <Typography variant="caption" color="text.secondary">
          Correlation:
        </Typography>
        {[
          { label: "−1.0", color: "#26c6da" },
          { label: "−0.5", color: "#b2dfdb" },
          { label: "0", color: "#c8e6c9" },
          { label: "+0.5", color: "#ffa726" },
          { label: "+1.0", color: "#f44336" },
        ].map(({ label, color }) => (
          <Box
            key={label}
            sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
          >
            <Box
              sx={{
                width: 14,
                height: 14,
                borderRadius: 1,
                backgroundColor: color,
              }}
            />
            <Typography variant="caption" color="text.secondary">
              {label}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

// ─── Risk Contribution Chart ──────────────────────────────────────────────────
const RiskContributionChart = () => (
  <Box>
    <Typography variant="h6" gutterBottom>
      Risk Contribution by Asset
    </Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
      Shows how much each holding contributes to overall portfolio volatility.
      High-contribution assets may be candidates for reduction to improve
      diversification.
    </Typography>

    <Grid container spacing={3}>
      {/* Bar chart */}
      <Grid item xs={12} md={7}>
        <Box sx={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={riskContributionData}
              margin={{ top: 10, right: 20, left: 0, bottom: 5 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.07)"
              />
              <XAxis
                dataKey="name"
                tick={{ fill: "#b2bac2", fontSize: 11 }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#b2bac2", fontSize: 11 }}
                tickLine={false}
                unit="%"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#132f4c",
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 8,
                }}
                formatter={(v) => [`${v.toFixed(1)}%`, "Risk Contribution"]}
              />
              <Bar dataKey="riskContrib" radius={[4, 4, 0, 0]}>
                {riskContributionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Box>
      </Grid>

      {/* Weight vs Risk breakdown */}
      <Grid item xs={12} md={5}>
        <Typography variant="subtitle2" sx={{ mb: 2 }}>
          Weight vs Risk Contribution
        </Typography>
        {riskContributionData.map((d) => (
          <Box key={d.name} sx={{ mb: 1.5 }}>
            <Box
              sx={{ display: "flex", justifyContent: "space-between", mb: 0.3 }}
            >
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {d.name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {d.weight}% wt → {d.riskContrib.toFixed(1)}% risk
              </Typography>
            </Box>
            <Box sx={{ display: "flex", gap: 0.5 }}>
              <Box
                sx={{
                  height: 6,
                  width: `${d.weight * 4}px`,
                  backgroundColor: "rgba(97,218,251,0.35)",
                  borderRadius: 3,
                }}
              />
              <Box
                sx={{
                  height: 6,
                  width: `${d.riskContrib * 4}px`,
                  backgroundColor: d.fill,
                  borderRadius: 3,
                }}
              />
            </Box>
          </Box>
        ))}
        <Box sx={{ display: "flex", gap: 2, mt: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Box
              sx={{
                width: 12,
                height: 6,
                borderRadius: 3,
                backgroundColor: "rgba(97,218,251,0.35)",
              }}
            />
            <Typography variant="caption" color="text.secondary">
              Weight
            </Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Box
              sx={{
                width: 12,
                height: 6,
                borderRadius: 3,
                backgroundColor: "#61dafb",
              }}
            />
            <Typography variant="caption" color="text.secondary">
              Risk Contrib
            </Typography>
          </Box>
        </Box>
      </Grid>
    </Grid>
  </Box>
);

// ─── Main component ───────────────────────────────────────────────────────────
const RiskAnalysis = () => {
  const [tabValue, setTabValue] = useState(0);
  const {
    varData,
    cvarData,
    loading,
    error,
    calculateVaR,
    calculateCVaR,
    clearError,
  } = useRiskAnalysis();

  const [varParams, setVarParams] = useState({
    confidence_level: 0.95,
    time_horizon: 1,
    method: "historical",
  });
  const [stressScenario, setStressScenario] = useState("2008_crisis");
  const [stressParams, setStressParams] = useState(
    SCENARIO_PRESETS["2008_crisis"],
  );
  const [stressResult, setStressResult] = useState(null);

  const handleTabChange = (_, newValue) => setTabValue(newValue);

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

  const handleScenarioChange = (scenario) => {
    setStressScenario(scenario);
    const preset = SCENARIO_PRESETS[scenario];
    if (preset) setStressParams({ ...preset });
    setStressResult(null);
  };

  const handleStressTest = () => {
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
    const data = { varData, cvarData, exportedAt: new Date().toISOString() };
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

  const SHOCK_FIELDS = [
    { label: "Equity Markets", key: "equity_shock" },
    { label: "Bond Yields", key: "bond_shock" },
    { label: "Cryptocurrency", key: "crypto_shock" },
  ];

  return (
    <Box className="fade-in">
      {/* Page header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Typography variant="h4" component="h1">
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
        <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* ── Summary metrics row ──────────────────────────────────── */}
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
              <Grid container spacing={2}>
                {[
                  {
                    label: "Value at Risk (95%)",
                    value: formatCurrency(riskSummary.valueAtRisk),
                    sub: `${formatPercentage((riskSummary.valueAtRisk / 124532.89) * 100)} of portfolio`,
                    subColor: "text.secondary",
                  },
                  {
                    label: "CVaR (Expected Shortfall)",
                    value: formatCurrency(riskSummary.cvar),
                    sub: "Expected tail loss",
                    subColor: "text.secondary",
                  },
                  {
                    label: "Volatility (Annualized)",
                    value: formatPercentage(riskSummary.volatility),
                    sub: "Moderate volatility",
                    subColor: "text.secondary",
                  },
                  {
                    label: "Sharpe Ratio",
                    value: String(riskSummary.sharpeRatio),
                    sub: "Good risk-adjusted return",
                    subColor: "success.main",
                  },
                  {
                    label: "Maximum Drawdown",
                    value: formatPercentage(riskSummary.maxDrawdown),
                    sub: "Moderate risk",
                    subColor: "warning.main",
                  },
                ].map(({ label, value, sub, subColor }) => (
                  <Grid item xs={12} sm={6} md={4} lg={2.4} key={label}>
                    <Box sx={{ textAlign: "center", p: 1.5 }}>
                      <Typography
                        variant="subtitle2"
                        color="text.secondary"
                        gutterBottom
                      >
                        {label}
                      </Typography>
                      <Typography variant="h5" sx={{ fontWeight: 700 }}>
                        {value}
                      </Typography>
                      <Typography variant="body2" color={subColor}>
                        {sub}
                      </Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* ── Tabbed tools ─────────────────────────────────────────── */}
        <Grid item xs={12}>
          <Card>
            <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
              <Tabs
                value={tabValue}
                onChange={handleTabChange}
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
              {/* ── VaR ───────────────────────────────── */}
              {tabValue === 0 && (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Value at Risk (VaR) Calculator
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 2 }}
                  >
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
                        {loading ? "Calculating…" : "Calculate VaR"}
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
                                sx={{ fontWeight: 700 }}
                              >
                                {formatCurrency(
                                  varData?.var_amount ??
                                    riskSummary.valueAtRisk,
                                )}
                              </Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography
                                variant="body2"
                                color="text.secondary"
                              >
                                CVaR (Exp. Shortfall)
                              </Typography>
                              <Typography
                                variant="h5"
                                color="error.main"
                                sx={{ fontWeight: 700 }}
                              >
                                {formatCurrency(
                                  cvarData?.cvar_amount ?? riskSummary.cvar,
                                )}
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
                                sx={{ fontWeight: 600 }}
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
                                sx={{ fontWeight: 600 }}
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

              {/* ── CVaR ──────────────────────────────── */}
              {tabValue === 1 && (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    CVaR / Expected Shortfall
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 2 }}
                  >
                    CVaR measures the expected loss beyond the VaR threshold,
                    providing a fuller picture of tail risk.
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
                        {loading ? "Calculating…" : "Calculate CVaR"}
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
                            sx={{ fontWeight: 700, my: 1 }}
                          >
                            {formatCurrency(
                              cvarData?.cvar_amount ?? riskSummary.cvar,
                            )}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Average loss expected in the worst{" "}
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

              {/* ── Stress Testing ────────────────────── */}
              {tabValue === 2 && (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Stress Testing
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 2 }}
                  >
                    Simulate how your portfolio performs under extreme
                    historical or custom market conditions.
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                        <InputLabel>Scenario</InputLabel>
                        <Select
                          value={stressScenario}
                          label="Scenario"
                          onChange={(e) => handleScenarioChange(e.target.value)}
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
                      <Grid container spacing={2} alignItems="center">
                        {SHOCK_FIELDS.map(({ label, key }) => (
                          <React.Fragment key={key}>
                            <Grid item xs={7}>
                              <Typography variant="body2">{label}</Typography>
                            </Grid>
                            <Grid item xs={5}>
                              <TextField
                                size="small"
                                fullWidth
                                type="number"
                                value={stressParams[key]}
                                onChange={(e) =>
                                  setStressParams((p) => ({
                                    ...p,
                                    [key]: parseFloat(e.target.value) || 0,
                                  }))
                                }
                                InputProps={{ endAdornment: "%" }}
                              />
                            </Grid>
                          </React.Fragment>
                        ))}
                      </Grid>

                      <Button
                        variant="contained"
                        fullWidth
                        sx={{ mt: 2 }}
                        startIcon={
                          loading ? (
                            <CircularProgress size={16} color="inherit" />
                          ) : (
                            <CalculateIcon />
                          )
                        }
                        onClick={handleStressTest}
                        disabled={loading}
                      >
                        {loading ? "Running…" : "Run Stress Test"}
                      </Button>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Card
                        variant="outlined"
                        sx={{ backgroundColor: "background.default" }}
                      >
                        <CardContent>
                          <Typography variant="subtitle2" gutterBottom>
                            Results: {SCENARIO_LABELS[stressScenario]}
                          </Typography>
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="body2" color="text.secondary">
                              Estimated Portfolio Loss
                            </Typography>
                            <Typography
                              variant="h5"
                              color="error.main"
                              sx={{ fontWeight: 700 }}
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
                              <Divider sx={{ mb: 1.5 }} />
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
                                  label: "Gold (safe-haven)",
                                  value: stressResult.goldImpact,
                                },
                              ].map(({ label, value }) => (
                                <Box
                                  key={label}
                                  sx={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    mb: 0.8,
                                  }}
                                >
                                  <Typography variant="body2">
                                    {label}
                                  </Typography>
                                  <Typography
                                    variant="body2"
                                    color={
                                      value >= 0 ? "success.main" : "error.main"
                                    }
                                    sx={{ fontWeight: 700 }}
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

              {/* ── Correlation Analysis ──────────────── */}
              {tabValue === 3 && <CorrelationHeatmap />}

              {/* ── Risk Contribution ─────────────────── */}
              {tabValue === 4 && <RiskContributionChart />}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default RiskAnalysis;
