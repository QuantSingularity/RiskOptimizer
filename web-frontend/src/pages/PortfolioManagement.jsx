import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import RefreshIcon from "@mui/icons-material/Refresh";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { usePortfolio } from "../context/PortfolioContext";
import { formatCurrency, formatPercentage } from "../utils/formatters";

const emptyForm = { symbol: "", name: "", quantity: "", purchasePrice: "" };

const PortfolioManagement = () => {
  const {
    portfolio,
    loading,
    error,
    fetchPortfolio,
    savePortfolio,
    clearError,
  } = usePortfolio();

  const [localAssets, setLocalAssets] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [currentAsset, setCurrentAsset] = useState(null);
  const [formData, setFormData] = useState(emptyForm);
  const [formError, setFormError] = useState("");

  // Load portfolio on mount
  useEffect(() => {
    fetchPortfolio();
  }, [fetchPortfolio]);

  // Sync local assets whenever context portfolio changes
  useEffect(() => {
    if (portfolio?.assets) {
      setLocalAssets(portfolio.assets);
    }
  }, [portfolio]);

  // ── Derived totals ──────────────────────────────────────────────────────────
  const portfolioValue = localAssets.reduce(
    (s, a) => s + (a.totalValue || a.quantity * a.currentPrice || 0),
    0,
  );
  const totalGain = localAssets.reduce((s, a) => s + (a.gain || 0), 0);
  const totalCost = localAssets.reduce(
    (s, a) => s + (a.quantity * a.purchasePrice || 0),
    0,
  );
  const totalGainPct = totalCost > 0 ? (totalGain / totalCost) * 100 : 0;

  // ── Dialog helpers ──────────────────────────────────────────────────────────
  const handleOpenDialog = (asset = null) => {
    clearError();
    setFormError("");
    if (asset) {
      setCurrentAsset(asset);
      setFormData({
        symbol: asset.symbol || "",
        name: asset.name || "",
        quantity: String(asset.quantity ?? ""),
        purchasePrice: String(asset.purchasePrice ?? ""),
      });
    } else {
      setCurrentAsset(null);
      setFormData(emptyForm);
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setCurrentAsset(null);
    setFormData(emptyForm);
    setFormError("");
  };

  const handleInputChange = (field) => (e) => {
    setFormData((prev) => ({ ...prev, [field]: e.target.value }));
    setFormError("");
  };

  const handleSaveAsset = async () => {
    const { symbol, name, quantity, purchasePrice } = formData;
    if (!symbol || !name || !quantity || !purchasePrice) {
      setFormError("All fields are required.");
      return;
    }
    const qty = parseFloat(quantity);
    const price = parseFloat(purchasePrice);
    if (isNaN(qty) || qty <= 0) {
      setFormError("Quantity must be a positive number.");
      return;
    }
    if (isNaN(price) || price <= 0) {
      setFormError("Purchase price must be a positive number.");
      return;
    }

    // For demo: use a simple simulated current price (purchase price ± random %)
    const existingAsset = currentAsset;
    const currentPrice =
      existingAsset?.currentPrice ?? price * (1 + (Math.random() * 0.4 - 0.1));
    const totalValue = qty * currentPrice;
    const gain = (currentPrice - price) * qty;
    const gainPercent = price > 0 ? ((currentPrice - price) / price) * 100 : 0;

    const updatedAsset = {
      id: existingAsset?.id ?? Date.now(),
      symbol: symbol.toUpperCase(),
      name,
      quantity: qty,
      purchasePrice: price,
      currentPrice: parseFloat(currentPrice.toFixed(2)),
      totalValue: parseFloat(totalValue.toFixed(2)),
      gain: parseFloat(gain.toFixed(2)),
      gainPercent: parseFloat(gainPercent.toFixed(2)),
    };

    const updatedAssets = currentAsset
      ? localAssets.map((a) => (a.id === currentAsset.id ? updatedAsset : a))
      : [...localAssets, updatedAsset];

    setLocalAssets(updatedAssets);
    await savePortfolio({ assets: updatedAssets });
    handleCloseDialog();
  };

  const handleDeleteAsset = async (id) => {
    const updated = localAssets.filter((a) => a.id !== id);
    setLocalAssets(updated);
    await savePortfolio({ assets: updated });
  };

  const handleRefresh = () => fetchPortfolio();

  return (
    <Box className="fade-in">
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Typography variant="h4" component="h1">
          Portfolio Management
        </Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add Asset
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", my: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Total Portfolio Value
              </Typography>
              <Typography variant="h4" sx={{ my: 1, fontWeight: 600 }}>
                {formatCurrency(portfolioValue)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {localAssets.length} asset{localAssets.length !== 1 ? "s" : ""}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Total Gain / Loss
              </Typography>
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 0.5, my: 1 }}
              >
                {totalGain >= 0 ? (
                  <TrendingUpIcon color="success" />
                ) : (
                  <TrendingDownIcon color="error" />
                )}
                <Typography
                  variant="h4"
                  sx={{ fontWeight: 600 }}
                  color={totalGain >= 0 ? "success.main" : "error.main"}
                >
                  {formatCurrency(totalGain)}
                </Typography>
              </Box>
              <Typography
                variant="body2"
                color={totalGain >= 0 ? "success.main" : "error.main"}
              >
                {formatPercentage(totalGainPct, 2, true)} overall
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Total Cost Basis
              </Typography>
              <Typography variant="h4" sx={{ my: 1, fontWeight: 600 }}>
                {formatCurrency(totalCost)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Invested capital
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Assets Table */}
      <Card>
        <CardHeader title="Your Assets" />
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Asset</TableCell>
                <TableCell align="right">Quantity</TableCell>
                <TableCell align="right">Purchase Price</TableCell>
                <TableCell align="right">Current Price</TableCell>
                <TableCell align="right">Total Value</TableCell>
                <TableCell align="right">Gain / Loss</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {localAssets.length > 0 ? (
                localAssets.map((asset) => (
                  <TableRow key={asset.id} hover>
                    <TableCell>
                      <Box>
                        <Typography variant="body2" fontWeight={700}>
                          {asset.symbol}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {asset.name}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell align="right">{asset.quantity}</TableCell>
                    <TableCell align="right">
                      {formatCurrency(asset.purchasePrice)}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(asset.currentPrice)}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(asset.totalValue)}
                    </TableCell>
                    <TableCell align="right">
                      <Chip
                        label={`${formatPercentage(asset.gainPercent, 2, true)} (${formatCurrency(asset.gain)})`}
                        color={asset.gain >= 0 ? "success" : "error"}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Edit">
                        <IconButton
                          size="small"
                          onClick={() => handleOpenDialog(asset)}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteAsset(asset.id)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ py: 4 }}
                    >
                      No assets found. Click &quot;Add Asset&quot; to get
                      started.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Add / Edit Dialog */}
      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {currentAsset ? "Edit Asset" : "Add New Asset"}
        </DialogTitle>
        <DialogContent>
          {formError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {formError}
            </Alert>
          )}
          <TextField
            fullWidth
            label="Symbol (e.g. AAPL)"
            value={formData.symbol}
            onChange={handleInputChange("symbol")}
            margin="normal"
            required
            inputProps={{ style: { textTransform: "uppercase" } }}
          />
          <TextField
            fullWidth
            label="Asset Name"
            value={formData.name}
            onChange={handleInputChange("name")}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Quantity"
            type="number"
            value={formData.quantity}
            onChange={handleInputChange("quantity")}
            margin="normal"
            required
            inputProps={{ min: 0, step: "any" }}
          />
          <TextField
            fullWidth
            label="Purchase Price ($)"
            type="number"
            value={formData.purchasePrice}
            onChange={handleInputChange("purchasePrice")}
            margin="normal"
            required
            inputProps={{ min: 0, step: "any" }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSaveAsset}
            disabled={loading}
          >
            {loading ? (
              <CircularProgress size={20} />
            ) : currentAsset ? (
              "Save Changes"
            ) : (
              "Add Asset"
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PortfolioManagement;
