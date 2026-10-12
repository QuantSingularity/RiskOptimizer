import { act, fireEvent, render, waitFor } from "@testing-library/react-native";
import PortfolioListScreen from "../../src/screens/Portfolios/PortfolioListScreen";
import apiService from "../../src/services/apiService";

jest.mock("@rneui/themed", () => require("../../test-utils/rneuiMock"));
jest.mock("@react-navigation/native", () => ({
  useFocusEffect: (callback) => {
    const { useEffect: effect } = require("react");
    effect(callback, [callback]);
  },
}));
jest.mock("../../src/services/apiService", () => ({
  __esModule: true,
  default: { getPortfolios: jest.fn() },
}));

const PORTFOLIOS = [
  {
    id: 1,
    name: "Growth",
    total_value: 1500.5,
    currency: "USD",
    risk_score: 0.2134,
  },
  { id: 2, name: "Income", total_value: 0, currency: "EUR", risk_score: null },
];

const setup = () => {
  const navigation = { navigate: jest.fn() };
  return {
    navigation,
    ...render(<PortfolioListScreen navigation={navigation} />),
  };
};

describe("PortfolioListScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("shows a loading indicator until the portfolios arrive", async () => {
    let resolve;
    apiService.getPortfolios.mockReturnValue(
      new Promise((done) => (resolve = done)),
    );
    const { getByTestId, queryByTestId } = setup();
    expect(getByTestId("loading-indicator")).toBeTruthy();
    await act(async () =>
      resolve({ data: { data: { portfolios: PORTFOLIOS } } }),
    );
    expect(queryByTestId("loading-indicator")).toBeNull();
    expect(getByTestId("portfolio-item-1")).toBeTruthy();
  });

  it("renders portfolios from the API envelope with formatted values", async () => {
    apiService.getPortfolios.mockResolvedValue({
      data: { data: { portfolios: PORTFOLIOS } },
    });
    const { findByTestId, getByText } = setup();
    await findByTestId("portfolio-item-1");
    expect(getByText("Growth")).toBeTruthy();
    expect(getByText(/Value: USD\s+1,500\.50 \| Risk: 0\.21/)).toBeTruthy();
    expect(getByText(/Value: EUR\s+0\.00 \| Risk: N\/A/)).toBeTruthy();
  });

  it("also accepts the unwrapped response shape", async () => {
    apiService.getPortfolios.mockResolvedValue({
      data: { portfolios: PORTFOLIOS },
    });
    const { findByTestId } = setup();
    expect(await findByTestId("portfolio-item-2")).toBeTruthy();
  });

  it("loads once and does not refetch in a loop", async () => {
    apiService.getPortfolios.mockResolvedValue({
      data: { data: { portfolios: PORTFOLIOS } },
    });
    const { findByTestId } = setup();
    await findByTestId("portfolio-item-1");
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
    expect(apiService.getPortfolios).toHaveBeenCalledTimes(1);
  });

  it("shows an empty state", async () => {
    apiService.getPortfolios.mockResolvedValue({
      data: { data: { portfolios: [] } },
    });
    const { findByText } = setup();
    expect(await findByText("No portfolios found. Create one!")).toBeTruthy();
  });

  it("shows an error with a working retry", async () => {
    apiService.getPortfolios
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ data: { data: { portfolios: PORTFOLIOS } } });
    const { findByTestId, getByTestId, queryByTestId } = setup();
    expect((await findByTestId("error-message")).props.children).toBe(
      "Could not load portfolios.",
    );
    fireEvent.press(getByTestId("retry-button"));
    expect(await findByTestId("portfolio-item-1")).toBeTruthy();
    expect(queryByTestId("error-message")).toBeNull();
    expect(apiService.getPortfolios).toHaveBeenCalledTimes(2);
  });

  it("navigates to a portfolio and to the create screen", async () => {
    apiService.getPortfolios.mockResolvedValue({
      data: { data: { portfolios: PORTFOLIOS } },
    });
    const { findByTestId, getByTestId, navigation } = setup();
    fireEvent.press(await findByTestId("portfolio-item-1"));
    expect(navigation.navigate).toHaveBeenCalledWith(
      "PortfolioDetail",
      expect.objectContaining({ portfolioId: 1 }),
    );
    fireEvent.press(getByTestId("create-portfolio-button"));
    expect(navigation.navigate).toHaveBeenCalledWith("CreatePortfolio");
  });
});
