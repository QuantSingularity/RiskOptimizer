import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SaveAltIcon from "@mui/icons-material/SaveAlt";
import TuneIcon from "@mui/icons-material/Tune";
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
  FormControlLabel,
  Grid,
  IconButton,
  LinearProgress,
  MenuItem,
  Select,
  Slider,
  Snackbar,
  Switch,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from "@mui/material";
import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  ZAxis,
  Line,
  ComposedChart,
  Area,
} from "recharts";
import { usePortfolio } from "../context/PortfolioContext";
import { formatPercentage } from "../utils/formatters";

const ASSETS = [
  { name: "Apple Inc. (AAPL)", current: 15 },
  { name: "Microsoft Corp. (MSFT)", current: 12 },
  { name: "Amazon.com Inc. (AMZN)", current: 10 },
  { name: "Tesla Inc. (TSLA)", current: 8 },
  { name: "Alphabet Inc. (GOOGL)", current: 10 },
  { name: "Bitcoin (BTC)", current: 5 },
  { name: "Ethereum (ETH)", current: 5 },
  { name: "S&P 500 ETF (SPY)", current: 20 },
  { name: "Gold ETF (GLD)", current: 10 },
  { name: "Cash (USD)", current: 5 },
];

// Generate mock efficient frontier data
function generateEfficientFrontier(riskTolerance) {
  const points = [];
  for (let i = 0; i <= 25; i++) {
    const risk = 4 + i * 1.2;
    const ret = 2 + i * 0.85 - (i > 14 ? (i - 14) * 0.2 : 0);
    points.push({
      risk: parseFloat(risk.toFixed(2)),
      return: parseFloat(ret.toFixed(2)),
    });
  }
  // Mark optimal point based on risk tolerance
  const optIdx = Math.round((riskTolerance / 100) * 20);
  return { points, optimalIdx: optIdx };
}

const EfficientFrontierChart = ({ data, riskTolerance }) => {
  if (!data) return null;
  const { points, optimalIdx } = data;
  const optimal = points[optimalIdx];

  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        Efficient Frontier
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Each point represents an optimal portfolio for a given risk level. The
        highlighted point matches your risk tolerance.
      </Typography>
      <Box sx={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={points}
            margin={{ top: 10, right: 20, left: 0, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.06)"
            />
            <XAxis
              dataKey="risk"
              name="Risk"
              unit="%"
              tick={{ fill: "#b2bac2", fontSize: 10 }}
              tickLine={false}
              label={{
                value: "Risk (Volatility %)",
                position: "insideBottom",
                offset: -2,
                fill: "#b2bac2",
                fontSize: 11,
              }}
            />
            <YAxis
              dataKey="return"
              name="Return"
              unit="%"
              tick={{ fill: "#b2bac2", fontSize: 10 }}
              tickLine={false}
              label={{
                value: "Expected Return %",
                angle: -90,
                position: "insideLeft",
                fill: "#b2bac2",
                fontSize: 11,
              }}
            />
            <RechartsTooltip
              contentStyle={{
                backgroundColor: "#132f4c",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 8,
              }}
              formatter={(v, n) => [
                `${v}%`,
                n === "return" ? "Expected Return" : "Risk",
              ]}
            />
            <Area
              type="monotone"
              dataKey="return"
              stroke="#61dafb"
              strokeWidth={2.5}
              fill="rgba(97,218,251,0.08)"
              dot={(props) => {
                const isOptimal = props.index === optimalIdx;
                return isOptimal ? (
                  <circle
                    key={props.index}
                    cx={props.cx}
                    cy={props.cy}
                    r={8}
                    fill="#ff9800"
                    stroke="#fff"
                    strokeWidth={2}
                  />
                ) : (
                  <circle
                    key={props.index}
                    cx={props.cx}
                    cy={props.cy}
                    r={3}
                    fill="#61dafb"
                  />
                );
              }}
              activeDot={{ r: 6 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </Box>
      {optimal && (
        <Box sx={{ display: "flex", gap: 3, mt: 1 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Optimal Risk
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {optimal.risk}%
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Optimal Return
            </Typography>
            <Typography variant="body2" fontWeight={600} color="success.main">
              {optimal.return}%
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Implied Sharpe
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {(optimal.return / optimal.risk).toFixed(2)}
            </Typography>
          </Box>
        </Box>
      )}
    </Box>
  );
};

const AllocationBar = ({ name, current, optimized }) => {
  const diff = optimized - current;
  return (
    <Box sx={{ mb: 1.5 }}>
      <Grid container alignItems="center" spacing={1}>
        <Grid item xs={5}>
          <Typography variant="body2" noWrap>
            {name}
          </Typography>
        </Grid>
        <Grid item xs={3}>
          <Typography variant="body2" color="text.secondary" align="right">
            {current}%
          </Typography>
        </Grid>
        <Grid item xs={4}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              gap: 0.5,
            }}
          >
            <Typography
              variant="body2"
              sx={{
                fontWeight: 700,
                color:
                  diff > 0
                    ? "success.main"
                    : diff < 0
                      ? "error.main"
                      : "text.primary",
              }}
            >
              {diff > 0 ? "↑" : diff < 0 ? "↓" : "→"} {optimized}%
            </Typography>
          </Box>
        </Grid>
      </Grid>
      <Box sx={{ display: "flex", gap: 0.5, mt: 0.4 }}>
        <LinearProgress
          variant="determinate"
          value={current}
          sx={{
            flex: 1,
            height: 4,
            borderRadius: 2,
            backgroundColor: "rgba(255,255,255,0.08)",
            "& .MuiLinearProgress-bar": {
              backgroundColor: "rgba(97,218,251,0.45)",
            },
          }}
        />
        <LinearProgress
          variant="determinate"
          value={optimized}
          sx={{
            flex: 1,
            height: 4,
            borderRadius: 2,
            backgroundColor: "rgba(255,255,255,0.08)",
            "& .MuiLinearProgress-bar": {
              backgroundColor:
                diff > 0 ? "#4caf50" : diff < 0 ? "#f44336" : "#61dafb",
            },
          }}
        />
      </Box>
    </Box>
  );
};

const Optimization = () => {
  const { optimizePortfolio, loading, error, clearError } = usePortfolio();

  const [riskTolerance, setRiskTolerance] = useState(50);
  const [method, setMethod] = useState("sharpe");
  const [timeHorizon, setTimeHorizon] = useState("medium");
  const [noShortSelling, setNoShortSelling] = useState(true);
  const [maxPerAsset, setMaxPerAsset] = useState(true);
  const [includeESG, setIncludeESG] = useState(false);
  const [results, setResults] = useState(null);
  const [frontierData, setFrontierData] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [snackbar, setSnackbar] = useState({ open: false, message: "" });

  const handleRunOptimization = async () => {
    const params = {
      risk_tolerance: riskTolerance / 100,
      method,
      time_horizon: timeHorizon,
      constraints: {
        no_short_selling: noShortSelling,
        max_weight_per_asset: maxPerAsset ? 0.2 : 1.0,
        include_esg: includeESG,
      },
    };

    await optimizePortfolio(params);

    // Always use mock results (backend not required)
    const mockAllocations = ASSETS.map((a) => {
      const delta = Math.round((Math.random() - 0.5) * 6);
      return {
        name: a.name,
        current: a.current,
        optimized: Math.max(0, a.current + delta),
      };
    });

    const targetReturn = 8 + (riskTolerance / 100) * 8;
    const targetRisk = 6 + (riskTolerance / 100) * 10;

    setResults({
      expected_return: parseFloat(targetReturn.toFixed(1)),
      expected_risk: parseFloat(targetRisk.toFixed(1)),
      sharpe_ratio: parseFloat((targetReturn / targetRisk).toFixed(2)),
      allocations: mockAllocations,
    });

    setFrontierData(generateEfficientFrontier(riskTolerance));
    setActiveTab(0);
  };

  const handleSaveOptimization = () => {
    if (results) {
      setSnackbar({
        open: true,
        message: "Optimization applied successfully!",
      });
    }
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
        <Typography variant="h4" component="h1">
          Portfolio Optimization
        </Typography>
        <Button
          variant="contained"
          startIcon={<SaveAltIcon />}
          onClick={handleSaveOptimization}
          disabled={!results}
        >
          Apply Optimization
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Parameters */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: "100%" }}>
            <CardHeader
              title="Parameters"
              action={
                <IconButton>
                  <MoreVertIcon />
                </IconButton>
              }
            />
            <Divider />
            <CardContent>
              {/* Risk Tolerance */}
              <Box sx={{ mb: 3 }}>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Typography
                    variant="subtitle2"
                    sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
                  >
                    Risk Tolerance
                    <Tooltip title="Higher tolerance may yield higher returns with more volatility">
                      <InfoOutlinedIcon
                        sx={{ fontSize: 16, color: "text.secondary" }}
                      />
                    </Tooltip>
                  </Typography>
                  <Typography
                    variant="body2"
                    color={
                      riskTolerance < 33
                        ? "success.main"
                        : riskTolerance < 67
                          ? "warning.main"
                          : "error.main"
                    }
                    sx={{ fontWeight: 600 }}
                  >
                    {riskTolerance < 33
                      ? "Conservative"
                      : riskTolerance < 67
                        ? "Moderate"
                        : "Aggressive"}
                  </Typography>
                </Box>
                <Slider
                  value={riskTolerance}
                  onChange={(_, v) => setRiskTolerance(v)}
                  valueLabelDisplay="auto"
                  step={5}
                  marks
                  min={0}
                  max={100}
                />
              </Box>

              {/* Method */}
              <Box sx={{ mb: 2.5 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Optimization Method
                </Typography>
                <FormControl fullWidth size="small">
                  <Select
                    value={method}
                    onChange={(e) => setMethod(e.target.value)}
                  >
                    <MenuItem value="sharpe">Maximum Sharpe Ratio</MenuItem>
                    <MenuItem value="minrisk">Minimum Risk</MenuItem>
                    <MenuItem value="target">Target Return</MenuItem>
                    <MenuItem value="efficient">Efficient Frontier</MenuItem>
                  </Select>
                </FormControl>
              </Box>

              {/* Time Horizon */}
              <Box sx={{ mb: 2.5 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Time Horizon
                </Typography>
                <FormControl fullWidth size="small">
                  <Select
                    value={timeHorizon}
                    onChange={(e) => setTimeHorizon(e.target.value)}
                  >
                    <MenuItem value="short">Short Term (1–2 years)</MenuItem>
                    <MenuItem value="medium">Medium Term (3–5 years)</MenuItem>
                    <MenuItem value="long">Long Term (5+ years)</MenuItem>
                  </Select>
                </FormControl>
              </Box>

              {/* Constraints */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Constraints
                </Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={noShortSelling}
                      onChange={(e) => setNoShortSelling(e.target.checked)}
                    />
                  }
                  label="No Short Selling"
                  sx={{ display: "flex" }}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={maxPerAsset}
                      onChange={(e) => setMaxPerAsset(e.target.checked)}
                    />
                  }
                  label="Max 20% per Asset"
                  sx={{ display: "flex" }}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={includeESG}
                      onChange={(e) => setIncludeESG(e.target.checked)}
                    />
                  }
                  label="Include ESG Factors"
                  sx={{ display: "flex" }}
                />
              </Box>

              <Button
                variant="contained"
                fullWidth
                size="large"
                startIcon={
                  loading ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : (
                    <PlayArrowIcon />
                  )
                }
                onClick={handleRunOptimization}
                disabled={loading}
              >
                {loading ? "Optimizing..." : "Run Optimization"}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Results */}
        <Grid item xs={12} md={8}>
          <Card sx={{ height: "100%" }}>
            <CardHeader
              title="Results"
              subheader={
                results
                  ? `${method === "sharpe" ? "Max Sharpe" : method === "minrisk" ? "Min Risk" : method === "target" ? "Target Return" : "Efficient Frontier"} · ${timeHorizon} term`
                  : "Run optimization to see results"
              }
              action={
                results && (
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<TuneIcon />}
                    onClick={() => {
                      setResults(null);
                      setFrontierData(null);
                    }}
                  >
                    Reset
                  </Button>
                )
              }
            />
            <Divider />
            <CardContent>
              {results ? (
                <>
                  {/* Key metrics row */}
                  <Grid container spacing={2} sx={{ mb: 3 }}>
                    {[
                      {
                        label: "Expected Return",
                        value: formatPercentage(results.expected_return, 1),
                        color: "success.main",
                        sub: "Annualized",
                      },
                      {
                        label: "Expected Risk",
                        value: formatPercentage(results.expected_risk, 1),
                        color: "text.primary",
                        sub: "Volatility",
                      },
                      {
                        label: "Sharpe Ratio",
                        value: results.sharpe_ratio?.toFixed(2) ?? "—",
                        color: "primary.main",
                        sub:
                          results.sharpe_ratio > 2
                            ? "Excellent"
                            : results.sharpe_ratio > 1
                              ? "Above Average"
                              : "Fair",
                      },
                    ].map(({ label, value, color, sub }) => (
                      <Grid
                        item
                        xs={4}
                        key={label}
                        sx={{ textAlign: "center" }}
                      >
                        <Typography
                          variant="subtitle2"
                          color="text.secondary"
                          gutterBottom
                        >
                          {label}
                        </Typography>
                        <Typography
                          variant="h5"
                          sx={{ fontWeight: 700, color }}
                        >
                          {value}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {sub}
                        </Typography>
                      </Grid>
                    ))}
                  </Grid>

                  {/* Tabs: Allocation / Frontier */}
                  <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
                    <Tabs
                      value={activeTab}
                      onChange={(_, v) => setActiveTab(v)}
                      size="small"
                    >
                      <Tab label="Asset Allocation" />
                      <Tab label="Efficient Frontier" />
                    </Tabs>
                  </Box>

                  {activeTab === 0 && (
                    <Box>
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          mb: 1,
                        }}
                      >
                        <Typography variant="caption" color="text.secondary">
                          Asset
                        </Typography>
                        <Box sx={{ display: "flex", gap: 4 }}>
                          <Typography variant="caption" color="text.secondary">
                            Current
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Optimized
                          </Typography>
                        </Box>
                      </Box>
                      {results.allocations.map((a) => (
                        <AllocationBar key={a.name} {...a} />
                      ))}
                      <Box sx={{ mt: 3, display: "flex", gap: 2 }}>
                        <Button
                          variant="outlined"
                          fullWidth
                          onClick={() => setActiveTab(1)}
                        >
                          View Frontier
                        </Button>
                        <Button
                          variant="contained"
                          fullWidth
                          onClick={handleSaveOptimization}
                        >
                          Apply Allocation
                        </Button>
                      </Box>
                    </Box>
                  )}

                  {activeTab === 1 && (
                    <EfficientFrontierChart
                      data={frontierData}
                      riskTolerance={riskTolerance}
                    />
                  )}
                </>
              ) : (
                <Box
                  sx={{
                    height: 340,
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    alignItems: "center",
                    gap: 2,
                  }}
                >
                  <PlayArrowIcon
                    sx={{ fontSize: 60, color: "rgba(97,218,251,0.2)" }}
                  />
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    align="center"
                  >
                    Configure parameters and click &quot;Run Optimization&quot;
                    to see results.
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ open: false, message: "" })}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity="success">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default Optimization;
