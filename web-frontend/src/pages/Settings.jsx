import SaveIcon from "@mui/icons-material/Save";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Divider,
  FormControlLabel,
  Grid,
  Snackbar,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

const Settings = () => {
  const { user, logout } = useAuth();
  const [settings, setSettings] = useState({
    notifications: true,
    darkMode: true,
    autoRebalance: false,
    email: user?.email || "",
    riskTolerance: 50,
  });
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "success",
  });

  const handleChange = (field) => (event) => {
    const value =
      event.target.type === "checkbox"
        ? event.target.checked
        : event.target.value;
    setSettings((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    setSnackbar({
      open: true,
      message: "Settings saved successfully!",
      severity: "success",
    });
  };

  const handleCloseSnackbar = () => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  };

  return (
    <Box className="fade-in">
      <Typography variant="h4" component="h1" gutterBottom>
        Settings
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Account Settings" />
            <Divider />
            <CardContent>
              <TextField
                fullWidth
                label="Email"
                value={settings.email}
                onChange={handleChange("email")}
                margin="normal"
                type="email"
              />
              <TextField
                fullWidth
                label="Wallet Address"
                value={user?.wallet_address || user?.address || ""}
                margin="normal"
                disabled
                helperText="Your connected wallet address"
              />
              <Box sx={{ mt: 3 }}>
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={handleSave}
                  sx={{ mr: 2 }}
                >
                  Save Changes
                </Button>
                <Button variant="outlined" color="error" onClick={logout}>
                  Logout
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Preferences" />
            <Divider />
            <CardContent>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.notifications}
                    onChange={handleChange("notifications")}
                  />
                }
                label="Enable Notifications"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.darkMode}
                    onChange={handleChange("darkMode")}
                  />
                }
                label="Dark Mode"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.autoRebalance}
                    onChange={handleChange("autoRebalance")}
                  />
                }
                label="Auto-Rebalance Portfolio"
              />
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Default Risk Tolerance
                </Typography>
                <TextField
                  type="number"
                  value={settings.riskTolerance}
                  onChange={handleChange("riskTolerance")}
                  inputProps={{ min: 0, max: 100 }}
                  helperText="0 = Conservative, 100 = Aggressive"
                  fullWidth
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardHeader title="Security" />
            <Divider />
            <CardContent>
              <Alert severity="info" sx={{ mb: 2 }}>
                Your wallet connection is secured through blockchain
                authentication.
              </Alert>
              <Typography variant="body2" color="text.secondary">
                Connected Wallet:{" "}
                {user?.wallet_address || user?.address || "Not connected"}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Settings;
