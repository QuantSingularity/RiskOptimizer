import { useFocusEffect } from "@react-navigation/native";
import { Button, Icon, ListItem } from "@rneui/themed";
import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import apiService from "../../services/apiService";

const PortfolioListScreen = ({ navigation }) => {
  const [portfolios, setPortfolios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const fetchPortfolios = useCallback(async () => {
    setError("");
    try {
      const response = await apiService.getPortfolios();
      const payload = response.data?.data ?? response.data;
      setPortfolios(payload?.portfolios || []);
    } catch (err) {
      console.error("Failed to fetch portfolios:", err);
      setError("Could not load portfolios.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Fetch data when the screen comes into focus
  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fetchPortfolios();
    }, [fetchPortfolios]),
  );

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchPortfolios();
  }, [fetchPortfolios]);

  const renderItem = ({ item }) => (
    <ListItem
      testID={`portfolio-item-${item.id}`}
      bottomDivider
      onPress={() =>
        navigation.navigate("PortfolioDetail", {
          portfolioId: item.id,
          portfolioName: item.name,
        })
      }
      containerStyle={styles.listItem}
    >
      <Icon name="briefcase-outline" type="material-community" color="#555" />
      <ListItem.Content>
        <ListItem.Title style={styles.itemTitle}>{item.name}</ListItem.Title>
        <ListItem.Subtitle style={styles.itemSubtitle}>
          Value: {item.currency}{" "}
          {item.total_value?.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          }) || "0.00"}{" "}
          | Risk: {item.risk_score?.toFixed(2) || "N/A"}
        </ListItem.Subtitle>
      </ListItem.Content>
      <ListItem.Chevron />
    </ListItem>
  );

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator
          testID="loading-indicator"
          size="large"
          color="#007AFF"
        />
      </View>
    );
  }

  if (error && portfolios.length === 0) {
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
            fetchPortfolios();
          }}
        />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {error ? (
        <Text testID="error-message" style={styles.errorText}>
          {error}
        </Text>
      ) : null}
      <FlatList
        testID="portfolio-list"
        data={portfolios}
        renderItem={renderItem}
        keyExtractor={(item) => String(item.id)}
        ListEmptyComponent={
          <View style={styles.centered}>
            <Text>No portfolios found. Create one!</Text>
          </View>
        }
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      />
      <Button
        testID="create-portfolio-button"
        icon={<Icon name="plus" type="material-community" color="white" />}
        title="Create Portfolio"
        buttonStyle={styles.createButton}
        onPress={() => navigation.navigate("CreatePortfolio")}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  listItem: {
    backgroundColor: "white",
  },
  itemTitle: {
    fontWeight: "bold",
    fontSize: 16,
  },
  itemSubtitle: {
    color: "gray",
    fontSize: 14,
  },
  createButton: {
    backgroundColor: "#007AFF",
    margin: 15,
    borderRadius: 8,
  },
  errorText: {
    color: "red",
    textAlign: "center",
    marginBottom: 10,
    paddingHorizontal: 15,
  },
});

export default PortfolioListScreen;
