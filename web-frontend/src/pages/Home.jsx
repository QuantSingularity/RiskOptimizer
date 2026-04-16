import AssessmentIcon from "@mui/icons-material/Assessment";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import SecurityIcon from "@mui/icons-material/Security";
import SpeedIcon from "@mui/icons-material/Speed";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Divider,
  Grid,
  Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const features = [
  {
    icon: <AutoGraphIcon sx={{ fontSize: 40 }} />,
    title: "AI-Powered Optimization",
    description:
      "Leverage cutting-edge algorithms to find the optimal asset allocation that maximizes returns for your risk tolerance.",
    color: "#61dafb",
  },
  {
    icon: <AssessmentIcon sx={{ fontSize: 40 }} />,
    title: "Advanced Risk Analysis",
    description:
      "Calculate VaR, CVaR, Sharpe Ratio, and run stress tests against historical market crises.",
    color: "#4caf50",
  },
  {
    icon: <SecurityIcon sx={{ fontSize: 40 }} />,
    title: "Portfolio Protection",
    description:
      "Monitor drawdown, volatility, and correlation to protect your portfolio from unexpected market events.",
    color: "#ff9800",
  },
  {
    icon: <SpeedIcon sx={{ fontSize: 40 }} />,
    title: "Real-Time Monitoring",
    description:
      "Track portfolio performance in real-time with interactive charts and live risk metrics.",
    color: "#e91e63",
  },
];

const stats = [
  { label: "Assets Tracked", value: "10,000+" },
  { label: "Avg. Sharpe Improvement", value: "+38%" },
  { label: "Portfolios Optimized", value: "5,200+" },
  { label: "Risk Reduction", value: "Up to 22%" },
];

const Home = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleGetStarted = () => {
    if (user) {
      navigate("/dashboard");
    } else {
      navigate("/login");
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "linear-gradient(135deg, #0a1929 0%, #0d2137 50%, #0a1929 100%)",
        color: "white",
      }}
    >
      {/* Hero Section */}
      <Box
        sx={{
          position: "relative",
          overflow: "hidden",
          pt: { xs: 10, md: 14 },
          pb: { xs: 8, md: 12 },
        }}
      >
        {/* Background decorative elements */}
        <Box
          sx={{
            position: "absolute",
            top: -100,
            right: -100,
            width: 600,
            height: 600,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(97,218,251,0.08) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />
        <Box
          sx={{
            position: "absolute",
            bottom: -200,
            left: -200,
            width: 700,
            height: 700,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(255,152,0,0.06) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />

        <Container maxWidth="lg">
          <Box sx={{ textAlign: "center", position: "relative", zIndex: 1 }}>
            <Chip
              label="AI-Powered Portfolio Intelligence"
              sx={{
                mb: 3,
                backgroundColor: "rgba(97,218,251,0.1)",
                color: "#61dafb",
                border: "1px solid rgba(97,218,251,0.3)",
                fontWeight: 600,
                fontSize: "0.8rem",
                px: 1,
              }}
            />
            <Typography
              variant="h1"
              component="h1"
              sx={{
                fontSize: { xs: "2.5rem", md: "4rem", lg: "5rem" },
                fontWeight: 800,
                lineHeight: 1.1,
                mb: 3,
                background:
                  "linear-gradient(135deg, #ffffff 30%, #61dafb 100%)",
                backgroundClip: "text",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                fontFamily: "Poppins, sans-serif",
              }}
            >
              Optimize Your
              <br />
              Portfolio Risk
            </Typography>
            <Typography
              variant="h5"
              sx={{
                color: "rgba(255,255,255,0.65)",
                maxWidth: 600,
                mx: "auto",
                mb: 5,
                lineHeight: 1.6,
                fontWeight: 400,
                fontSize: { xs: "1rem", md: "1.25rem" },
              }}
            >
              Professional-grade risk analytics and portfolio optimization
              powered by quantitative finance algorithms.
            </Typography>
            <Box
              sx={{
                display: "flex",
                gap: 2,
                justifyContent: "center",
                flexWrap: "wrap",
              }}
            >
              <Button
                variant="contained"
                size="large"
                onClick={handleGetStarted}
                startIcon={<TrendingUpIcon />}
                sx={{
                  py: 1.8,
                  px: 5,
                  fontSize: "1rem",
                  fontWeight: 700,
                  borderRadius: 3,
                  background:
                    "linear-gradient(135deg, #61dafb 0%, #4db8d9 100%)",
                  color: "#0a1929",
                  boxShadow: "0 8px 32px rgba(97,218,251,0.35)",
                  "&:hover": {
                    background:
                      "linear-gradient(135deg, #8be9fd 0%, #61dafb 100%)",
                    boxShadow: "0 12px 40px rgba(97,218,251,0.5)",
                    transform: "translateY(-2px)",
                  },
                  transition: "all 0.2s ease",
                }}
              >
                {user ? "Go to Dashboard" : "Get Started Free"}
              </Button>
              <Button
                variant="outlined"
                size="large"
                onClick={() => navigate("/dashboard")}
                sx={{
                  py: 1.8,
                  px: 5,
                  fontSize: "1rem",
                  borderRadius: 3,
                  borderColor: "rgba(97,218,251,0.4)",
                  color: "#61dafb",
                  "&:hover": {
                    borderColor: "#61dafb",
                    backgroundColor: "rgba(97,218,251,0.07)",
                  },
                }}
              >
                View Demo
              </Button>
            </Box>
          </Box>
        </Container>
      </Box>

      {/* Stats Row */}
      <Container maxWidth="lg" sx={{ pb: 8 }}>
        <Card
          sx={{
            background: "rgba(19, 47, 76, 0.8)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(97,218,251,0.15)",
            borderRadius: 4,
            p: { xs: 3, md: 4 },
          }}
        >
          <Grid container spacing={2} justifyContent="space-evenly">
            {stats.map((stat, index) => (
              <Grid item xs={6} md={3} key={index} sx={{ textAlign: "center" }}>
                <Typography
                  variant="h3"
                  sx={{
                    fontWeight: 800,
                    color: "#61dafb",
                    fontFamily: "Poppins, sans-serif",
                    fontSize: { xs: "1.8rem", md: "2.5rem" },
                  }}
                >
                  {stat.value}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{ color: "rgba(255,255,255,0.55)", mt: 0.5 }}
                >
                  {stat.label}
                </Typography>
              </Grid>
            ))}
          </Grid>
        </Card>
      </Container>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ pb: 10 }}>
        <Box sx={{ textAlign: "center", mb: 7 }}>
          <Typography
            variant="overline"
            sx={{ color: "#61dafb", fontWeight: 700, letterSpacing: 3 }}
          >
            CAPABILITIES
          </Typography>
          <Typography
            variant="h3"
            sx={{
              fontWeight: 700,
              mt: 1,
              fontFamily: "Poppins, sans-serif",
              fontSize: { xs: "1.8rem", md: "2.5rem" },
            }}
          >
            Everything You Need to Manage Risk
          </Typography>
          <Typography
            variant="body1"
            sx={{
              color: "rgba(255,255,255,0.55)",
              mt: 2,
              maxWidth: 560,
              mx: "auto",
            }}
          >
            From individual asset analysis to full portfolio optimization,
            RiskOptimizer provides institutional-grade tools for every investor.
          </Typography>
        </Box>

        <Grid container spacing={3}>
          {features.map((feature, index) => (
            <Grid item xs={12} sm={6} key={index}>
              <Card
                sx={{
                  height: "100%",
                  background: "rgba(19, 47, 76, 0.6)",
                  backdropFilter: "blur(10px)",
                  border: "1px solid rgba(255,255,255,0.07)",
                  borderRadius: 4,
                  transition: "all 0.3s ease",
                  "&:hover": {
                    border: `1px solid ${feature.color}44`,
                    transform: "translateY(-4px)",
                    boxShadow: `0 20px 60px rgba(0,0,0,0.4), 0 0 30px ${feature.color}18`,
                  },
                }}
              >
                <CardContent sx={{ p: 4 }}>
                  <Box
                    sx={{
                      display: "inline-flex",
                      p: 1.5,
                      borderRadius: 3,
                      backgroundColor: `${feature.color}18`,
                      color: feature.color,
                      mb: 2.5,
                    }}
                  >
                    {feature.icon}
                  </Box>
                  <Typography
                    variant="h6"
                    sx={{
                      fontWeight: 700,
                      mb: 1.5,
                      fontFamily: "Poppins, sans-serif",
                    }}
                  >
                    {feature.title}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{ color: "rgba(255,255,255,0.6)", lineHeight: 1.7 }}
                  >
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* CTA Section */}
      <Container maxWidth="md" sx={{ pb: 12 }}>
        <Card
          sx={{
            background:
              "linear-gradient(135deg, rgba(97,218,251,0.12) 0%, rgba(19,47,76,0.9) 100%)",
            border: "1px solid rgba(97,218,251,0.25)",
            borderRadius: 5,
            p: { xs: 4, md: 7 },
            textAlign: "center",
          }}
        >
          <Typography
            variant="h4"
            sx={{ fontWeight: 700, mb: 2, fontFamily: "Poppins, sans-serif" }}
          >
            Ready to Optimize Your Portfolio?
          </Typography>
          <Typography
            variant="body1"
            sx={{
              color: "rgba(255,255,255,0.6)",
              mb: 4,
              maxWidth: 450,
              mx: "auto",
            }}
          >
            Join thousands of investors who use RiskOptimizer to make
            data-driven portfolio decisions.
          </Typography>
          <Divider sx={{ mb: 4, borderColor: "rgba(255,255,255,0.1)" }} />
          <Button
            variant="contained"
            size="large"
            onClick={handleGetStarted}
            sx={{
              py: 1.8,
              px: 6,
              fontSize: "1rem",
              fontWeight: 700,
              borderRadius: 3,
              background: "linear-gradient(135deg, #61dafb 0%, #4db8d9 100%)",
              color: "#0a1929",
              "&:hover": {
                background: "linear-gradient(135deg, #8be9fd 0%, #61dafb 100%)",
                transform: "translateY(-2px)",
              },
              transition: "all 0.2s ease",
            }}
          >
            {user ? "Open Dashboard" : "Start for Free"}
          </Button>
        </Card>
      </Container>

      {/* Footer */}
      <Box
        sx={{
          borderTop: "1px solid rgba(255,255,255,0.07)",
          py: 4,
          textAlign: "center",
        }}
      >
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.35)" }}>
          © {new Date().getFullYear()} RiskOptimizer · AI-Powered Portfolio
          Optimization
        </Typography>
      </Box>
    </Box>
  );
};

export default Home;
