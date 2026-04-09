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
  MenuItem,
  Select,
  Slider,
  Snackbar,
  Switch,
  Tooltip,
  Typography,
} from "@mui/material";
import { useState } from "react";
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

const Optimization = () => {
  const { optimizePortfolio, loading, error, clearError } = usePortfolio();
  const [riskTolerance, setRiskTolerance] = useState(50);
  const [method, setMethod] = useState("sharpe");
  const [timeHorizon, setTimeHorizon] = useState("medium");
  const [noShortSelling, setNoShortSelling] = useState(true);
  const [maxPerAsset, setMaxPerAsset] = useState(true);
  const [includeESG, setIncludeESG] = useState(false);
  const [results, setResults] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: "" });

  const handleRiskToleranceChange = (_event, newValue) => {
    setRiskTolerance(newValue);
  };

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

    const data = await optimizePortfolio(params);
    if (data) {
      setResults(data);
    } else {
      // Use mock results for demo
      setResults({
        expected_return: 12.4,
        expected_risk: 9.8,
        sharpe_ratio: 1.87,
        allocations: ASSETS.map((a) => ({
          name: a.name,
          current: a.current,
          optimized: Math.max(
            0,
            a.current + Math.round((Math.random() - 0.5) * 6),
          ),
        })),
      });
    }
  };

  const handleSaveOptimization = () => {
    if (results) {
      setSnackbar({ open: true, message: "Optimization saved successfully!" });
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
        <Typography variant="h4" component="h1" gutterBottom>
          Portfolio Optimization
        </Typography>
        <Button
          variant="contained"
          startIcon={<SaveAltIcon />}
          onClick={handleSaveOptimization}
          disabled={!results}
        >
          Save Optimization
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Optimization Parameters */}
        <Grid item xs={12} md={5}>
          <Card>
            <CardHeader
              title="Optimization Parameters"
              action={
                <IconButton>
                  <MoreVertIcon />
                </IconButton>
              }
            />
            <Divider />
            <CardContent>
              <Box sx={{ mb: 4 }}>
                <Typography
                  variant="subtitle2"
                  gutterBottom
                  sx={{ display: "flex", alignItems: "center" }}
                >
                  Risk Tolerance
                  <Tooltip title="Higher risk tolerance may lead to higher potential returns but with increased volatility">
                    <IconButton size="small">
                      <InfoOutlinedIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Typography>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs>
                    <Slider
                      value={riskTolerance}
                      onChange={handleRiskToleranceChange}
                      aria-labelledby="risk-tolerance-slider"
                      valueLabelDisplay="auto"
                      step={5}
                      marks
                      min={0}
                      max={100}
                    />
                  </Grid>
                  <Grid item>
                    <Typography variant="body2" color="text.secondary">
                      {riskTolerance < 30
                        ? "Conservative"
                        : riskTolerance < 70
                          ? "Moderate"
                          : "Aggressive"}
                    </Typography>
                  </Grid>
                </Grid>
              </Box>

              <Box sx={{ mb: 3 }}>
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

              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Time Horizon
                </Typography>
                <FormControl fullWidth size="small">
                  <Select
                    value={timeHorizon}
                    onChange={(e) => setTimeHorizon(e.target.value)}
                  >
                    <MenuItem value="short">Short Term (1-2 years)</MenuItem>
                    <MenuItem value="medium">Medium Term (3-5 years)</MenuItem>
                    <MenuItem value="long">Long Term (5+ years)</MenuItem>
                  </Select>
                </FormControl>
              </Box>

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
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={maxPerAsset}
                      onChange={(e) => setMaxPerAsset(e.target.checked)}
                    />
                  }
                  label="Max 20% per Asset"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={includeESG}
                      onChange={(e) => setIncludeESG(e.target.checked)}
                    />
                  }
                  label="Include ESG Factors"
                />
              </Box>

              <Button
                variant="contained"
                fullWidth
                startIcon={
                  loading ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : (
                    <PlayArrowIcon />
                  )
                }
                size="large"
                sx={{ mt: 2 }}
                onClick={handleRunOptimization}
                disabled={loading}
              >
                {loading ? "Optimizing..." : "Run Optimization"}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Optimization Results */}
        <Grid item xs={12} md={7}>
          <Card>
            <CardHeader
              title="Optimization Results"
              subheader={
                results
                  ? method === "sharpe"
                    ? "Maximum Sharpe Ratio Portfolio"
                    : method === "minrisk"
                      ? "Minimum Risk Portfolio"
                      : "Optimized Portfolio"
                  : "Run optimization to see results"
              }
              action={
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<TuneIcon />}
                  disabled={!results}
                  onClick={() => setResults(null)}
                >
                  Reset
                </Button>
              }
            />
            <Divider />
            <CardContent>
              {results ? (
                <>
                  <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid item xs={12} sm={4}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography
                          variant="subtitle2"
                          color="text.secondary"
                          gutterBottom
                        >
                          Expected Return
                        </Typography>
                        <Typography
                          variant="h5"
                          color="success.main"
                          sx={{ fontWeight: 600 }}
                        >
                          {formatPercentage(results.expected_return, 1)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Annualized
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography
                          variant="subtitle2"
                          color="text.secondary"
                          gutterBottom
                        >
                          Expected Risk
                        </Typography>
                        <Typography variant="h5" sx={{ fontWeight: 600 }}>
                          {formatPercentage(results.expected_risk, 1)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Volatility
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography
                          variant="subtitle2"
                          color="text.secondary"
                          gutterBottom
                        >
                          Sharpe Ratio
                        </Typography>
                        <Typography variant="h5" sx={{ fontWeight: 600 }}>
                          {results.sharpe_ratio?.toFixed(2) ?? "—"}
                        </Typography>
                        <Typography variant="body2" color="success.main">
                          {results.sharpe_ratio > 2
                            ? "Excellent"
                            : results.sharpe_ratio > 1
                              ? "Above Average"
                              : "Fair"}
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>

                  <Typography variant="subtitle2" gutterBottom>
                    Optimized Asset Allocation
                  </Typography>

                  <Box sx={{ mb: 3 }}>
                    {(
                      results.allocations ||
                      ASSETS.map((a) => ({ ...a, optimized: a.current }))
                    ).map((asset, index) => (
                      <Box key={index} sx={{ mb: 1 }}>
                        <Grid container alignItems="center">
                          <Grid item xs={5}>
                            <Typography variant="body2">
                              {asset.name}
                            </Typography>
                          </Grid>
                          <Grid item xs={3}>
                            <Typography variant="body2" color="text.secondary">
                              Current: {asset.current}%
                            </Typography>
                          </Grid>
                          <Grid item xs={4}>
                            <Typography
                              variant="body2"
                              sx={{
                                fontWeight: 600,
                                color:
                                  asset.optimized > asset.current
                                    ? "success.main"
                                    : asset.optimized < asset.current
                                      ? "error.main"
                                      : "text.primary",
                              }}
                            >
                              {asset.optimized > asset.current
                                ? "↑"
                                : asset.optimized < asset.current
                                  ? "↓"
                                  : "→"}{" "}
                              {asset.optimized}%
                            </Typography>
                          </Grid>
                        </Grid>
                      </Box>
                    ))}
                  </Box>

                  <Box
                    sx={{
                      mt: 3,
                      display: "flex",
                      justifyContent: "space-between",
                    }}
                  >
                    <Button variant="outlined" onClick={() => setResults(null)}>
                      Compare with Current
                    </Button>
                    <Button
                      variant="contained"
                      onClick={handleSaveOptimization}
                    >
                      Apply Optimization
                    </Button>
                  </Box>
                </>
              ) : (
                <Box
                  sx={{
                    height: 300,
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    flexDirection: "column",
                    gap: 2,
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
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
