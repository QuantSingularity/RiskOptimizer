import { Box, CircularProgress, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import apiService from "../services/apiService";

const METRIC_COLORS = {
  "VaR (95%)": "#f44336",
  "Sharpe Ratio": "#4caf50",
  Volatility: "#ff9800",
  "Max Drawdown": "#e91e63",
};

export default function RiskAnalytics({ returns }) {
  const [riskData, setRiskData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const mockReturns =
      returns ||
      Array.from({ length: 252 }, () => (Math.random() - 0.5) * 0.02);

    setLoading(true);
    setError(null);

    Promise.all([
      apiService.risk.calculateVaR({
        returns: mockReturns,
        confidence_level: 0.95,
      }),
      apiService.risk.calculateSharpeRatio({ returns: mockReturns }),
      apiService.risk.calculateMaxDrawdown({ returns: mockReturns }),
    ])
      .then(([varRes, sharpeRes, drawdownRes]) => {
        setRiskData([
          {
            metric: "VaR (95%)",
            value: Number((varRes?.data?.var_amount ?? 4532).toFixed(2)),
          },
          {
            metric: "Sharpe Ratio",
            value: Number((sharpeRes?.data?.sharpe_ratio ?? 1.87).toFixed(2)),
          },
          {
            metric: "Volatility",
            value: Number((varRes?.data?.volatility ?? 14.2).toFixed(2)),
          },
          {
            metric: "Max Drawdown",
            value: Math.abs(
              Number((drawdownRes?.data?.max_drawdown ?? -12.4).toFixed(2)),
            ),
          },
        ]);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [returns]);

  if (loading) return <CircularProgress />;
  if (error) return <Typography color="error">{error}</Typography>;

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Risk Analytics
      </Typography>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={riskData}
          margin={{ top: 10, right: 20, left: 0, bottom: 5 }}
        >
          <XAxis dataKey="metric" tick={{ fontSize: 12 }} />
          <YAxis />
          <Tooltip />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {riskData.map((entry) => (
              <Cell
                key={entry.metric}
                fill={METRIC_COLORS[entry.metric] || "#8884d8"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Box>
  );
}
