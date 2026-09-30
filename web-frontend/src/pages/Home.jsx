import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import BoltIcon from "@mui/icons-material/Bolt";
import InsightsIcon from "@mui/icons-material/Insights";
import SecurityIcon from "@mui/icons-material/Security";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import TuneIcon from "@mui/icons-material/Tune";
import {
  Box,
  Button,
  Card,
  Chip,
  Container,
  Grid,
  Stack,
  Typography,
} from "@mui/material";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { mono } from "../theme";

const features = [
  {
    icon: <ShowChartIcon />,
    title: "Value at Risk and CVaR",
    body: "Historical and parametric tail-risk estimates on your return series, computed server-side and returned with full precision.",
  },
  {
    icon: <InsightsIcon />,
    title: "Risk-adjusted performance",
    body: "Sharpe ratio, maximum drawdown, and portfolio metrics from a single return stream, ready to compare across strategies.",
  },
  {
    icon: <TuneIcon />,
    title: "Efficient frontier",
    body: "Trace the risk-return frontier for a set of assets and see where a candidate allocation sits against the optimum.",
  },
  {
    icon: <SecurityIcon />,
    title: "Token-based access",
    body: "JWT authentication with refresh, so a session stays live without re-entering credentials on every request.",
  },
  {
    icon: <BoltIcon />,
    title: "Live system status",
    body: "Watch API, cache, and database health from the monitoring panel, with the same numbers the operators see.",
  },
  {
    icon: <AutoGraphIcon />,
    title: "Built for iteration",
    body: "Type returns or paste a series, run a metric, adjust, and rerun. The desk is built for fast what-if loops.",
  },
];

const stats = [
  { value: "6", label: "Risk metrics served" },
  { value: "0.95", label: "Default confidence" },
  { value: "JWT", label: "Session security" },
];

const Home = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    // Returning, authenticated users skip the marketing page.
    if (user) navigate("/dashboard", { replace: true });
  }, [user, navigate]);

  return (
    <Box
      sx={{ width: "100%", minHeight: "100vh", bgcolor: "background.default" }}
    >
      {/* Top bar */}
      <Box
        sx={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          backdropFilter: "blur(10px)",
          bgcolor: "rgba(10,15,30,0.7)",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Container maxWidth="lg">
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ height: 68 }}
          >
            <Typography
              variant="h6"
              sx={{ fontWeight: 700, letterSpacing: "-0.01em" }}
            >
              Risk<span style={{ color: "#5B8DEF" }}>Optimizer</span>
            </Typography>
            <Stack direction="row" spacing={1.5}>
              <Button color="inherit" onClick={() => navigate("/login")}>
                Sign in
              </Button>
              <Button variant="contained" onClick={() => navigate("/register")}>
                Create account
              </Button>
            </Stack>
          </Stack>
        </Container>
      </Box>

      {/* Hero */}
      <Container
        maxWidth="lg"
        sx={{ pt: { xs: 8, md: 12 }, pb: { xs: 6, md: 10 } }}
      >
        <Grid container spacing={6} alignItems="center">
          <Grid item xs={12} md={7}>
            <Chip
              label="Quantitative portfolio risk"
              size="small"
              sx={{
                mb: 3,
                bgcolor: "rgba(91,141,239,0.12)",
                color: "primary.light",
                border: "1px solid rgba(91,141,239,0.3)",
              }}
            />
            <Typography
              variant="h2"
              sx={{
                fontSize: { xs: "2.4rem", md: "3.4rem" },
                lineHeight: 1.05,
                mb: 2.5,
              }}
            >
              Measure the risk before
              <br />
              you commit the capital.
            </Typography>
            <Typography
              variant="h6"
              sx={{
                color: "text.secondary",
                fontWeight: 400,
                maxWidth: 560,
                mb: 4,
              }}
            >
              RiskOptimizer turns a return series into the numbers that matter:
              value at risk, expected shortfall, Sharpe, drawdown, and the
              efficient frontier. No spreadsheets, no guesswork.
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <Button
                size="large"
                variant="contained"
                onClick={() => navigate("/register")}
                sx={{ py: 1.4, px: 3.5 }}
              >
                Get started free
              </Button>
              <Button
                size="large"
                variant="outlined"
                onClick={() => navigate("/login")}
                sx={{ py: 1.4, px: 3.5 }}
              >
                Sign in
              </Button>
            </Stack>

            <Stack direction="row" spacing={5} sx={{ mt: 6 }}>
              {stats.map((s) => (
                <Box key={s.label}>
                  <Typography
                    sx={{
                      fontFamily: mono,
                      fontSize: "1.8rem",
                      fontWeight: 600,
                      color: "secondary.main",
                    }}
                  >
                    {s.value}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {s.label}
                  </Typography>
                </Box>
              ))}
            </Stack>
          </Grid>

          {/* Signature: a mock risk readout in tabular mono */}
          <Grid item xs={12} md={5}>
            <Card sx={{ p: 3 }}>
              <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="center"
                sx={{ mb: 2 }}
              >
                <Typography variant="overline" color="text.secondary">
                  Risk readout
                </Typography>
                <Chip
                  size="small"
                  label="95% confidence"
                  sx={{
                    bgcolor: "rgba(52,199,123,0.12)",
                    color: "success.main",
                  }}
                />
              </Stack>
              {[
                ["Value at Risk", "-2.53%", "negative"],
                ["Conditional VaR", "-3.81%", "negative"],
                ["Sharpe ratio", "1.42", "neutral"],
                ["Max drawdown", "-11.7%", "negative"],
                ["Annualized return", "+14.2%", "positive"],
              ].map(([label, value, tone]) => (
                <Stack
                  key={label}
                  direction="row"
                  justifyContent="space-between"
                  sx={{
                    py: 1.4,
                    borderBottom: "1px solid",
                    borderColor: "divider",
                    "&:last-of-type": { borderBottom: 0 },
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    {label}
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: mono,
                      fontVariantNumeric: "tabular-nums",
                      fontWeight: 600,
                      color:
                        tone === "positive"
                          ? "success.main"
                          : tone === "negative"
                            ? "error.main"
                            : "text.primary",
                    }}
                  >
                    {value}
                  </Typography>
                </Stack>
              ))}
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "block", mt: 2 }}
              >
                Illustrative figures. Sign in to compute on your own series.
              </Typography>
            </Card>
          </Grid>
        </Grid>
      </Container>

      {/* Features */}
      <Container maxWidth="lg" sx={{ pb: { xs: 8, md: 12 } }}>
        <Typography variant="overline" color="primary.light">
          What you get
        </Typography>
        <Typography variant="h4" sx={{ mb: 5, mt: 1 }}>
          A risk desk, not a dashboard
        </Typography>
        <Grid container spacing={3}>
          {features.map((f) => (
            <Grid item xs={12} sm={6} md={4} key={f.title}>
              <Card sx={{ p: 3, height: "100%" }}>
                <Box
                  sx={{
                    width: 44,
                    height: 44,
                    borderRadius: 2,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    bgcolor: "rgba(91,141,239,0.12)",
                    color: "primary.light",
                    mb: 2,
                  }}
                >
                  {f.icon}
                </Box>
                <Typography variant="h6" sx={{ mb: 1, fontSize: "1.05rem" }}>
                  {f.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {f.body}
                </Typography>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* CTA */}
      <Container maxWidth="lg" sx={{ pb: { xs: 10, md: 14 } }}>
        <Card
          sx={{
            p: { xs: 4, md: 6 },
            textAlign: "center",
            background:
              "linear-gradient(135deg, rgba(91,141,239,0.14), rgba(229,181,103,0.08))",
          }}
        >
          <Typography variant="h4" sx={{ mb: 1.5 }}>
            Run your first risk report in minutes
          </Typography>
          <Typography
            color="text.secondary"
            sx={{ mb: 3, maxWidth: 520, mx: "auto" }}
          >
            Create an account, paste a return series, and get value at risk,
            Sharpe, and drawdown on the same screen.
          </Typography>
          <Button
            size="large"
            variant="contained"
            onClick={() => navigate("/register")}
            sx={{ py: 1.4, px: 4 }}
          >
            Create your account
          </Button>
        </Card>
      </Container>

      <Box sx={{ borderTop: "1px solid", borderColor: "divider", py: 3 }}>
        <Container maxWidth="lg">
          <Typography variant="caption" color="text.secondary">
            RiskOptimizer - quantitative portfolio risk. For research and
            educational use; not investment advice.
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

export default Home;
