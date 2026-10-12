import { useFocusEffect } from "@react-navigation/native";
import { Button, Card, Divider, Icon, ListItem, useTheme } from "@rneui/themed"; // Import useTheme
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Dimensions,
  FlatList,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { PieChart } from "react-native-chart-kit"; // Import PieChart
import apiService from "../../services/apiService";

const screenWidth = Dimensions.get("window").width;

// Function to generate random colors for pie chart slices
const getRandomColor = () => {
  const letters = "0123456789ABCDEF";
  let color = "#";
  for (let i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
};

const PortfolioDetailScreen = ({ route, navigation }) => {
  const { portfolioId, portfolioName } = route.params;
  const [portfolioDetails, setPortfolioDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const { theme } = useTheme(); // Access theme

  // Update header title
  useEffect(() => {
    navigation.setOptions({
      title: portfolioDetails?.name || portfolioName || "Portfolio Details",
    });
  }, [portfolioDetails?.name, portfolioName, navigation]);

  const fetchPortfolioDetails = useCallback(async () => {
    setError("");
    try {
      const response = await apiService.getPortfolioDetails(portfolioId);
      const payload = response.data?.data ?? response.data;
      if (!payload) {
        throw new Error("Empty portfolio response");
      }
      setPortfolioDetails(payload);
    } catch (err) {
      console.error("Failed to fetch portfolio details:", err);
      setError("Could not load portfolio details.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [portfolioId, portfolioName]);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fetchPortfolioDetails();
    }, [fetchPortfolioDetails]),
  );

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchPortfolioDetails();
  }, [fetchPortfolioDetails]);

  // Prepare data for Pie Chart
  const pieChartData = useMemo(() => {
    if (!portfolioDetails?.assets || portfolioDetails.assets.length === 0) {
      return [];
    }
    return portfolioDetails.assets
      .map((asset) => ({
        name: asset.symbol,
        population: asset.allocation_percentage || 0,
        color: getRandomColor(), // Assign a random color
        legendFontColor: theme.colors.grey0,
        legendFontSize: 13,
      }))
      .filter((item) => item.population > 0); // Filter out zero allocations
  }, [portfolioDetails?.assets, theme.colors.grey0]);

  // Define styles using theme
  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          flex: 1,
          backgroundColor: theme.colors.background,
        },
        centered: {
          flex: 1,
          justifyContent: "center",
          alignItems: "center",
          padding: 20,
          backgroundColor: theme.colors.background,
        },
        summaryCard: {
          // Theme handles card styling
          alignItems: "center",
          marginBottom: 10,
        },
        summaryLabel: {
          fontSize: 16,
          color: theme.colors.grey0,
          marginBottom: 5,
        },
        summaryValue: {
          fontSize: 30, // Larger value
          fontWeight: "bold",
          color: theme.colors.black,
        },
        summaryRisk: {
          fontSize: 16,
          color: theme.colors.grey0,
          marginTop: 8,
        },
        description: {
          fontSize: 14,
          color: theme.colors.grey1,
          marginTop: 10,
          textAlign: "center",
        },
        allocationCard: {
          // Theme handles card styling
          marginBottom: 10,
          alignItems: "center",
        },
        assetsCard: {
          // Theme handles card styling
          marginBottom: 15,
        },
        assetItem: {
          paddingVertical: 12,
          backgroundColor: theme.colors.white,
        },
        assetSymbol: {
          fontWeight: "bold",
          fontSize: 16,
          color: theme.colors.black,
        },
        assetName: {
          fontWeight: "normal",
          color: theme.colors.grey0,
          fontSize: 14,
        },
        assetDetails: {
          color: theme.colors.grey1,
          fontSize: 14,
          marginTop: 3,
        },
        addAssetButton: {
          backgroundColor: theme.colors.success,
          marginTop: 15,
          // Theme handles borderRadius, padding
        },
        noAssetsText: {
          textAlign: "center",
          paddingVertical: 20,
          color: theme.colors.grey0,
        },
        sectionLink: {
          flexDirection: "row",
          alignItems: "center",
          backgroundColor: theme.colors.white,
          paddingVertical: 15,
          paddingHorizontal: 15,
        },
        sectionLinkText: {
          flex: 1,
          marginLeft: 15,
          fontSize: 17,
          color: theme.colors.black,
        },
        divider: {
          // Theme handles divider color
        },
        errorText: {
          color: theme.colors.error,
          textAlign: "center",
          marginBottom: 10,
        },
        chartContainer: {
          alignItems: "center", // Center the chart
          marginTop: 10,
        },
        infoText: {
          textAlign: "center",
          color: theme.colors.grey0,
          paddingVertical: 20,
        },
      }),
    [theme],
  );

  const chartConfig = useMemo(
    () => ({
      color: (opacity = 1) => `rgba(0, 0, 0, ${opacity})`, // Default color, overridden by slice color
      labelColor: (_opacity = 1) => theme.colors.grey0,
    }),
    [theme],
  );

  const renderAssetItem = ({ item }) => (
    <ListItem
      testID={`asset-item-${item.symbol}`}
      bottomDivider
      onPress={() =>
        navigation.navigate("AssetDetailPortfolio", { symbol: item.symbol })
      }
      containerStyle={styles.assetItem}
    >
      <ListItem.Content>
        <ListItem.Title style={styles.assetSymbol}>
          {item.symbol} <Text style={styles.assetName}>({item.name})</Text>
        </ListItem.Title>
        <ListItem.Subtitle style={styles.assetDetails}>
          Qty: {item.quantity ?? "N/A"} | Value: {portfolioDetails?.currency}{" "}
          {item.value?.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </ListItem.Subtitle>
        <ListItem.Subtitle style={styles.assetDetails}>
          Allocation: {item.allocation_percentage?.toFixed(2)}% | Perf:{" "}
          {item.performance == null ? "N/A" : `${item.performance.toFixed(2)}%`}
        </ListItem.Subtitle>
      </ListItem.Content>
      <ListItem.Chevron color={theme.colors.grey2} />
    </ListItem>
  );

  if (loading && !refreshing) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator
          testID="loading-indicator"
          size="large"
          color={theme.colors.primary}
        />
      </View>
    );
  }

  if (error && !portfolioDetails) {
    return (
      <View style={styles.centered}>
        <Text testID="error-message" style={styles.errorText}>
          {error}
        </Text>
        <Button
          testID="retry-button"
          title="Retry"
          onPress={() => {
            setLoading(true);
            fetchPortfolioDetails();
          }}
        />
      </View>
    );
  }

  if (!portfolioDetails) {
    return (
      <View style={styles.centered}>
        <Text style={styles.infoText}>No portfolio data found.</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={theme.colors.primary}
        />
      }
    >
      {error && (
        <Text
          testID="error-message"
          style={[styles.errorText, { padding: 15 }]}
        >
          {error}
        </Text>
      )}
      <Card containerStyle={styles.summaryCard}>
        <Text style={styles.summaryLabel}>Total Value</Text>
        <Text style={styles.summaryValue}>
          {portfolioDetails.currency}{" "}
          {portfolioDetails.total_value?.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </Text>
        <Text style={styles.summaryRisk}>
          Risk Score: {portfolioDetails.risk_score?.toFixed(2) || "N/A"}
        </Text>
        {portfolioDetails.description ? (
          <Text style={styles.description}>{portfolioDetails.description}</Text>
        ) : null}
      </Card>

      {/* Allocation Chart Section */}
      {pieChartData.length > 0 && (
        <Card containerStyle={styles.allocationCard}>
          <Card.Title>Asset Allocation</Card.Title>
          <Card.Divider />
          <View style={styles.chartContainer}>
            <PieChart
              data={pieChartData}
              width={screenWidth * 0.85} // Adjust width as needed
              height={220}
              chartConfig={chartConfig}
              accessor={"population"} // Accessor for the value
              backgroundColor={"transparent"}
              paddingLeft={"15"}
              // center={[10, 0]} // Adjust center if needed
              absolute // Show absolute values (percentages in this case)
              // hasLegend={false} // Hide default legend if using custom or if labels are clear
            />
          </View>
        </Card>
      )}

      {/* Links Section */}
      <View style={{ backgroundColor: theme.colors.white, marginVertical: 10 }}>
        <TouchableOpacity
          onPress={() => alert("Navigate to Performance Chart")}
          style={styles.sectionLink}
        >
          <Icon
            name="chart-timeline-variant"
            type="material-community"
            color={theme.colors.primary}
          />
          <Text style={styles.sectionLinkText}>View Performance Details</Text>
          <Icon
            name="chevron-right"
            type="material-community"
            color={theme.colors.grey2}
          />
        </TouchableOpacity>
        <Divider style={styles.divider} />
        <TouchableOpacity
          onPress={() =>
            navigation.navigate("RiskAnalysis", { portfolioId: portfolioId })
          }
          style={styles.sectionLink}
        >
          <Icon
            name="shield-half-full"
            type="material-community"
            color={theme.colors.primary}
          />
          <Text style={styles.sectionLinkText}>View Risk Analysis</Text>
          <Icon
            name="chevron-right"
            type="material-community"
            color={theme.colors.grey2}
          />
        </TouchableOpacity>
        <Divider style={styles.divider} />
        <TouchableOpacity
          onPress={() =>
            navigation.navigate("TransactionHistory", {
              portfolioId: portfolioId,
            })
          }
          style={styles.sectionLink}
        >
          <Icon
            name="receipt"
            type="material-community"
            color={theme.colors.primary}
          />
          <Text style={styles.sectionLinkText}>View Transaction History</Text>
          <Icon
            name="chevron-right"
            type="material-community"
            color={theme.colors.grey2}
          />
        </TouchableOpacity>
      </View>

      {/* Assets List Section */}
      <Card containerStyle={styles.assetsCard}>
        <Card.Title>Assets</Card.Title>
        <Card.Divider />
        {portfolioDetails.assets && portfolioDetails.assets.length > 0 ? (
          <FlatList
            data={portfolioDetails.assets}
            renderItem={renderAssetItem}
            keyExtractor={(item) => item.id}
            scrollEnabled={false} // Disable scrolling within the card
          />
        ) : (
          <Text style={styles.noAssetsText}>
            No assets in this portfolio yet.
          </Text>
        )}
        <Button
          testID="add-asset-button"
          icon={
            <Icon
              name="plus"
              type="material-community"
              color={theme.colors.white}
            />
          }
          title="Add Asset"
          buttonStyle={styles.addAssetButton}
          onPress={() =>
            navigation.navigate("AddAsset", { portfolioId: portfolioId })
          }
        />
      </Card>
    </ScrollView>
  );
};

export default PortfolioDetailScreen;
