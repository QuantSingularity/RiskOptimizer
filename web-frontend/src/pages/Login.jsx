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

  useEffect(() => {
    if (user) {
      navigate("/", { replace: true });
    }
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
      setLocalError("Please enter your wallet address");
      return;
    }

    const success = await login({ wallet_address: formData.wallet_address });
    if (success) {
      navigate("/");
    }
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

    const success = await register({
      username: formData.username,
      email: formData.email,
      password: formData.password,
      wallet_address: formData.wallet_address,
    });
    if (success) {
      navigate("/");
    }
  };

  const displayError = localError || error;

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          minHeight: "100vh",
        }}
        className="fade-in"
      >
        <Paper
          elevation={3}
          sx={{
            padding: 4,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            backgroundColor: "background.paper",
            borderRadius: 2,
            width: "100%",
          }}
        >
          <Avatar sx={{ m: 1, bgcolor: "primary.main" }}>
            <LockOutlinedIcon />
          </Avatar>
          <Typography component="h1" variant="h5" sx={{ mb: 2 }}>
            RiskOptimizer
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
                sx={{ mt: 3, mb: 2, py: 1.5 }}
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} /> : "Sign In"}
              </Button>
              <Divider sx={{ my: 1 }} />
              <Typography
                variant="body2"
                color="text.secondary"
                align="center"
                sx={{ mt: 1 }}
              >
                For demo, use any wallet address.
              </Typography>
            </Box>
          )}

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
                sx={{ mt: 3, mb: 2, py: 1.5 }}
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} /> : "Create Account"}
              </Button>
            </Box>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default Login;
