import {
  Box,
  Card,
  CardContent,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency } from "../../utils/formatters";

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <Box
      sx={{
        backgroundColor: "#132f4c",
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: 2,
        p: 1.5,
      }}
    >
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600, color: "#61dafb" }}>
        {formatCurrency(payload[0].value)}
      </Typography>
    </Box>
  );
};

const RANGES = [
  { label: "1W", days: 7 },
  { label: "1M", days: 30 },
  { label: "3M", days: 90 },
  { label: "1Y", days: 365 },
];

const PerformanceChart = ({ performanceData }) => {
  const [range, setRange] = useState("1M");

  const defaultData = (() => {
    const out = [];
    const now = new Date();
    let value = 100000;
    for (let i = 365; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      value = Math.max(80000, value + (Math.random() - 0.45) * 600);
      out.push({
        date: d.toISOString().split("T")[0],
        value: Math.round(value * 100) / 100,
      });
    }
    return out;
  })();

  const allData = performanceData || defaultData;
  const days = RANGES.find((r) => r.label === range)?.days ?? 30;
  const sliced = allData.slice(-days);

  const tickCount = Math.min(6, sliced.length);
  const step = Math.max(1, Math.floor(sliced.length / tickCount));
  const xTicks = sliced
    .filter((_, i) => i % step === 0 || i === sliced.length - 1)
    .map((d) => d.date);

  const startValue = sliced[0]?.value ?? 0;
  const endValue = sliced[sliced.length - 1]?.value ?? 0;
  const gain = endValue - startValue;
  const gainPct =
    startValue > 0 ? ((gain / startValue) * 100).toFixed(2) : "0.00";
  const isPositive = gain >= 0;

  return (
    <Card>
      <CardContent>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            mb: 2,
          }}
        >
          <Box>
            <Typography variant="h6">Portfolio Performance</Typography>
            <Typography
              variant="body2"
              color={isPositive ? "success.main" : "error.main"}
              sx={{ mt: 0.3 }}
            >
              {isPositive ? "+" : ""}
              {gainPct}% ({isPositive ? "+" : ""}
              {formatCurrency(gain)}) in {range}
            </Typography>
          </Box>
          <ToggleButtonGroup
            value={range}
            exclusive
            onChange={(_, v) => v && setRange(v)}
            size="small"
          >
            {RANGES.map((r) => (
              <ToggleButton
                key={r.label}
                value={r.label}
                sx={{
                  px: 1.5,
                  py: 0.3,
                  fontSize: "0.7rem",
                  color: "text.secondary",
                  borderColor: "rgba(255,255,255,0.12)",
                  "&.Mui-selected": {
                    color: "primary.main",
                    backgroundColor: "rgba(97,218,251,0.1)",
                  },
                }}
              >
                {r.label}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>

        <Box sx={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={sliced}
              margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
            >
              <defs>
                <linearGradient id="perfGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#61dafb" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#61dafb" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.06)"
              />
              <XAxis
                dataKey="date"
                ticks={xTicks}
                tick={{ fill: "#b2bac2", fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
              />
              <YAxis
                tick={{ fill: "#b2bac2", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                domain={["auto", "auto"]}
                width={50}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="value"
                stroke={isPositive ? "#61dafb" : "#f44336"}
                strokeWidth={2}
                fill="url(#perfGradient)"
                dot={false}
                activeDot={{ r: 5, fill: "#61dafb" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default PerformanceChart;
