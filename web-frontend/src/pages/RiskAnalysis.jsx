import CalculateIcon from "@mui/icons-material/Calculate";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import apiService from "../services/apiService";
import { mono } from "../theme";

const SAMPLE =
  "0.012, -0.008, 0.021, -0.015, 0.006, 0.018, -0.004, -0.022, 0.011, 0.009, " +
  "-0.003, 0.014, -0.017, 0.025, -0.006, 0.002, 0.019, -0.011, 0.007, -0.013";

function parseReturns(text) {
  return text
    .split(/[\s,]+/)
    .map((t) => t.trim())
    .filter(Boolean)
    .map(Number)
    .filter((n) => Number.isFinite(n));
}

// Pull the most relevant numeric value out of a backend risk envelope.
function pickMetric(envelope, keys) {
  const data = envelope?.data ?? envelope ?? {};
  for (const k of keys) {
    if (typeof data[k] === "number") return data[k];
  }
  const firstNum = Object.values(data).find((v) => typeof v === "number");
  return typeof firstNum === "number" ? firstNum : null;
}

const pct = (v) => (v == null ? "-" : `${(v * 100).toFixed(2)}%`);
const num = (v) => (v == null ? "-" : v.toFixed(3));

const RiskAnalysis = () => {
  const [raw, setRaw] = useState(SAMPLE);
  const [confidence, setConfidence] = useState(0.95);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState(null);

  const returns = parseReturns(raw);

  const run = async () => {
    setError("");
    if (returns.length < 5) {
      setError("Enter at least five return observations to compute metrics.");
      return;
    }
    setLoading(true);
    setResults(null);
    const payload = { returns, confidence_level: confidence };
    const outcomes = await Promise.allSettled([
      apiService.risk.calculateVaR(payload),
      apiService.risk.calculateCVaR(payload),
      apiService.risk.calculateSharpeRatio({ returns }),
      apiService.risk.calculateMaxDrawdown({ returns }),
    ]);

    const [var_, cvar, sharpe, mdd] = outcomes;
    const anyOk = outcomes.some((o) => o.status === "fulfilled");
    if (!anyOk) {
      setError(
        outcomes[0].reason?.message ||
          "Could not reach the risk service. Check that you are signed in and the API is running.",
      );
      setLoading(false);
      return;
    }
    setResults({
      var:
        var_.status === "fulfilled"
          ? pickMetric(var_.value, ["value_at_risk", "var"])
          : null,
      cvar:
        cvar.status === "fulfilled"
          ? pickMetric(cvar.value, [
              "conditional_var",
              "cvar",
              "expected_shortfall",
            ])
          : null,
      sharpe:
        sharpe.status === "fulfilled"
          ? pickMetric(sharpe.value, ["sharpe_ratio", "sharpe"])
          : null,
      mdd:
        mdd.status === "fulfilled"
          ? pickMetric(mdd.value, ["max_drawdown", "maximum_drawdown"])
          : null,
    });
    setLoading(false);
  };

  const metricCards = results
    ? [
        {
          label: "Value at Risk",
          value: pct(results.var),
          tone: "neg",
          hint: `${(confidence * 100).toFixed(0)}% confidence`,
        },
        {
          label: "Conditional VaR",
          value: pct(results.cvar),
          tone: "neg",
          hint: "Expected shortfall",
        },
        {
          label: "Sharpe ratio",
          value: num(results.sharpe),
          tone: "neutral",
          hint: "Risk-adjusted return",
        },
        {
          label: "Max drawdown",
          value: pct(results.mdd),
          tone: "neg",
          hint: "Peak to trough",
        },
      ]
    : [];

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 0.5 }}>
        Risk Analysis
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Compute value at risk, expected shortfall, Sharpe, and drawdown on a
        return series. Figures come straight from the risk service.
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Inputs
              </Typography>
              <TextField
                fullWidth
                multiline
                minRows={6}
                label="Return series"
                value={raw}
                onChange={(e) => setRaw(e.target.value)}
                helperText={`${returns.length} valid observations (comma, space, or newline separated)`}
                sx={{
                  mb: 2,
                  "& textarea": { fontFamily: mono, fontSize: "0.85rem" },
                }}
              />
              <TextField
                select
                fullWidth
                label="Confidence level"
                value={confidence}
                onChange={(e) => setConfidence(Number(e.target.value))}
                sx={{ mb: 2 }}
              >
                <MenuItem value={0.9}>90%</MenuItem>
                <MenuItem value={0.95}>95%</MenuItem>
                <MenuItem value={0.99}>99%</MenuItem>
              </TextField>
              <Stack direction="row" spacing={1.5}>
                <Button
                  variant="contained"
                  startIcon={loading ? null : <CalculateIcon />}
                  onClick={run}
                  disabled={loading}
                  fullWidth
                  sx={{ py: 1.2 }}
                >
                  {loading ? <CircularProgress size={22} /> : "Run analysis"}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => setRaw(SAMPLE)}
                  disabled={loading}
                >
                  Sample
                </Button>
              </Stack>
              {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {error}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={7}>
          <Card sx={{ minHeight: 320 }}>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                sx={{ mb: 2 }}
              >
                <Typography variant="h6">Results</Typography>
                {results && (
                  <Chip
                    size="small"
                    label={`n = ${returns.length}`}
                    sx={{ fontFamily: mono }}
                  />
                )}
              </Stack>

              {!results && !loading && (
                <Box sx={{ py: 6, textAlign: "center" }}>
                  <Typography color="text.secondary">
                    Run an analysis to see results here.
                  </Typography>
                </Box>
              )}

              {loading && (
                <Box sx={{ py: 8, textAlign: "center" }}>
                  <CircularProgress />
                </Box>
              )}

              {results && (
                <Grid container spacing={2}>
                  {metricCards.map((m) => (
                    <Grid item xs={6} key={m.label}>
                      <Box
                        sx={{
                          p: 2.5,
                          borderRadius: 2,
                          border: "1px solid",
                          borderColor: "divider",
                          bgcolor: "rgba(148,163,184,0.04)",
                        }}
                      >
                        <Typography variant="caption" color="text.secondary">
                          {m.label}
                        </Typography>
                        <Typography
                          sx={{
                            fontFamily: mono,
                            fontVariantNumeric: "tabular-nums",
                            fontSize: "1.7rem",
                            fontWeight: 600,
                            my: 0.5,
                            color:
                              m.tone === "neg"
                                ? "error.main"
                                : m.tone === "pos"
                                  ? "success.main"
                                  : "text.primary",
                          }}
                        >
                          {m.value}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {m.hint}
                        </Typography>
                      </Box>
                    </Grid>
                  ))}
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default RiskAnalysis;
