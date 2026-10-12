import { Button, Card, Slider } from "@rneui/themed";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Dimensions,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { LineChart } from "react-native-chart-kit";
import apiService from "../../services/apiService";
import {
  METHODS,
  MIN_ASSETS,
  buildOptimizationRequest,
  buildResults,
  extractErrorMessage,
} from "../../utils/optimization";

const CHART_WIDTH = Dimensions.get("window").width - 48;

const Chip = ({ label, selected, onPress, testID }) => (
  <TouchableOpacity
    testID={testID}
    accessibilityRole="button"
    accessibilityState={{ selected }}
    onPress={onPress}
    style={[styles.chip, selected && styles.chipSelected]}
  >
    <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
      {label}
    </Text>
  </TouchableOpacity>
);

const FrontierChart = ({ points, optimalIdx }) => {
  if (!points || points.length < 2) {
    return <Text style={styles.muted}>Efficient frontier unavailable.</Text>;
  }
  return (
    <View>
      <LineChart
        data={{
          labels: points.map((point, index) =>
            index % Math.ceil(points.length / 5) === 0 ? `${point.risk}` : "",
          ),
          datasets: [{ data: points.map((point) => point.return) }],
        }}
        width={CHART_WIDTH}
        height={200}
        yAxisSuffix="%"
        chartConfig={{
          backgroundGradientFrom: "#ffffff",
          backgroundGradientTo: "#ffffff",
          decimalPlaces: 1,
          color: (opacity = 1) => `rgba(0, 122, 255, ${opacity})`,
          labelColor: (opacity = 1) => `rgba(60, 60, 67, ${opacity})`,
        }}
        bezier
        style={styles.chart}
      />
      <Text style={styles.muted}>
        Horizontal axis: volatility %. Nearest frontier point to your portfolio:
        risk {points[optimalIdx].risk}%, return {points[optimalIdx].return}%.
      </Text>
    </View>
  );
};

const AllocationRow = ({ name, baseline, optimized }) => {
  const diff = optimized - baseline;
  return (
    <View style={styles.allocationRow}>
      <View style={styles.allocationHeader}>
        <Text style={styles.allocationName}>{name}</Text>
        <Text
          style={[
            styles.allocationValue,
            diff > 0.05 && styles.positive,
            diff < -0.05 && styles.negative,
          ]}
        >
          {baseline}% to {optimized}%
        </Text>
      </View>
      <View style={styles.barTrack}>
        <View
          style={[
            styles.bar,
            { width: `${Math.min(100, Math.max(0, optimized))}%` },
          ]}
        />
      </View>
    </View>
  );
};

const OptimizationScreen = () => {
  const [availableSymbols, setAvailableSymbols] = useState([]);
  const [selectedSymbols, setSelectedSymbols] = useState([]);
  const [loadingSymbols, setLoadingSymbols] = useState(true);
  const [tolerance, setTolerance] = useState(5);
  const [method, setMethod] = useState("utility");
  const [maxAllocation, setMaxAllocation] = useState(1);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiService
      .getOptimizationSymbols()
      .then((response) => {
        if (!active) return;
        const symbols = response.data?.data?.symbols || [];
        setAvailableSymbols(symbols);
        setSelectedSymbols(symbols);
      })
      .catch((err) => {
        if (active) setError(extractErrorMessage(err));
      })
      .finally(() => {
        if (active) setLoadingSymbols(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const toggleSymbol = (symbol) => {
    setSelectedSymbols((current) =>
      availableSymbols.filter((item) =>
        item === symbol ? !current.includes(item) : current.includes(item),
      ),
    );
  };

  const canRun = selectedSymbols.length >= MIN_ASSETS && !running;

  const handleRunOptimization = async () => {
    setRunning(true);
    setError("");
    const request = buildOptimizationRequest({
      symbols: selectedSymbols,
      tolerance,
      method,
      maxWeight: maxAllocation,
    });
    try {
      const [optimization, frontier] = await Promise.all([
        apiService.optimizePortfolio(request),
        apiService.getEfficientFrontier({
          symbols: request.symbols,
          risk_tolerance: request.risk_tolerance,
          min_weight: request.min_weight,
          max_weight: request.max_weight,
          points: 20,
        }),
      ]);
      setResult(
        buildResults({
          optimization: optimization.data.data,
          frontier: frontier.data.data?.frontier,
          symbols: selectedSymbols,
        }),
      );
    } catch (err) {
      setResult(null);
      setError(extractErrorMessage(err));
    } finally {
      setRunning(false);
    }
  };

  return (
    <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
      <Card>
        <Card.Title>Portfolio Optimization</Card.Title>
        <Card.Divider />

        <Text style={styles.label}>
          Assets ({selectedSymbols.length} selected)
        </Text>
        {loadingSymbols ? (
          <ActivityIndicator testID="symbols-loading" />
        ) : (
          <View style={styles.chipRow}>
            {availableSymbols.map((symbol) => (
              <Chip
                key={symbol}
                testID={`asset-${symbol}`}
                label={symbol.replace("_", "-")}
                selected={selectedSymbols.includes(symbol)}
                onPress={() => toggleSymbol(symbol)}
              />
            ))}
          </View>
        )}
        {!loadingSymbols && selectedSymbols.length < MIN_ASSETS && (
          <Text style={styles.errorText}>
            Select at least {MIN_ASSETS} assets
          </Text>
        )}

        <Text style={styles.label}>Method</Text>
        <View style={styles.chipRow}>
          {METHODS.map((item) => (
            <Chip
              key={item.value}
              testID={`method-${item.value}`}
              label={item.label}
              selected={method === item.value}
              onPress={() => setMethod(item.value)}
            />
          ))}
        </View>

        <Text style={styles.label}>
          Risk tolerance: {tolerance} of 10
          {method !== "utility" ? " (used by Risk Utility only)" : ""}
        </Text>
        <Slider
          value={tolerance}
          onValueChange={setTolerance}
          minimumValue={1}
          maximumValue={10}
          step={1}
          disabled={method !== "utility"}
          thumbStyle={styles.thumb}
        />

        <Text style={styles.label}>
          Max allocation per asset: {Math.round(maxAllocation * 100)}%
        </Text>
        <Slider
          value={maxAllocation}
          onValueChange={setMaxAllocation}
          minimumValue={0.1}
          maximumValue={1}
          step={0.05}
          thumbStyle={styles.thumb}
        />

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <Button
          title={running ? "Optimizing..." : "Run Optimization"}
          onPress={handleRunOptimization}
          disabled={!canRun}
          loading={running}
          containerStyle={styles.runButton}
        />
      </Card>

      {result && (
        <Card>
          <Card.Title>Results</Card.Title>
          <Card.Divider />
          <Text style={styles.muted}>
            {METHODS.find((m) => m.value === result.summary.method)?.label} |{" "}
            {result.summary.modelType === "ml"
              ? "ML return model"
              : "Historical mean model"}
          </Text>
          <View style={styles.metricRow}>
            <View style={styles.metric}>
              <Text style={styles.metricLabel}>Return</Text>
              <Text style={[styles.metricValue, styles.positive]}>
                {result.summary.expectedReturn}%
              </Text>
            </View>
            <View style={styles.metric}>
              <Text style={styles.metricLabel}>Risk</Text>
              <Text style={styles.metricValue}>
                {result.summary.expectedRisk}%
              </Text>
            </View>
            <View style={styles.metric}>
              <Text style={styles.metricLabel}>Sharpe</Text>
              <Text style={styles.metricValue}>
                {result.summary.sharpeRatio}
              </Text>
            </View>
          </View>

          <Text style={styles.label}>
            Allocation (equal weight to optimized)
          </Text>
          {result.allocations.map((allocation) => (
            <AllocationRow key={allocation.symbol} {...allocation} />
          ))}

          <Text style={styles.label}>Efficient frontier</Text>
          <FrontierChart
            points={result.frontier}
            optimalIdx={result.optimalIdx}
          />
        </Card>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f2f2f7" },
  label: { fontSize: 15, fontWeight: "600", marginTop: 14, marginBottom: 6 },
  muted: { fontSize: 12, color: "#6c6c70", marginTop: 4 },
  chipRow: { flexDirection: "row", flexWrap: "wrap" },
  chip: {
    borderWidth: 1,
    borderColor: "#c7c7cc",
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 8,
    marginBottom: 8,
  },
  chipSelected: { backgroundColor: "#007aff", borderColor: "#007aff" },
  chipText: { color: "#3c3c43", fontSize: 13 },
  chipTextSelected: { color: "#ffffff" },
  thumb: { height: 20, width: 20 },
  runButton: { marginTop: 18 },
  errorText: { color: "#ff3b30", marginTop: 8 },
  metricRow: { flexDirection: "row", marginVertical: 12 },
  metric: { flex: 1, alignItems: "center" },
  metricLabel: { fontSize: 12, color: "#6c6c70" },
  metricValue: { fontSize: 20, fontWeight: "700" },
  positive: { color: "#34c759" },
  negative: { color: "#ff3b30" },
  allocationRow: { marginBottom: 10 },
  allocationHeader: { flexDirection: "row", justifyContent: "space-between" },
  allocationName: { fontSize: 14 },
  allocationValue: { fontSize: 14, fontWeight: "600" },
  barTrack: {
    height: 6,
    borderRadius: 3,
    backgroundColor: "#e5e5ea",
    marginTop: 4,
  },
  bar: { height: 6, borderRadius: 3, backgroundColor: "#007aff" },
  chart: { marginVertical: 8, borderRadius: 8 },
});

export default OptimizationScreen;
