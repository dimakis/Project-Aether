import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AutomationTab } from "../AutomationTab";
import type { Automation } from "@/lib/types";

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
});
