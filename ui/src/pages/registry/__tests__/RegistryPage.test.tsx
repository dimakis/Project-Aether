import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RegistryPage } from "../index";
import {
  useRegistryAutomations,
  useRegistryScripts,
  useRegistryScenes,
  useRegistryServices,
  useRegistrySummary,
} from "@/api/hooks";

const mockSummary = {
  automations_count: 12,
  automations_enabled: 10,
  scripts_count: 5,
  scenes_count: 3,
  services_count: 42,
  services_seeded: 8,
};

const mockSyncMutate = vi.fn();

// Mock all registry hooks
vi.mock("@/api/hooks", () => ({
  useRegistryAutomations: vi.fn(() => ({ data: null, isLoading: false })),
  useRegistryScripts: vi.fn(() => ({ data: null, isLoading: false })),
  useRegistryScenes: vi.fn(() => ({ data: null, isLoading: false })),
  useRegistryServices: vi.fn(() => ({ data: null, isLoading: false })),
  useRegistrySummary: vi.fn(() => ({ data: mockSummary, isLoading: false })),
  useSyncRegistry: vi.fn(() => ({ mutate: mockSyncMutate, isPending: false })),
}));

// Mock InlineAssistant to avoid QueryClientProvider dependency in unit tests
vi.mock("@/components/InlineAssistant", () => ({
  InlineAssistant: () => <div data-testid="inline-assistant">InlineAssistant</div>,
}));

// Mock child tab components to isolate RegistryPage tests
vi.mock("../AutomationTab", () => ({
  AutomationTab: () => <div data-testid="automation-tab-content">AutomationTab</div>,
}));
vi.mock("../ScriptTab", () => ({
  ScriptTab: () => <div data-testid="script-tab-content">ScriptTab</div>,
}));
vi.mock("../SceneTab", () => ({
  SceneTab: () => <div data-testid="scene-tab-content">SceneTab</div>,
}));
vi.mock("../ServiceTab", () => ({
  ServiceTab: () => <div data-testid="service-tab-content">ServiceTab</div>,
}));
vi.mock("../OverviewTab", () => ({
  OverviewTab: () => <div data-testid="overview-tab-content">OverviewTab</div>,
}));

describe("RegistryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders overview tab as the default active tab", () => {
    render(<RegistryPage />);
    // Overview tab content should be visible by default
    expect(screen.getByTestId("overview-tab-content")).toBeInTheDocument();
    // Other tab contents should NOT be visible
    expect(screen.queryByTestId("automation-tab-content")).not.toBeInTheDocument();
    expect(screen.queryByTestId("script-tab-content")).not.toBeInTheDocument();
    expect(screen.queryByTestId("scene-tab-content")).not.toBeInTheDocument();
    expect(screen.queryByTestId("service-tab-content")).not.toBeInTheDocument();
  });

  it("renders tabs in correct order with Overview first", () => {
    render(<RegistryPage />);
    const tabButtons = screen.getAllByRole("tab");
    expect(tabButtons).toHaveLength(5);
    expect(tabButtons[0].textContent).toContain("Overview");
    expect(tabButtons[1].textContent).toContain("Automations");
    expect(tabButtons[2].textContent).toContain("Scripts");
    expect(tabButtons[3].textContent).toContain("Scenes");
    expect(tabButtons[4].textContent).toContain("Services");
  });

  it("switches to automations tab when clicked", async () => {
    const user = userEvent.setup();
    render(<RegistryPage />);
    // Click automations tab
    await user.click(screen.getByRole("tab", { name: /automations/i }));
    expect(screen.getByTestId("automation-tab-content")).toBeInTheDocument();
    expect(screen.queryByTestId("overview-tab-content")).not.toBeInTheDocument();
  });

  it("hides search bar on overview tab", () => {
    render(<RegistryPage />);
    // Search input should NOT be visible on overview tab
    expect(screen.queryByPlaceholderText(/search/i)).not.toBeInTheDocument();
  });

  it("shows search bar on non-overview tabs", async () => {
    const user = userEvent.setup();
    render(<RegistryPage />);
    await user.click(screen.getByRole("tab", { name: /automations/i }));
    expect(screen.getByPlaceholderText(/search automations/i)).toBeInTheDocument();
  });

  describe("tab count badges", () => {
    it("renders counts from summary data in tab badges", () => {
      render(<RegistryPage />);
      // Find tab elements with counts
      const automationsTab = screen.getByRole("tab", { name: /automations/i });
      const scriptsTab = screen.getByRole("tab", { name: /scripts/i });
      const scenesTab = screen.getByRole("tab", { name: /scenes/i });
      const servicesTab = screen.getByRole("tab", { name: /services/i });

      expect(automationsTab.textContent).toContain("12");
      expect(scriptsTab.textContent).toContain("5");
      expect(scenesTab.textContent).toContain("3");
      expect(servicesTab.textContent).toContain("42");
    });

    it("does not render a count badge on the overview tab", () => {
      render(<RegistryPage />);
      const overviewTab = screen.getByRole("tab", { name: /overview/i });
      // Overview should NOT contain any numeric badge
      expect(overviewTab.textContent).toBe("Overview");
    });

    it("renders tab counts using Badge component styling", () => {
      render(<RegistryPage />);
      // Badge component uses the class "rounded-full" from badgeVariants
      const automationsTab = screen.getByRole("tab", { name: /automations/i });
      const badge = automationsTab.querySelector(".rounded-full");
      expect(badge).toBeInTheDocument();
      expect(badge?.textContent).toBe("12");
    });
  });

  describe("sync button", () => {
    it("renders sync registry button in the header", () => {
      render(<RegistryPage />);
      expect(screen.getByRole("button", { name: /sync registry/i })).toBeInTheDocument();
    });

    it("calls sync mutate when sync button is clicked", async () => {
      const user = userEvent.setup();
      render(<RegistryPage />);
      await user.click(screen.getByRole("button", { name: /sync registry/i }));
      expect(mockSyncMutate).toHaveBeenCalled();
    });
  });

  describe("lazy data loading", () => {
    it("only enables summary hook on mount (overview tab)", () => {
      render(<RegistryPage />);
      expect(useRegistrySummary).toHaveBeenCalledWith({ enabled: true });
      expect(useRegistryAutomations).toHaveBeenCalledWith({ enabled: false });
      expect(useRegistryScripts).toHaveBeenCalledWith({ enabled: false });
      expect(useRegistryScenes).toHaveBeenCalledWith({ enabled: false });
      expect(useRegistryServices).toHaveBeenCalledWith({ enabled: false });
    });

    it("enables automations hook when automations tab is active", async () => {
      const user = userEvent.setup();
      render(<RegistryPage />);
      await user.click(screen.getByRole("tab", { name: /automations/i }));
      expect(useRegistryAutomations).toHaveBeenLastCalledWith({ enabled: true });
      expect(useRegistryScripts).toHaveBeenLastCalledWith({ enabled: false });
      expect(useRegistryScenes).toHaveBeenLastCalledWith({ enabled: false });
      expect(useRegistryServices).toHaveBeenLastCalledWith({ enabled: false });
    });
  });
});
