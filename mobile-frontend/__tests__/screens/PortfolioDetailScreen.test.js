import { act, fireEvent, render } from "@testing-library/react-native";
import PortfolioDetailScreen from "../../src/screens/Portfolios/PortfolioDetailScreen";
import apiService from "../../src/services/apiService";

jest.mock("@rneui/themed", () => require("../../test-utils/rneuiMock"));
jest.mock("react-native-chart-kit", () => ({ PieChart: () => null }));
jest.mock("@react-navigation/native", () => ({
  useFocusEffect: (callback) => {
    const { useEffect: effect } = require("react");
    effect(callback, [callback]);
  },
}));
jest.mock("../../src/services/apiService", () => ({
  __esModule: true,
  default: { getPortfolioDetails: jest.fn() },
}));

const DETAILS = {
  id: 7,
  name: "Retirement",
  description: "Long term",
  currency: "USD",
  total_value: 12000,
  risk_score: 0.31,
  assets: [
    {
      id: "1",
      symbol: "AAPL",
      name: "Apple",
      quantity: 40,
      value: 6000,
      allocation_percentage: 50,
      performance: 5.25,
    },
    {
      id: "2",
      symbol: "MSFT",
      name: "MSFT",
      quantity: null,
      value: 6000,
      allocation_percentage: 50,
      performance: null,
    },
  ],
};

const setup = (params = { portfolioId: 7, portfolioName: "Retirement" }) => {
  const navigation = { navigate: jest.fn(), setOptions: jest.fn() };
  const utils = render(
    <PortfolioDetailScreen route={{ params }} navigation={navigation} />,
  );
  return { navigation, ...utils };
};

describe("PortfolioDetailScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("loads the requested portfolio from the API, not from placeholder data", async () => {
    apiService.getPortfolioDetails.mockResolvedValue({
      data: { data: DETAILS },
    });
    const { findByTestId, queryByText } = setup();
    await findByTestId("asset-item-AAPL");
    expect(apiService.getPortfolioDetails).toHaveBeenCalledWith(7);
    expect(queryByText(/Tesla/)).toBeNull();
    expect(queryByText(/BTC-USD/)).toBeNull();
  });

  it("shows a loading indicator first", async () => {
    let resolve;
    apiService.getPortfolioDetails.mockReturnValue(
      new Promise((done) => (resolve = done)),
    );
    const { getByTestId, queryByTestId } = setup();
    expect(getByTestId("loading-indicator")).toBeTruthy();
    await act(async () => resolve({ data: { data: DETAILS } }));
    expect(queryByTestId("loading-indicator")).toBeNull();
  });

  it("renders totals and asset rows, using N/A for missing quantity and performance", async () => {
    apiService.getPortfolioDetails.mockResolvedValue({
      data: { data: DETAILS },
    });
    const { findByTestId, getByText } = setup();
    await findByTestId("asset-item-AAPL");
    expect(getByText(/12,000\.00/)).toBeTruthy();
    expect(getByText(/Qty: 40 \| Value: USD\s+6,000\.00/)).toBeTruthy();
    expect(getByText(/Allocation: 50\.00% \| Perf:\s+5\.25%/)).toBeTruthy();
    expect(getByText(/Qty: N\/A/)).toBeTruthy();
    expect(getByText(/Perf:\s+N\/A/)).toBeTruthy();
  });

  it("accepts the unwrapped response shape and sets the screen title", async () => {
    apiService.getPortfolioDetails.mockResolvedValue({ data: DETAILS });
    const { findByTestId, navigation } = setup({ portfolioId: 7 });
    await findByTestId("asset-item-MSFT");
    expect(navigation.setOptions).toHaveBeenLastCalledWith({
      title: "Retirement",
    });
  });

  it("shows an empty state for a portfolio without assets", async () => {
    apiService.getPortfolioDetails.mockResolvedValue({
      data: { data: { ...DETAILS, assets: [] } },
    });
    const { findByText } = setup();
    expect(await findByText(/No assets in this portfolio yet/)).toBeTruthy();
  });

  it("shows an error with retry when the request fails", async () => {
    apiService.getPortfolioDetails
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ data: { data: DETAILS } });
    const { findByTestId, getByTestId } = setup();
    expect((await findByTestId("error-message")).props.children).toBe(
      "Could not load portfolio details.",
    );
    fireEvent.press(getByTestId("retry-button"));
    expect(await findByTestId("asset-item-AAPL")).toBeTruthy();
    expect(apiService.getPortfolioDetails).toHaveBeenCalledTimes(2);
  });

  it("treats an empty response as an error", async () => {
    apiService.getPortfolioDetails.mockResolvedValue({ data: null });
    const { findByTestId } = setup();
    expect(await findByTestId("error-message")).toBeTruthy();
  });

  it("loads once without looping", async () => {
    apiService.getPortfolioDetails.mockResolvedValue({
      data: { data: DETAILS },
    });
    const { findByTestId } = setup();
    await findByTestId("asset-item-AAPL");
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
    expect(apiService.getPortfolioDetails).toHaveBeenCalledTimes(1);
  });

  it("navigates to the asset and to the add asset screen", async () => {
    apiService.getPortfolioDetails.mockResolvedValue({
      data: { data: DETAILS },
    });
    const { findByTestId, getByTestId, navigation } = setup();
    fireEvent.press(await findByTestId("asset-item-AAPL"));
    expect(navigation.navigate).toHaveBeenCalledWith("AssetDetailPortfolio", {
      symbol: "AAPL",
    });
    fireEvent.press(getByTestId("add-asset-button"));
    expect(navigation.navigate).toHaveBeenCalledWith("AddAsset", {
      portfolioId: 7,
    });
  });
});
