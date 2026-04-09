import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import Header from "../../src/components/navigation/Header";

vi.mock("@mui/material/styles", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useTheme: () => ({ palette: { mode: "dark" } }),
  };
});

describe("Header", () => {
  it("renders the brand name", () => {
    render(<Header onMenuClick={vi.fn()} />);
    expect(screen.getByText("RiskOptimizer")).toBeInTheDocument();
  });

  it("renders the logo image", () => {
    render(<Header onMenuClick={vi.fn()} />);
    expect(screen.getByAltText("RiskOptimizer Logo")).toBeInTheDocument();
  });

  it("calls onMenuClick when menu button is clicked", async () => {
    const user = userEvent.setup();
    const handleMenuClick = vi.fn();
    render(<Header onMenuClick={handleMenuClick} />);
    const menuBtn = screen.getByRole("button", { name: /open drawer/i });
    await user.click(menuBtn);
    expect(handleMenuClick).toHaveBeenCalledOnce();
  });

  it("renders notification badge", () => {
    render(<Header onMenuClick={vi.fn()} />);
    expect(screen.getByTestId("NotificationsIcon")).toBeInTheDocument();
  });

  it("renders account/avatar button", () => {
    render(<Header onMenuClick={vi.fn()} />);
    expect(screen.getByTestId("AccountCircleIcon")).toBeInTheDocument();
  });
});
