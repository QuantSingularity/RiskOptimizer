import { act, fireEvent, render, waitFor } from "@testing-library/react-native";
import { Alert } from "react-native";
import CreatePortfolioScreen from "../../src/screens/Portfolios/CreatePortfolioScreen";
import apiService from "../../src/services/apiService";

jest.mock("@rneui/themed", () => require("../../test-utils/rneuiMock"));
jest.mock("../../src/services/apiService", () => ({
  __esModule: true,
  default: { createPortfolio: jest.fn() },
}));

const setup = () => {
  const navigation = { goBack: jest.fn() };
  const utils = render(<CreatePortfolioScreen navigation={navigation} />);
  return { navigation, ...utils };
};

describe("CreatePortfolioScreen", () => {
  let alertSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    alertSpy = jest.spyOn(Alert, "alert").mockImplementation(() => {});
    jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("renders the form with USD as the default currency", () => {
    const { getByTestId } = setup();
    expect(getByTestId("portfolio-name-input").props.value).toBe("");
    expect(getByTestId("portfolio-description-input")).toBeTruthy();
    expect(getByTestId("portfolio-currency-input").props.value).toBe("USD");
  });

  it("does not submit while the name is empty or only whitespace", () => {
    const { getByTestId } = setup();
    fireEvent.press(getByTestId("create-portfolio-submit"));
    fireEvent.changeText(getByTestId("portfolio-name-input"), "   ");
    fireEvent.press(getByTestId("create-portfolio-submit"));
    expect(apiService.createPortfolio).not.toHaveBeenCalled();
    expect(
      getByTestId("create-portfolio-submit").props.accessibilityState.disabled,
    ).toBe(true);
  });

  it("submits trimmed values with an upper-cased currency and navigates back", async () => {
    apiService.createPortfolio.mockResolvedValue({ data: {} });
    const { getByTestId, navigation } = setup();
    fireEvent.changeText(getByTestId("portfolio-name-input"), "  Growth Fund ");
    fireEvent.changeText(getByTestId("portfolio-description-input"), " Tech ");
    fireEvent.changeText(getByTestId("portfolio-currency-input"), "eur");
    fireEvent.press(getByTestId("create-portfolio-submit"));

    await waitFor(() => expect(navigation.goBack).toHaveBeenCalledTimes(1));
    expect(apiService.createPortfolio).toHaveBeenCalledWith({
      name: "Growth Fund",
      description: "Tech",
      currency: "EUR",
    });
  });

  it("falls back to USD when the currency is cleared", async () => {
    apiService.createPortfolio.mockResolvedValue({ data: {} });
    const { getByTestId } = setup();
    fireEvent.changeText(getByTestId("portfolio-name-input"), "Fund");
    fireEvent.changeText(getByTestId("portfolio-currency-input"), "  ");
    fireEvent.press(getByTestId("create-portfolio-submit"));
    await waitFor(() => expect(apiService.createPortfolio).toHaveBeenCalled());
    expect(apiService.createPortfolio.mock.calls[0][0].currency).toBe("USD");
  });

  it("shows a loading indicator and hides the button while saving", async () => {
    let resolve;
    apiService.createPortfolio.mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    const { getByTestId, queryByTestId, navigation } = setup();
    fireEvent.changeText(getByTestId("portfolio-name-input"), "Fund");
    fireEvent.press(getByTestId("create-portfolio-submit"));

    expect(getByTestId("loading-indicator")).toBeTruthy();
    expect(queryByTestId("create-portfolio-submit")).toBeNull();

    await act(async () => {
      resolve({ data: {} });
    });
    expect(navigation.goBack).toHaveBeenCalled();
  });

  it("reports a failed creation, stays on the screen and re-enables submitting", async () => {
    apiService.createPortfolio.mockRejectedValue(new Error("boom"));
    const { getByTestId, findByTestId, navigation } = setup();
    fireEvent.changeText(getByTestId("portfolio-name-input"), "Fund");
    fireEvent.press(getByTestId("create-portfolio-submit"));

    const error = await findByTestId("create-error");
    expect(error.props.children).toBe(
      "Could not create portfolio. Please try again.",
    );
    expect(alertSpy).toHaveBeenCalledWith("Error", expect.any(String));
    expect(navigation.goBack).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(getByTestId("create-portfolio-submit")).toBeTruthy(),
    );
  });
});
