import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import Sidebar from "../../src/components/navigation/Sidebar";

const renderSidebar = (props = {}) =>
  render(
    <MemoryRouter initialEntries={["/"]}>
      <Sidebar
        mobileOpen={false}
        onClose={vi.fn()}
        isMobile={false}
        {...props}
      />
    </MemoryRouter>,
  );

describe("Sidebar", () => {
  it("renders all navigation items", () => {
    renderSidebar();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Portfolio")).toBeInTheDocument();
    expect(screen.getByText("Risk Analysis")).toBeInTheDocument();
    expect(screen.getByText("Optimization")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("renders Help & Support item", () => {
    renderSidebar();
    expect(screen.getByText("Help & Support")).toBeInTheDocument();
  });

  it("highlights the active route", () => {
    render(
      <MemoryRouter initialEntries={["/portfolio"]}>
        <Sidebar mobileOpen={false} onClose={vi.fn()} isMobile={false} />
      </MemoryRouter>,
    );
    const portfolioBtn = screen.getByText("Portfolio").closest("li");
    expect(portfolioBtn).toHaveClass("Mui-selected");
  });

  it("closes mobile drawer on navigation when isMobile=true", async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    renderSidebar({ isMobile: true, onClose: handleClose });
    await user.click(screen.getByText("Portfolio"));
    expect(handleClose).toHaveBeenCalledOnce();
  });

  it("does not close drawer on navigation when isMobile=false", async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    renderSidebar({ isMobile: false, onClose: handleClose });
    await user.click(screen.getByText("Portfolio"));
    expect(handleClose).not.toHaveBeenCalled();
  });
});
