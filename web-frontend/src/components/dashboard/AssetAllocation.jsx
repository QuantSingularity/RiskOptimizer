import { Box, Card, CardContent, Grid, Typography } from "@mui/material";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const defaultAllocation = [
  { name: "Stocks", value: 60, color: "#2196f3" },
  { name: "Bonds", value: 20, color: "#4caf50" },
  { name: "Crypto", value: 10, color: "#ff9800" },
  { name: "Cash", value: 5, color: "#9e9e9e" },
  { name: "Gold", value: 5, color: "#ffc107" },
];

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null;
  const { name, value, color } = payload[0].payload;
  return (
    <Box
      sx={{
        backgroundColor: "#132f4c",
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: 2,
        p: 1.2,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Box
          sx={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            backgroundColor: color,
          }}
        />
        <Typography variant="caption" sx={{ fontWeight: 600 }}>
          {name}
        </Typography>
      </Box>
      <Typography variant="body2" color="primary.main" sx={{ fontWeight: 700 }}>
        {value}%
      </Typography>
    </Box>
  );
};

const AssetAllocation = ({ allocation }) => {
  const data = allocation || defaultAllocation;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Asset Allocation
        </Typography>

        <Box sx={{ height: 220, position: "relative" }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={3}
                dataKey="value"
                stroke="none"
              >
                {data.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </Box>

        <Grid container spacing={1} sx={{ mt: 1 }}>
          {data.map((item, index) => (
            <Grid item xs={6} key={index}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 0.5 }}>
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    backgroundColor: item.color,
                    mr: 1,
                    flexShrink: 0,
                  }}
                />
                <Typography variant="body2" noWrap>
                  {item.name}: <strong>{item.value}%</strong>
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default AssetAllocation;
