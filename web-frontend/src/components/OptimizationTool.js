import {
  Box,
  Button,
  CircularProgress,
  Slider,
  Typography,
} from "@mui/material";
import { useState } from "react";
import apiService from "../services/apiService";

export default function OptimizationTool() {
  const [riskTolerance, setRiskTolerance] = useState(5);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const optimize = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.optimization.optimize({
        risk_tolerance: riskTolerance / 10,
        method: "max_sharpe",
      });
      setResult(data?.data || data);
    } catch (err) {
      setError(err.message || "Optimization failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box p={3}>
      <Typography variant="h6" gutterBottom>
        Portfolio Optimization
      </Typography>
      <Typography variant="body2" gutterBottom>
        Risk Tolerance Level: {riskTolerance}
      </Typography>
      <Slider
        value={riskTolerance}
        onChange={(_e, v) => setRiskTolerance(v)}
        min={1}
        max={10}
        step={1}
        marks
        sx={{ mb: 3 }}
      />
      <Button
        variant="contained"
        color="primary"
        onClick={optimize}
        disabled={loading}
        startIcon={
          loading ? <CircularProgress size={16} color="inherit" /> : null
        }
      >
        {loading ? "Optimizing..." : "Optimize Portfolio"}
      </Button>

      {error && (
        <Typography color="error" sx={{ mt: 2 }}>
          {error}
        </Typography>
      )}

      {result && (
        <Box mt={3}>
          <Typography variant="h6">Optimized Allocation</Typography>
          <pre style={{ overflowX: "auto" }}>
            {JSON.stringify(result.optimized_allocation ?? result, null, 2)}
          </pre>
          {result.performance_metrics && (
            <>
              <Typography>
                Expected Return: {result.performance_metrics[0]}
              </Typography>
              <Typography>
                Volatility: {result.performance_metrics[1]}
              </Typography>
              <Typography>
                Sharpe Ratio: {result.performance_metrics[2]}
              </Typography>
            </>
          )}
        </Box>
      )}
    </Box>
  );
}
