import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RemoveIcon from "@mui/icons-material/Remove";
import SaveAltIcon from "@mui/icons-material/SaveAlt";
import TuneIcon from "@mui/icons-material/Tune";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
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
import { useEffect, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { usePortfolio } from "../context/PortfolioContext";
import apiService from "../services/apiService";
import { formatPercentage } from "../utils/formatters";
import {
  CAP_PER_ASSET,
  METHODS,
  MIN_ASSETS,
  SYMBOL_NAMES,
  buildOptimizationRequest,
  buildResults,
} from "../utils/optimization";

const methodLabel = (value) =>
  METHODS.find((method) => method.value === value)?.label || value;

const EfficientFrontierChart = ({ data, sharpe }) => {
  if (!data) {
    return (
      <Typography variant="body2" color="text.secondary">
        The efficient frontier could not be computed for this selection.
      </Typography>
    );
  }
  const { points, optimalIdx } = data;
  const optimal = points[optimalIdx];

  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        Efficient Frontier
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Each point is the lowest risk portfolio for a given expected return. The
        highlighted point is closest to your optimized portfolio.
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
              type="number"
              domain={["dataMin", "dataMax"]}
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
                return (
                  <circle
                    key={props.index}
                    cx={props.cx}
                    cy={props.cy}
                    r={isOptimal ? 8 : 3}
                    fill={isOptimal ? "#ff9800" : "#61dafb"}
                    stroke={isOptimal ? "#fff" : "none"}
                    strokeWidth={isOptimal ? 2 : 0}
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
              Nearest Frontier Risk
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {optimal.risk}%
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Nearest Frontier Return
            </Typography>
            <Typography variant="body2" fontWeight={600} color="success.main">
              {optimal.return}%
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Portfolio Sharpe
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {sharpe?.toFixed(2) ?? "-"}
            </Typography>
          </Box>
        </Box>
      )}
    </Box>
  );
};

const AllocationBar = ({ name, current, optimized }) => {
  const diff = optimized - current;
  const color =
    diff > 0.05 ? "success.main" : diff < -0.05 ? "error.main" : "text.primary";
  const Icon =
    diff > 0.05
      ? ArrowUpwardIcon
      : diff < -0.05
        ? ArrowDownwardIcon
        : RemoveIcon;
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
              color,
            }}
          >
            <Icon sx={{ fontSize: 16 }} />
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {optimized}%
            </Typography>
          </Box>
        </Grid>
      </Grid>
      <Box sx={{ display: "flex", gap: 0.5, mt: 0.4 }}>
        <LinearProgress
          variant="determinate"
          value={Math.min(100, current)}
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
          value={Math.min(100, optimized)}
          sx={{
            flex: 1,
            height: 4,
            borderRadius: 2,
            backgroundColor: "rgba(255,255,255,0.08)",
            "& .MuiLinearProgress-bar": {
              backgroundColor:
                diff > 0.05 ? "#4caf50" : diff < -0.05 ? "#f44336" : "#61dafb",
            },
          }}
        />
      </Box>
    </Box>
  );
};

const Optimization = () => {
  const {
    portfolio,
    optimizePortfolio,
    savePortfolio,
    loading,
    error,
    clearError,
  } = usePortfolio();

  const [availableSymbols, setAvailableSymbols] = useState([]);
  const [selectedSymbols, setSelectedSymbols] = useState([]);
  const [symbolsLoading, setSymbolsLoading] = useState(true);
  const [symbolsError, setSymbolsError] = useState(null);
  const [riskTolerance, setRiskTolerance] = useState(50);
  const [method, setMethod] = useState("utility");
  const [capEnabled, setCapEnabled] = useState(false);
  const [results, setResults] = useState(null);
  const [frontierData, setFrontierData] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "success",
  });

  useEffect(() => {
    let active = true;
    apiService.optimization
      .getSymbols()
      .then((response) => {
        if (!active) return;
        const symbols = response.data?.symbols || [];
        setAvailableSymbols(symbols);
        setSelectedSymbols(symbols);
      })
      .catch((err) => {
        if (active) setSymbolsError(err.message || "Failed to load assets");
      })
      .finally(() => {
        if (active) setSymbolsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const toggleSymbol = (symbol) => {
    setSelectedSymbols((current) =>
      current.includes(symbol)
        ? current.filter((item) => item !== symbol)
        : availableSymbols.filter((item) =>
            [...current, symbol].includes(item),
          ),
    );
  };

  const canRun = selectedSymbols.length >= MIN_ASSETS && !loading;

  const handleRunOptimization = async () => {
    const request = buildOptimizationRequest({
      symbols: selectedSymbols,
      slider: riskTolerance,
      method,
      capEnabled,
    });
    const response = await optimizePortfolio(request);
    if (!response) return;
    const built = buildResults({
      optimization: response.optimization,
      frontier: response.frontier,
      symbols: selectedSymbols,
      assets: portfolio?.assets,
    });
    setResults(built.results);
    setFrontierData(built.frontierData);
    setActiveTab(0);
  };

  const handleSaveOptimization = async () => {
    if (!results) return;
    const saved = await savePortfolio({
      target_allocation: results.weights,
    });
    setSnackbar({
      open: true,
      severity: saved ? "success" : "error",
      message: saved
        ? "Target allocation saved to your portfolio"
        : "Could not save the target allocation",
    });
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
          disabled={!results || loading}
        >
          Save Target Allocation
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
          {error}
        </Alert>
      )}
      {symbolsError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {symbolsError}
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: "100%" }}>
            <CardHeader title="Parameters" />
            <Divider />
            <CardContent>
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Assets ({selectedSymbols.length} selected)
                </Typography>
                {symbolsLoading ? (
                  <CircularProgress size={20} />
                ) : (
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
                    {availableSymbols.map((symbol) => {
                      const selected = selectedSymbols.includes(symbol);
                      return (
                        <Tooltip
                          key={symbol}
                          title={SYMBOL_NAMES[symbol] || symbol}
                        >
                          <Chip
                            label={symbol.replace("_", "-")}
                            size="small"
                            color={selected ? "primary" : "default"}
                            variant={selected ? "filled" : "outlined"}
                            onClick={() => toggleSymbol(symbol)}
                          />
                        </Tooltip>
                      );
                    })}
                  </Box>
                )}
                {!symbolsLoading && selectedSymbols.length < MIN_ASSETS && (
                  <Typography variant="caption" color="error">
                    Select at least {MIN_ASSETS} assets
                  </Typography>
                )}
              </Box>

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
                    <Tooltip title="Higher tolerance accepts more volatility for higher expected return. It applies to the Risk Tolerance Utility method.">
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
                  disabled={method !== "utility"}
                />
              </Box>

              <Box sx={{ mb: 2.5 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Optimization Method
                </Typography>
                <FormControl fullWidth size="small">
                  <Select
                    value={method}
                    onChange={(e) => setMethod(e.target.value)}
                  >
                    {METHODS.map((item) => (
                      <MenuItem key={item.value} value={item.value}>
                        {item.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>

              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Constraints
                </Typography>
                <FormControlLabel
                  control={<Switch checked disabled />}
                  label="Long Only"
                  sx={{ display: "flex" }}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={capEnabled}
                      onChange={(e) => setCapEnabled(e.target.checked)}
                    />
                  }
                  label={`Max ${Math.round(CAP_PER_ASSET * 100)}% per Asset`}
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
                disabled={!canRun}
              >
                {loading ? "Optimizing..." : "Run Optimization"}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card sx={{ height: "100%" }}>
            <CardHeader
              title="Results"
              subheader={
                results
                  ? `${methodLabel(results.method)} | ${
                      results.model_type === "ml"
                        ? "ML return model"
                        : "Historical mean model"
                    }`
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
                        value: results.sharpe_ratio?.toFixed(2) ?? "-",
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
                            {results.current_basis === "portfolio"
                              ? "Current"
                              : "Equal Weight"}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Optimized
                          </Typography>
                        </Box>
                      </Box>
                      {results.allocations.map((a) => (
                        <AllocationBar key={a.symbol} {...a} />
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
                          disabled={loading}
                        >
                          Save Allocation
                        </Button>
                      </Box>
                    </Box>
                  )}

                  {activeTab === 1 && (
                    <EfficientFrontierChart
                      data={frontierData}
                      sharpe={results.sharpe_ratio}
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
                    Choose assets and parameters, then click &quot;Run
                    Optimization&quot; to see results.
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
        onClose={() => setSnackbar((current) => ({ ...current, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default Optimization;
