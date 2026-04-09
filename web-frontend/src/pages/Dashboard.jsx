import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import RefreshIcon from "@mui/icons-material/Refresh";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  Divider,
  Grid,
  IconButton,
  Typography,
} from "@mui/material";
import { useCallback } from "react";
import { Link } from "react-router-dom";
import AssetAllocation from "../components/dashboard/AssetAllocation";
import PerformanceChart from "../components/dashboard/PerformanceChart";
import RecentTransactions from "../components/dashboard/RecentTransactions";
import { useDashboardData } from "../hooks/useDashboardData";
import { formatCurrency, formatPercentage } from "../utils/formatters";

const Dashboard = () => {
  const { loading, error, dashboardData, reload } = useDashboardData();

  const handleRefresh = useCallback(() => {
    reload();
  }, [reload]);

  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "60vh",
        }}
      >
        <CircularProgress size={48} />
      </Box>
    );
  }

  const {
    portfolioValue,
    dailyChange,
    dailyChangePercent,
    riskScore,
    sharpeRatio,
    performanceData,
    assetAllocation,
    riskMetrics,
    recentTransactions,
  } = dashboardData;

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
          Dashboard
        </Typography>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          size="small"
          onClick={handleRefresh}
        >
          Refresh Data
        </Button>
      </Box>

      {error && (
        <Box sx={{ mb: 2 }}>
          <Typography color="error" variant="body2">
            {error}
          </Typography>
        </Box>
      )}

      {/* Portfolio Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Typography variant="subtitle2" color="text.secondary">
                  Total Portfolio Value
                </Typography>
                <IconButton size="small">
                  <MoreVertIcon fontSize="small" />
                </IconButton>
              </Box>
              <Typography variant="h4" sx={{ my: 1, fontWeight: 600 }}>
                {formatCurrency(portfolioValue)}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                {dailyChange >= 0 ? (
                  <TrendingUpIcon
                    color="success"
                    fontSize="small"
                    sx={{ mr: 0.5 }}
                  />
                ) : (
                  <TrendingDownIcon
                    color="error"
                    fontSize="small"
                    sx={{ mr: 0.5 }}
                  />
                )}
                <Typography
                  variant="body2"
                  color={dailyChange >= 0 ? "success.main" : "error.main"}
                >
                  {formatPercentage(dailyChangePercent, 2, true)} (
                  {formatCurrency(Math.abs(dailyChange))})
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Typography variant="subtitle2" color="text.secondary">
                  Daily Change
                </Typography>
                <IconButton size="small">
                  <MoreVertIcon fontSize="small" />
                </IconButton>
              </Box>
              <Typography
                variant="h4"
                sx={{
                  my: 1,
                  fontWeight: 600,
                  color: dailyChange >= 0 ? "success.main" : "error.main",
                }}
              >
                {dailyChange >= 0 ? "+" : ""}
                {formatCurrency(dailyChange)}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                {dailyChange >= 0 ? (
                  <TrendingUpIcon
                    color="success"
                    fontSize="small"
                    sx={{ mr: 0.5 }}
                  />
                ) : (
                  <TrendingDownIcon
                    color="error"
                    fontSize="small"
                    sx={{ mr: 0.5 }}
                  />
                )}
                <Typography
                  variant="body2"
                  color={dailyChange >= 0 ? "success.main" : "error.main"}
                >
                  {formatPercentage(dailyChangePercent, 2, true)} today
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Typography variant="subtitle2" color="text.secondary">
                  Risk Score
                </Typography>
                <IconButton size="small">
                  <MoreVertIcon fontSize="small" />
                </IconButton>
              </Box>
              <Typography variant="h4" sx={{ my: 1, fontWeight: 600 }}>
                {riskScore}/100
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <TrendingDownIcon
                  color="warning"
                  fontSize="small"
                  sx={{ mr: 0.5 }}
                />
                <Typography variant="body2" color="warning.main">
                  {riskScore < 30
                    ? "Low Risk"
                    : riskScore < 60
                      ? "Moderate Risk"
                      : "High Risk"}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Typography variant="subtitle2" color="text.secondary">
                  Sharpe Ratio
                </Typography>
                <IconButton size="small">
                  <MoreVertIcon fontSize="small" />
                </IconButton>
              </Box>
              <Typography variant="h4" sx={{ my: 1, fontWeight: 600 }}>
                {sharpeRatio?.toFixed(2) ?? "—"}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <TrendingUpIcon
                  color="success"
                  fontSize="small"
                  sx={{ mr: 0.5 }}
                />
                <Typography variant="body2" color="success.main">
                  {sharpeRatio > 2
                    ? "Excellent"
                    : sharpeRatio > 1
                      ? "Good Performance"
                      : "Fair"}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Content */}
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <PerformanceChart performanceData={performanceData} />
        </Grid>

        <Grid item xs={12} md={6} lg={4}>
          <AssetAllocation allocation={assetAllocation} />
        </Grid>

        {/* Risk Metrics */}
        <Grid item xs={12} md={6} lg={4}>
          <Card sx={{ height: "100%" }}>
            <CardHeader
              title="Risk Metrics"
              action={
                <IconButton>
                  <MoreVertIcon />
                </IconButton>
              }
            />
            <Divider />
            <CardContent sx={{ p: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Value at Risk (VaR)
                  </Typography>
                  <Typography variant="h6">
                    {formatCurrency(riskMetrics?.valueAtRisk)}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Max Drawdown
                  </Typography>
                  <Typography variant="h6">
                    {formatPercentage(riskMetrics?.maxDrawdown)}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Volatility
                  </Typography>
                  <Typography variant="h6">
                    {formatPercentage(riskMetrics?.volatility)}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Beta
                  </Typography>
                  <Typography variant="h6">
                    {riskMetrics?.beta?.toFixed(2) ?? "—"}
                  </Typography>
                </Grid>
              </Grid>
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="outlined"
                  fullWidth
                  size="small"
                  component={Link}
                  to="/risk-analysis"
                >
                  View Detailed Analysis
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={8}>
          <RecentTransactions transactions={recentTransactions} />
        </Grid>

        {/* Optimization Suggestions */}
        <Grid item xs={12} md={6} lg={4}>
          <Card>
            <CardHeader
              title="Optimization Suggestions"
              action={
                <IconButton>
                  <MoreVertIcon />
                </IconButton>
              }
            />
            <Divider />
            <CardContent>
              <Typography variant="body2" paragraph>
                Based on our AI analysis, we recommend the following portfolio
                adjustments:
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="success.main">
                  Increase:
                </Typography>
                <Typography variant="body2">
                  • Technology sector (+2.5%)
                </Typography>
                <Typography variant="body2">
                  • Healthcare stocks (+1.8%)
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="error.main">
                  Decrease:
                </Typography>
                <Typography variant="body2">• Energy sector (-3.1%)</Typography>
                <Typography variant="body2">
                  • Consumer discretionary (-1.2%)
                </Typography>
              </Box>
              <Button
                variant="contained"
                fullWidth
                size="small"
                component={Link}
                to="/optimization"
              >
                Run Optimization
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
