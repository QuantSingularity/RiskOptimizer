import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthProvider } from "../../src/context/AuthContext";
import Settings from "../../src/pages/Settings";

vi.mock("../../src/services/apiService", () => ({
  default: {
    auth: { login: vi.fn(), logout: vi.fn(), register: vi.fn() },
  },
}));

const renderSettings = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <Settings />
      </AuthProvider>
    </MemoryRouter>,
  );

describe("Settings Page", () => {
  it("renders the page heading", () => {
    renderSettings();
    expect(
      screen.getByRole("heading", { name: /settings/i }),
    ).toBeInTheDocument();
  });

  it("renders Account Settings card", () => {
    renderSettings();
    expect(screen.getByText("Account Settings")).toBeInTheDocument();
  });

  it("renders Preferences card", () => {
    renderSettings();
    expect(screen.getByText("Preferences")).toBeInTheDocument();
  });

  it("renders Security card", () => {
    renderSettings();
    expect(screen.getByText("Security")).toBeInTheDocument();
  });

  it("renders Save Changes button", () => {
    renderSettings();
    expect(
      screen.getByRole("button", { name: /save changes/i }),
    ).toBeInTheDocument();
  });

  it("renders Logout button", () => {
    renderSettings();
    expect(screen.getByRole("button", { name: /logout/i })).toBeInTheDocument();
  });

  it("shows success snackbar on save", async () => {
    const user = userEvent.setup();
    renderSettings();
    await user.click(screen.getByRole("button", { name: /save changes/i }));
    await waitFor(() =>
      expect(
        screen.getByText(/settings saved successfully/i),
      ).toBeInTheDocument(),
    );
  });

  it("renders toggle switches for preferences", () => {
    renderSettings();
    const switches = screen.getAllByRole("checkbox");
    expect(switches.length).toBeGreaterThanOrEqual(3);
  });

  it("renders Risk Tolerance number field", () => {
    renderSettings();
    expect(screen.getByText(/default risk tolerance/i)).toBeInTheDocument();
  });

  it("renders security info alert", () => {
    renderSettings();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
