import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AutomationTab } from "../AutomationTab";
import type { Automation } from "@/lib/types";

// Mock framer-motion so AnimatePresence removes children synchronously
vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({
      children,
      ...props
    }: React.HTMLAttributes<HTMLDivElement> & { [key: string]: unknown }) => {
      // Strip framer-motion-specific props and pass through
      const { initial, animate, exit, transition, ...rest } = props as Record<string, unknown>;
      return <div {...(rest as React.HTMLAttributes<HTMLDivElement>)}>{children}</div>;
    },
  },
}));

// Mock hooks and heavy components
vi.mock("@/api/hooks", () => ({
  useAutomationConfig: vi.fn(() => ({ data: null, isLoading: false })),
}));
vi.mock("@/components/ui/data-viewer", () => ({
  YamlViewer: () => <div data-testid="yaml-viewer" />,
}));

const makeAutomation = (overrides: Partial<Automation> = {}): Automation => ({
  id: "a1",
  entity_id: "automation.test",
  ha_automation_id: "ha1",
  alias: "Test Automation",
  state: "on",
  ...overrides,
});

describe("AutomationTab", () => {
  describe("search result count", () => {
    it("shows result count when search filters the list", () => {
      const automations = [
        makeAutomation({ id: "a1", alias: "Kitchen lights" }),
        makeAutomation({ id: "a2", alias: "Living room lights" }),
        makeAutomation({ id: "a3", alias: "Bedroom fan" }),
      ];
      render(
        <AutomationTab
          automations={automations}
          isLoading={false}
          searchQuery="lights"
          enabledCount={3}
          disabledCount={0}
        />,
      );
      expect(screen.getByText(/showing 2 of 3/i)).toBeInTheDocument();
    });

    it("does not show result count when search is empty", () => {
      const automations = [
        makeAutomation({ id: "a1" }),
        makeAutomation({ id: "a2" }),
      ];
      render(
        <AutomationTab
          automations={automations}
          isLoading={false}
          searchQuery=""
          enabledCount={2}
          disabledCount={0}
        />,
      );
      expect(screen.queryByText(/showing/i)).not.toBeInTheDocument();
    });

    it("does not show result count when all items match", () => {
      const automations = [
        makeAutomation({ id: "a1", alias: "Light A" }),
        makeAutomation({ id: "a2", alias: "Light B" }),
      ];
      render(
        <AutomationTab
          automations={automations}
          isLoading={false}
          searchQuery="light"
          enabledCount={2}
          disabledCount={0}
        />,
      );
      expect(screen.queryByText(/showing/i)).not.toBeInTheDocument();
    });
  });

  describe("expand/collapse animation", () => {
    it("expands card detail on click and collapses on second click", async () => {
      const user = userEvent.setup();
      const automations = [
        makeAutomation({
          id: "a1",
          alias: "Kitchen lights",
          description: "Turn on kitchen lights at sunset",
        }),
      ];
      render(
        <AutomationTab
          automations={automations}
          isLoading={false}
          searchQuery=""
          enabledCount={1}
          disabledCount={0}
        />,
      );
      // Click to expand
      await user.click(screen.getByText("Kitchen lights"));
      expect(
        screen.getByText("Turn on kitchen lights at sunset"),
      ).toBeInTheDocument();
      // Click again to collapse
      await user.click(screen.getByText("Kitchen lights"));
      expect(
        screen.queryByText("Turn on kitchen lights at sunset"),
      ).not.toBeInTheDocument();
    });

    it("wraps expanded content in a motion container", async () => {
      const user = userEvent.setup();
      const automations = [
        makeAutomation({
          id: "a1",
          alias: "Kitchen lights",
          description: "Turn on kitchen lights at sunset",
        }),
      ];
      const { container } = render(
        <AutomationTab
          automations={automations}
          isLoading={false}
          searchQuery=""
          enabledCount={1}
          disabledCount={0}
        />,
      );
      await user.click(screen.getByText("Kitchen lights"));
      // Framer motion.div renders with data-framer-* attributes or style containing transform
      // Check that the expanded detail has a motion wrapper via data-testid
      const motionWrapper = container.querySelector("[data-testid='expand-motion']");
      expect(motionWrapper).toBeInTheDocument();
    });
  });
});
