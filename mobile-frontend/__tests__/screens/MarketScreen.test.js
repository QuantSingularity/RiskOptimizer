import { act, fireEvent, render, waitFor } from "@testing-library/react-native";
import MarketScreen from "../../src/screens/Market/MarketScreen";
import apiService from "../../src/services/apiService";
import { getWatchlist } from "../../src/utils/watchlist";

jest.mock("@rneui/themed", () => require("../../test-utils/rneuiMock"));
jest.mock("lodash", () => ({
  __esModule: true,
  default: { debounce: (fn) => fn },
}));
jest.mock("@react-navigation/native", () => ({
  useFocusEffect: (callback) => {
    const { useEffect: effect } = require("react");
    effect(callback, [callback]);
  },
}));
jest.mock("../../src/utils/watchlist", () => ({ getWatchlist: jest.fn() }));
jest.mock("../../src/services/apiService", () => ({
  __esModule: true,
  default: { getAssetPriceHistory: jest.fn(), searchAssets: jest.fn() },
}));

const history = (symbol, price, previous) => ({
  data: {
    meta: {
      symbol,
      shortName: `${symbol} Inc`,
      regularMarketPrice: price,
      chartPreviousClose: previous,
      currency: "USD",
    },
  },
});

const DEFAULT_SYMBOLS = [
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

const setup = () => {
  const navigation = { navigate: jest.fn() };
  return { navigation, ...render(<MarketScreen navigation={navigation} />) };
};

describe("MarketScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, "error").mockImplementation(() => {});
    jest.spyOn(console, "warn").mockImplementation(() => {});
    getWatchlist.mockResolvedValue([]);
    apiService.getAssetPriceHistory.mockImplementation((symbol) =>
      Promise.resolve(history(symbol, 110, 100)),
    );
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("shows a loading indicator and then the default market list", async () => {
    const { getByTestId, findByTestId, queryByTestId } = setup();
    expect(getByTestId("loading-indicator")).toBeTruthy();
    expect(await findByTestId("market-item-AAPL")).toBeTruthy();
    expect(queryByTestId("loading-indicator")).toBeNull();
    for (const symbol of DEFAULT_SYMBOLS) {
      expect(getByTestId(`market-item-${symbol}`)).toBeTruthy();
    }
    expect(apiService.getAssetPriceHistory).toHaveBeenCalledTimes(
      DEFAULT_SYMBOLS.length,
    );
  });

  it("shows price and percentage change from the quote metadata", async () => {
    const { findByTestId, getAllByText } = setup();
    await findByTestId("market-item-AAPL");
    expect(getAllByText(/110/).length).toBeGreaterThan(0);
    expect(getAllByText(/10\.00%/).length).toBeGreaterThan(0);
  });

  it("keeps assets whose quotes load and skips the ones that fail", async () => {
    apiService.getAssetPriceHistory.mockImplementation((symbol) =>
      symbol === "TSLA"
        ? Promise.reject(new Error("down"))
        : Promise.resolve(history(symbol, 50, 50)),
    );
    const { findByTestId, queryByTestId } = setup();
    await findByTestId("market-item-AAPL");
    expect(queryByTestId("market-item-TSLA")).toBeNull();
  });

  it("reports an error with a retry when every quote fails", async () => {
    apiService.getAssetPriceHistory.mockRejectedValue(new Error("offline"));
    const { findByTestId, getByTestId } = setup();
    expect((await findByTestId("error-message")).props.children).toBe(
      "Could not load initial market data.",
    );
    apiService.getAssetPriceHistory.mockImplementation((symbol) =>
      Promise.resolve(history(symbol, 10, 10)),
    );
    fireEvent.press(getByTestId("retry-button"));
    expect(await findByTestId("market-item-AAPL")).toBeTruthy();
  });

  it("navigates to the asset detail screen", async () => {
    const { findByTestId, navigation } = setup();
    fireEvent.press(await findByTestId("market-item-MSFT"));
    expect(navigation.navigate).toHaveBeenCalledWith("AssetDetailMarket", {
      symbol: "MSFT",
    });
  });

  it("searches assets and shows only the matches with their prices", async () => {
    apiService.searchAssets.mockResolvedValue({
      data: { assets: [{ symbol: "NFLX" }] },
    });
    apiService.getAssetPriceHistory.mockImplementation((symbol) =>
      Promise.resolve(history(symbol, 300, 290)),
    );
    const { findByTestId, getByTestId, queryByTestId } = setup();
    await findByTestId("market-item-AAPL");
    fireEvent.changeText(getByTestId("market-search"), "netflix");
    expect(await findByTestId("market-item-NFLX")).toBeTruthy();
    expect(queryByTestId("market-item-AAPL")).toBeNull();
    expect(apiService.searchAssets).toHaveBeenCalledWith("netflix");
  });

  it("reports a failed search", async () => {
    apiService.searchAssets.mockRejectedValue(new Error("nope"));
    const { findByTestId, getByTestId } = setup();
    await findByTestId("market-item-AAPL");
    fireEvent.changeText(getByTestId("market-search"), "x");
    expect((await findByTestId("error-message")).props.children).toBe(
      "Could not perform search.",
    );
  });

  it("shows a message when a search finds nothing", async () => {
    apiService.searchAssets.mockResolvedValue({ data: { assets: [] } });
    const { findByTestId, getByTestId, findByText } = setup();
    await findByTestId("market-item-AAPL");
    fireEvent.changeText(getByTestId("market-search"), "zzzz");
    expect(
      await findByText("No assets found matching your search."),
    ).toBeTruthy();
  });

  it("switches to the watchlist and shows saved symbols", async () => {
    getWatchlist.mockResolvedValue(["AMD"]);
    const { findByTestId, getByTestId } = setup();
    await findByTestId("market-item-AAPL");
    await act(async () => {
      fireEvent.press(getByTestId("view-Watchlist"));
    });
    expect(await findByTestId("market-item-AMD")).toBeTruthy();
  });

  it("explains an empty watchlist", async () => {
    const { findByTestId, getByTestId, findByText } = setup();
    await findByTestId("market-item-AAPL");
    await act(async () => {
      fireEvent.press(getByTestId("view-Watchlist"));
    });
    expect(await findByText(/Your watchlist is empty/)).toBeTruthy();
    await waitFor(() => expect(getWatchlist).toHaveBeenCalled());
  });
});
