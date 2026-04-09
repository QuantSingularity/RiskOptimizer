import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AuthProvider, useAuth } from "../../src/context/AuthContext";
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

const TestConsumer = () => {
  const { user, loading, error, login, logout, register } = useAuth();
  return (
    <div>
      {loading && <p>Loading...</p>}
      {error && <p data-testid="error">{error}</p>}
      {user ? (
        <div>
          <p data-testid="user-info">Logged in: {user.email}</p>
          <button onClick={logout}>Logout</button>
        </div>
      ) : (
        <p>Not logged in</p>
      )}
      <button onClick={() => login({ wallet_address: "0xabc" })}>Login</button>
      <button
        onClick={() =>
          register({
            username: "u",
            email: "e@e.com",
            password: "pw",
            wallet_address: "0xabc",
          })
        }
      >
        Register
      </button>
    </div>
  );
};

const renderWithProvider = () =>
  render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>,
  );

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("provides initial unauthenticated state", () => {
    renderWithProvider();
    expect(screen.getByText("Not logged in")).toBeInTheDocument();
    expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId("error")).not.toBeInTheDocument();
  });

  it("sets user state on successful login", async () => {
    const mockUser = { id: 1, email: "test@test.com", wallet_address: "0xabc" };
    apiService.auth.login.mockResolvedValue({
      status: "success",
      data: { token: "tok123", user: mockUser },
    });

    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Login"));

    await waitFor(() =>
      expect(screen.getByTestId("user-info")).toHaveTextContent(
        "Logged in: test@test.com",
      ),
    );
    expect(localStorage.setItem).toHaveBeenCalled();
  });

  it("sets error state on failed login", async () => {
    apiService.auth.login.mockRejectedValue(new Error("Invalid credentials"));

    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Login"));

    await waitFor(() =>
      expect(screen.getByTestId("error")).toHaveTextContent(
        "Invalid credentials",
      ),
    );
  });

  it("clears user state on logout", async () => {
    const mockUser = { id: 1, email: "test@test.com", wallet_address: "0xabc" };
    apiService.auth.login.mockResolvedValue({
      status: "success",
      data: { token: "tok123", user: mockUser },
    });
    apiService.auth.logout.mockResolvedValue({});

    const user = userEvent.setup();
    renderWithProvider();

    await user.click(screen.getByText("Login"));
    await waitFor(() =>
      expect(screen.getByTestId("user-info")).toBeInTheDocument(),
    );

    await user.click(screen.getByText("Logout"));
    await waitFor(() =>
      expect(screen.getByText("Not logged in")).toBeInTheDocument(),
    );
    expect(localStorage.removeItem).toHaveBeenCalledWith("user");
  });

  it("handles successful registration", async () => {
    const mockUser = { id: 2, email: "e@e.com", wallet_address: "0xabc" };
    apiService.auth.register.mockResolvedValue({
      status: "success",
      data: { token: "tok456", user: mockUser },
    });

    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByText("Register"));

    await waitFor(() =>
      expect(screen.getByTestId("user-info")).toHaveTextContent(
        "Logged in: e@e.com",
      ),
    );
  });

  it("restores user from localStorage via checkAuthState", () => {
    const savedUser = {
      id: 1,
      email: "saved@test.com",
      isAuthenticated: true,
      token: "t",
    };
    localStorage.getItem.mockReturnValue(JSON.stringify(savedUser));

    const HydrateTest = () => {
      const { user, checkAuthState } = useAuth();
      act(() => checkAuthState());
      return (
        <div>
          {user ? <span data-testid="restored">{user.email}</span> : "none"}
        </div>
      );
    };

    render(
      <AuthProvider>
        <HydrateTest />
      </AuthProvider>,
    );
    expect(screen.getByTestId("restored")).toHaveTextContent("saved@test.com");
  });
});
