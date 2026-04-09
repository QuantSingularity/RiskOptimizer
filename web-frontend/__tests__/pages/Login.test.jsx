import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthProvider } from "../../src/context/AuthContext";
import Login from "../../src/pages/Login";
import apiService from "../../src/services/apiService";

vi.mock("../../src/services/apiService", () => ({
  default: {
    auth: {
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
    },
  },
}));

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => vi.fn() };
});

const renderLogin = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>,
  );

describe("Login Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("renders the brand heading", () => {
    renderLogin();
    expect(screen.getByText("RiskOptimizer")).toBeInTheDocument();
  });

  it("renders Sign In and Register tabs", () => {
    renderLogin();
    expect(screen.getByRole("tab", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /register/i })).toBeInTheDocument();
  });

  it("renders wallet address field on Sign In tab", () => {
    renderLogin();
    expect(screen.getByLabelText(/wallet address/i)).toBeInTheDocument();
  });

  it("shows validation error when submitting empty Sign In form", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(
      await screen.findByText(/please enter your wallet address/i),
    ).toBeInTheDocument();
  });

  it("calls apiService.auth.login on valid Sign In submission", async () => {
    apiService.auth.login.mockResolvedValue({
      status: "success",
      data: { token: "tok", user: { id: 1, wallet_address: "0xabc" } },
    });
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText(/wallet address/i), "0xabc123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() =>
      expect(apiService.auth.login).toHaveBeenCalledWith({
        wallet_address: "0xabc123",
      }),
    );
  });

  it("shows error alert on failed login", async () => {
    apiService.auth.login.mockRejectedValue(new Error("Invalid wallet"));
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText(/wallet address/i), "0xbad");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("switches to Register tab and shows registration fields", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole("tab", { name: /register/i }));
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("shows validation error on incomplete Register form", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole("tab", { name: /register/i }));
    await user.click(screen.getByRole("button", { name: /create account/i }));
    expect(
      await screen.findByText(/all fields are required/i),
    ).toBeInTheDocument();
  });

  it("calls apiService.auth.register with correct payload", async () => {
    apiService.auth.register.mockResolvedValue({
      status: "success",
      data: { token: "tok2", user: { id: 2, email: "a@a.com" } },
    });
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole("tab", { name: /register/i }));
    await user.type(screen.getByLabelText(/username/i), "alice");
    await user.type(screen.getByLabelText(/email/i), "alice@test.com");
    await user.type(screen.getByLabelText(/password/i), "secret123");
    await user.type(screen.getAllByLabelText(/wallet address/i)[0], "0xdef456");
    await user.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() =>
      expect(apiService.auth.register).toHaveBeenCalledWith({
        username: "alice",
        email: "alice@test.com",
        password: "secret123",
        wallet_address: "0xdef456",
      }),
    );
  });
});
