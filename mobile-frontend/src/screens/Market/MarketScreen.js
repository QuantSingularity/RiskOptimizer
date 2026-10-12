import { useFocusEffect } from "@react-navigation/native";
import {
  Button,
  ButtonGroup,
  ListItem,
  SearchBar,
  useTheme,
} from "@rneui/themed"; // Import ButtonGroup
import _ from "lodash";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import apiService from "../../services/apiService";
import { getWatchlist } from "../../utils/watchlist"; // Import watchlist utility

const MarketScreen = ({ navigation }) => {
  const [marketData, setMarketData] = useState([]); // Holds the initial/default list
  const [searchResults, setSearchResults] = useState([]); // Holds search results
  const [watchlistData, setWatchlistData] = useState([]); // Holds watchlist asset data
  const [_watchlistSymbols, setWatchlistSymbols] = useState([]); // Holds watchlist symbols
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [selectedViewIndex, setSelectedViewIndex] = useState(0); // 0: All, 1: Watchlist

  const { theme } = useTheme();

  // Fetch asset price details (used by initial load and watchlist)
  const fetchAssetDetails = useCallback(async (symbol) => {
    try {
      const priceHistory = await apiService.getAssetPriceHistory(
        symbol,
        "1d",
        "1d",
      );
      const meta = priceHistory.data?.meta;
      const closes = priceHistory.data?.indicators?.quote?.[0]?.close || [];
      const latestPrice =
        meta?.regularMarketPrice || closes[closes.length - 1] || 0;
      const previousClose =
        meta?.chartPreviousClose ||
        (closes.length > 1 ? closes[closes.length - 2] : latestPrice);
      const change =
        previousClose !== 0
          ? ((latestPrice - previousClose) / previousClose) * 100
          : 0;
      return {
        symbol: meta?.symbol || symbol,
        name: meta?.shortName || meta?.longName || symbol,
        price: latestPrice,
        change: change,
        currency: meta?.currency || "USD",
      };
    } catch (err) {
      console.warn(`Failed to fetch market data for ${symbol}:`, err.message);
      return null;
    }
  }, []);

  // Fetch initial market data (predefined list)
  const fetchInitialMarketData = useCallback(async () => {
    setError("");
    try {
      const symbols = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "NVDA",
        "META",
        "BTC-USD",
        "ETH-USD",
      ];
      const promises = symbols.map(fetchAssetDetails);
      const results = (await Promise.all(promises)).filter(
        (data) => data !== null,
      );
      if (results.length === 0) {
        throw new Error("No market data could be retrieved");
      }
      setMarketData(results);
    } catch (err) {
      console.error("Failed to fetch initial market data:", err);
      setError("Could not load initial market data.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [fetchAssetDetails]);

  // Fetch data for watchlist symbols
  const fetchWatchlistData = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const symbols = await getWatchlist();
      setWatchlistSymbols(symbols);
      if (symbols.length > 0) {
        const promises = symbols.map(fetchAssetDetails);
        const results = (await Promise.all(promises)).filter(
          (data) => data !== null,
        );
        if (results.length === 0) {
          throw new Error("No watchlist data could be retrieved");
        }
        setWatchlistData(results);
      } else {
        setWatchlistData([]); // Clear data if watchlist is empty
      }
    } catch (err) {
      console.error("Failed to fetch watchlist data:", err);
      setError("Could not load watchlist data.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [fetchAssetDetails]);

  // Debounced search function
  const performSearch = useCallback(
    _.debounce(async (query) => {
      if (query.trim() === "") {
        setSearchResults([]);
        setIsSearching(false);
        return;
      }
      setIsSearching(true);
      setError("");
      try {
        const response = await apiService.searchAssets(query);
        const searchResultsWithPrice = await Promise.all(
          (response.data.assets || []).map((asset) =>
            fetchAssetDetails(asset.symbol),
          ),
        );
        setSearchResults(
          searchResultsWithPrice.filter((data) => data !== null),
        );
      } catch (err) {
        console.error("Failed to search assets:", err);
        setError("Could not perform search.");
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300),
    [],
  );

  useEffect(() => {
    if (selectedViewIndex === 0) {
      // Only search when in 'All' view
      performSearch(searchQuery);
    }
  }, [searchQuery, performSearch, selectedViewIndex]);

  // Fetch data based on focused view (All or Watchlist)
  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      if (selectedViewIndex === 0) {
        fetchInitialMarketData();
      } else {
        fetchWatchlistData();
      }
    }, [selectedViewIndex, fetchInitialMarketData, fetchWatchlistData]),
  );

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    // Reset search only if in 'All' view
    if (selectedViewIndex === 0) {
      setSearchQuery("");
      setSearchResults([]);
      fetchInitialMarketData();
    } else {
      fetchWatchlistData();
    }
  }, [selectedViewIndex, fetchInitialMarketData, fetchWatchlistData]);

  // Determine which data list to display
  const dataToDisplay =
    selectedViewIndex === 0
      ? searchQuery.trim() !== ""
        ? searchResults
        : marketData
      : watchlistData;

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
        listItem: {
          backgroundColor: theme.colors.white,
        },
        itemSymbol: {
          fontWeight: "bold",
          fontSize: 16,
          color: theme.colors.black,
        },
        itemName: {
          fontWeight: "normal",
          color: theme.colors.grey0,
          fontSize: 14,
        },
        itemPrice: {
          color: theme.colors.grey1, // Darker grey for price
          fontSize: 14,
          marginTop: 3,
        },
        changeContainer: {
          paddingHorizontal: 8,
          paddingVertical: 4,
          borderRadius: 5,
          minWidth: 70,
          alignItems: "flex-end",
        },
        itemChange: {
          fontSize: 14,
          fontWeight: "bold",
        },
        positiveChange: {
          color: theme.colors.success,
        },
        negativeChange: {
          color: theme.colors.error,
        },
        errorText: {
          color: theme.colors.error,
          textAlign: "center",
          marginBottom: 10,
        },
        infoText: {
          color: theme.colors.grey0,
          textAlign: "center",
        },
        searchBarContainer: {
          backgroundColor: theme.colors.background,
          borderTopWidth: 0,
          borderBottomWidth: 0,
          paddingHorizontal: 5,
        },
        searchBarInputContainer: {
          backgroundColor: theme.colors.searchBg,
          borderRadius: 10,
        },
        searchBarInput: {
          fontSize: 16,
        },
        buttonGroupContainer: {
          marginHorizontal: 10,
          marginBottom: 5,
          marginTop: 10,
          borderRadius: 8,
          height: 35, // Smaller height for view toggle
        },
        buttonGroupSelected: {
          backgroundColor: theme.colors.primary,
        },
        buttonGroupText: {
          fontSize: 13,
        },
      }),
    [theme],
  );

  const renderItem = ({ item }) => (
    <ListItem
      testID={`market-item-${item.symbol}`}
      bottomDivider
      onPress={() =>
        navigation.navigate("AssetDetailMarket", { symbol: item.symbol })
      }
      containerStyle={styles.listItem}
    >
      <ListItem.Content>
        <ListItem.Title style={styles.itemSymbol}>
          {item.symbol} <Text style={styles.itemName}>({item.name})</Text>
        </ListItem.Title>
        <ListItem.Subtitle style={styles.itemPrice}>
          {item.currency}{" "}
          {item.price?.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </ListItem.Subtitle>
      </ListItem.Content>
      <View style={styles.changeContainer}>
        <Text
          style={[
            styles.itemChange,
            item.change >= 0 ? styles.positiveChange : styles.negativeChange,
          ]}
        >
          {item.change >= 0 ? "+" : ""}
          {item.change?.toFixed(2)}%
        </Text>
      </View>
      <ListItem.Chevron color={theme.colors.grey2} />
    </ListItem>
  );

  const ListHeader = () => (
    <>
      <ButtonGroup
        buttons={["All Assets", "Watchlist"]}
        selectedIndex={selectedViewIndex}
        onPress={(value) => {
          setSelectedViewIndex(value);
          // Clear search when switching views
          setSearchQuery("");
          setSearchResults([]);
        }}
        containerStyle={styles.buttonGroupContainer}
        selectedButtonStyle={styles.buttonGroupSelected}
        textStyle={styles.buttonGroupText}
      />
      {selectedViewIndex === 0 && (
        <SearchBar
          testID="market-search"
          placeholder="Search assets..."
          onChangeText={setSearchQuery}
          value={searchQuery}
          containerStyle={styles.searchBarContainer}
          inputContainerStyle={styles.searchBarInputContainer}
          inputStyle={styles.searchBarInput}
          lightTheme={theme.mode === "light"}
          round
          showLoading={isSearching}
          onClear={() => setSearchQuery("")}
        />
      )}
      {error ? (
        <Text
          testID="error-message"
          style={[styles.errorText, { padding: 15 }]}
        >
          {error}
        </Text>
      ) : null}
    </>
  );

  const ListEmpty = () => (
    <View style={styles.centered}>
      {loading || (isSearching && selectedViewIndex === 0) ? (
        <ActivityIndicator
          testID="loading-indicator"
          size="large"
          color={theme.colors.primary}
        />
      ) : error ? (
        <Button
          testID="retry-button"
          title="Retry"
          onPress={
            selectedViewIndex === 0
              ? fetchInitialMarketData
              : fetchWatchlistData
          }
        />
      ) : (
        <Text style={styles.infoText}>
          {selectedViewIndex === 0
            ? searchQuery.trim()
              ? "No assets found matching your search."
              : "No market data available."
            : "Your watchlist is empty. Add assets using the star icon on the detail screen."}
        </Text>
      )}
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        testID="market-list"
        data={dataToDisplay}
        renderItem={renderItem}
        keyExtractor={(item) => item.symbol}
        ListHeaderComponent={ListHeader}
        ListEmptyComponent={ListEmpty}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={theme.colors.primary}
          />
        }
        contentContainerStyle={
          dataToDisplay.length === 0 ? { flexGrow: 1 } : {}
        }
      />
    </View>
  );
};

export default MarketScreen;
