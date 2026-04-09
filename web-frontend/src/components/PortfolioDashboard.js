import { Box, CircularProgress, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { Cell, Pie, PieChart, Tooltip } from "recharts";
import { useAuth } from "../context/AuthContext";
import apiService from "../services/apiService";

const COLORS = [
  "#0088FE",
  "#00C49F",
  "#FFBB28",
  "#FF8042",
  "#AA00FF",
  "#FF5722",
];

export default function PortfolioDashboard() {
  const { user } = useAuth();
  const [portfolio, setPortfolio] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const address = user?.wallet_address || user?.address;
    if (!address) return;

    setLoading(true);
    setError(null);
    apiService.portfolio
      .getByAddress(address)
      .then((response) => {
        if (response?.status === "success" && response.data) {
          const assets = response.data.assets || [];
          const formatted = assets.map((asset) => ({
            name: asset.symbol || asset.name,
            value: asset.totalValue || asset.quantity * asset.currentPrice || 0,
          }));
          setPortfolio(formatted);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [user]);

  if (loading) return <CircularProgress />;
  if (error) return <Typography color="error">{error}</Typography>;
  if (!portfolio.length)
    return <Typography color="text.secondary">No portfolio data</Typography>;

  return (
    <Box sx={{ display: "flex", justifyContent: "center" }}>
      <PieChart width={400} height={400}>
        <Pie
          data={portfolio}
          cx={200}
          cy={200}
          innerRadius={60}
          outerRadius={80}
          paddingAngle={5}
          dataKey="value"
          label={({ name, value }) => `${name}: $${value.toFixed(0)}`}
        >
          {portfolio.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v) => `$${Number(v).toFixed(2)}`} />
      </PieChart>
    </Box>
  );
}
