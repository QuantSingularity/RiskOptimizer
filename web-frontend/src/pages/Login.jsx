import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import {
  Alert,
  Avatar,
  Box,
  Button,
  CircularProgress,
  Container,
  Divider,
  Paper,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Login = () => {
  const [tab, setTab] = useState(0);
  const [formData, setFormData] = useState({
    wallet_address: "",
    email: "",
    password: "",
    username: "",
  });
  const [localError, setLocalError] = useState("");
  const { login, register, loading, error, user, clearError } = useAuth();
  const navigate = useNavigate();

  // Redirect if already authenticated
  useEffect(() => {
    if (user) navigate("/dashboard", { replace: true });
  }, [user, navigate]);

  useEffect(() => {
    return () => clearError();
  }, [clearError]);

  const handleTabChange = (_, newValue) => {
    setTab(newValue);
    setLocalError("");
    clearError();
  };

  const handleChange = (field) => (e) => {
    setFormData((prev) => ({ ...prev, [field]: e.target.value }));
    setLocalError("");
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLocalError("");
    if (!formData.wallet_address) {
      setLocalError("Please enter a wallet address");
      return;
    }
    const success = await login({ wallet_address: formData.wallet_address });
    if (success) navigate("/dashboard");
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setLocalError("");
    if (
      !formData.username ||
      !formData.email ||
      !formData.password ||
      !formData.wallet_address
    ) {
      setLocalError("All fields are required");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setLocalError("Please enter a valid email address");
      return;
    }
    if (formData.password.length < 6) {
      setLocalError("Password must be at least 6 characters");
      return;
    }
    const success = await register({
      username: formData.username,
      email: formData.email,
      password: formData.password,
      wallet_address: formData.wallet_address,
    });
    if (success) navigate("/dashboard");
  };

  const handleDemoLogin = async () => {
    const success = await login({
      wallet_address: "0xDEMO1234567890ABCDEFdemo",
    });
    if (success) navigate("/dashboard");
  };

  const displayError = localError || error;

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
        className="fade-in"
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            backgroundColor: "background.paper",
            borderRadius: 3,
            width: "100%",
            border: "1px solid rgba(255,255,255,0.07)",
          }}
        >
          <Avatar sx={{ m: 1, bgcolor: "primary.main", width: 48, height: 48 }}>
            <LockOutlinedIcon />
          </Avatar>
          <Typography
            component="h1"
            variant="h5"
            sx={{ mb: 0.5, fontFamily: "Poppins, sans-serif", fontWeight: 700 }}
          >
            RiskOptimizer
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            AI-Powered Portfolio Intelligence
          </Typography>

          <Tabs
            value={tab}
            onChange={handleTabChange}
            sx={{ mb: 2, width: "100%" }}
          >
            <Tab label="Sign In" sx={{ flex: 1 }} />
            <Tab label="Register" sx={{ flex: 1 }} />
          </Tabs>

          {displayError && (
            <Alert severity="error" sx={{ width: "100%", mb: 2 }}>
              {displayError}
            </Alert>
          )}

          {/* Sign In */}
          {tab === 0 && (
            <Box
              component="form"
              onSubmit={handleLoginSubmit}
              noValidate
              sx={{ width: "100%" }}
            >
              <TextField
                margin="normal"
                required
                fullWidth
                label="Wallet Address"
                autoComplete="off"
                autoFocus
                value={formData.wallet_address}
                onChange={handleChange("wallet_address")}
                disabled={loading}
                placeholder="0x..."
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 2, mb: 1, py: 1.4 }}
                disabled={loading}
              >
                {loading ? <CircularProgress size={22} /> : "Sign In"}
              </Button>
              <Divider sx={{ my: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                  or
                </Typography>
              </Divider>
              <Button
                fullWidth
                variant="outlined"
                onClick={handleDemoLogin}
                disabled={loading}
                sx={{ py: 1.2 }}
              >
                {loading ? (
                  <CircularProgress size={20} />
                ) : (
                  "Continue with Demo Account"
                )}
              </Button>
              <Typography
                variant="caption"
                color="text.secondary"
                align="center"
                display="block"
                sx={{ mt: 1.5 }}
              >
                Demo mode: enter any wallet address, or click above.
              </Typography>
            </Box>
          )}

          {/* Register */}
          {tab === 1 && (
            <Box
              component="form"
              onSubmit={handleRegisterSubmit}
              noValidate
              sx={{ width: "100%" }}
            >
              <TextField
                margin="normal"
                required
                fullWidth
                label="Username"
                value={formData.username}
                onChange={handleChange("username")}
                disabled={loading}
              />
              <TextField
                margin="normal"
                required
                fullWidth
                label="Email"
                type="email"
                value={formData.email}
                onChange={handleChange("email")}
                disabled={loading}
              />
              <TextField
                margin="normal"
                required
                fullWidth
                label="Password"
                type="password"
                value={formData.password}
                onChange={handleChange("password")}
                disabled={loading}
                helperText="Minimum 6 characters"
              />
              <TextField
                margin="normal"
                required
                fullWidth
                label="Wallet Address"
                value={formData.wallet_address}
                onChange={handleChange("wallet_address")}
                disabled={loading}
                placeholder="0x..."
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 2, mb: 1, py: 1.4 }}
                disabled={loading}
              >
                {loading ? <CircularProgress size={22} /> : "Create Account"}
              </Button>
            </Box>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default Login;
