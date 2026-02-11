import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EntityActionMenu } from "../EntityActionMenu";
import type { EntityAction } from "../EntityActionMenu";

// Mock framer-motion
vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  motion: {
    div: ({
      children,
      ...props
    }: React.HTMLAttributes<HTMLDivElement> & { [key: string]: unknown }) => {
      const { initial, animate, exit, transition, ...rest } =
        props as Record<string, unknown>;
      return (
        <div {...(rest as React.HTMLAttributes<HTMLDivElement>)}>
          {children}
        </div>
      );
    },
  },
}));

describe("EntityActionMenu", () => {
  const defaultProps = {
    entityId: "automation.kitchen_lights",
    entityType: "automation" as const,
    entityLabel: "Kitchen Lights",
    onAction: vi.fn(),
  };

  it("renders the trigger button", () => {
    render(<EntityActionMenu {...defaultProps} />);
    expect(
      screen.getByRole("button", { name: /actions/i }),
    ).toBeInTheDocument();
  });

  it("shows menu items when trigger button is clicked", async () => {
    const user = userEvent.setup();
    render(<EntityActionMenu {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: /actions/i }));

    expect(screen.getByText("Improve")).toBeInTheDocument();
    expect(screen.getByText("Deep Review")).toBeInTheDocument();
    expect(screen.getByText("Edit YAML")).toBeInTheDocument();
    expect(screen.getByText("Chat about this")).toBeInTheDocument();
  });

  it("does not show menu items before clicking", () => {
    render(<EntityActionMenu {...defaultProps} />);

    expect(screen.queryByText("Improve")).not.toBeInTheDocument();
    expect(screen.queryByText("Deep Review")).not.toBeInTheDocument();
  });

  it("calls onAction with 'improve' when Improve is clicked", async () => {
    const onAction = vi.fn();
    const user = userEvent.setup();
    render(<EntityActionMenu {...defaultProps} onAction={onAction} />);

    await user.click(screen.getByRole("button", { name: /actions/i }));
    await user.click(screen.getByText("Improve"));

    expect(onAction).toHaveBeenCalledWith("improve");
  });

  it("calls onAction with 'deep_review' when Deep Review is clicked", async () => {
    const onAction = vi.fn();
    const user = userEvent.setup();
    render(<EntityActionMenu {...defaultProps} onAction={onAction} />);

    await user.click(screen.getByRole("button", { name: /actions/i }));
    await user.click(screen.getByText("Deep Review"));

    expect(onAction).toHaveBeenCalledWith("deep_review");
  });

  it("calls onAction with 'edit_yaml' when Edit YAML is clicked", async () => {
    const onAction = vi.fn();
    const user = userEvent.setup();
    render(<EntityActionMenu {...defaultProps} onAction={onAction} />);

    await user.click(screen.getByRole("button", { name: /actions/i }));
    await user.click(screen.getByText("Edit YAML"));

    expect(onAction).toHaveBeenCalledWith("edit_yaml");
  });

  it("calls onAction with 'chat' when Chat is clicked", async () => {
    const onAction = vi.fn();
    const user = userEvent.setup();
    render(<EntityActionMenu {...defaultProps} onAction={onAction} />);

    await user.click(screen.getByRole("button", { name: /actions/i }));
    await user.click(screen.getByText("Chat about this"));

    expect(onAction).toHaveBeenCalledWith("chat");
  });

  it("closes the menu after an action is selected", async () => {
    const user = userEvent.setup();
    render(<EntityActionMenu {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: /actions/i }));
    expect(screen.getByText("Improve")).toBeInTheDocument();

    await user.click(screen.getByText("Improve"));
    expect(screen.queryByText("Deep Review")).not.toBeInTheDocument();
  });

  it("closes the menu when clicking outside", async () => {
    const user = userEvent.setup();
    render(
      <div>
        <EntityActionMenu {...defaultProps} />
        <div data-testid="outside">Outside</div>
      </div>,
    );

    await user.click(screen.getByRole("button", { name: /actions/i }));
    expect(screen.getByText("Improve")).toBeInTheDocument();

    // Click outside
    await user.click(screen.getByTestId("outside"));
    expect(screen.queryByText("Improve")).not.toBeInTheDocument();
  });
});
