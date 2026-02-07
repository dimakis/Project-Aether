import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EmptyState } from "../EmptyState";

describe("EmptyState", () => {
  it("renders default message without sync button", () => {
    render(<EmptyState type="scripts" />);
    expect(screen.getByText(/no scripts found/i)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders sync CTA button when onSync is provided", () => {
    render(<EmptyState type="automations" onSync={() => {}} isSyncing={false} />);
    expect(screen.getByRole("button", { name: /sync now/i })).toBeInTheDocument();
  });

  it("calls onSync when sync button is clicked", async () => {
    const user = userEvent.setup();
    const onSync = vi.fn();
    render(<EmptyState type="scenes" onSync={onSync} isSyncing={false} />);

    await user.click(screen.getByRole("button", { name: /sync now/i }));
    expect(onSync).toHaveBeenCalledOnce();
  });

  it("disables sync button when isSyncing is true", () => {
    render(<EmptyState type="scripts" onSync={() => {}} isSyncing={true} />);
    const button = screen.getByRole("button", { name: /syncing/i });
    expect(button).toBeDisabled();
  });

  it("shows syncing text when isSyncing is true", () => {
    render(<EmptyState type="scripts" onSync={() => {}} isSyncing={true} />);
    expect(screen.getByText(/syncing/i)).toBeInTheDocument();
  });
});
