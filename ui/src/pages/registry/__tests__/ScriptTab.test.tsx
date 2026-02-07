import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ScriptTab } from "../ScriptTab";
import type { Script } from "@/lib/types";

// Mock DataViewer to avoid Shiki/syntax highlighting in tests
vi.mock("@/components/ui/data-viewer", () => ({
  DataViewer: () => <div data-testid="data-viewer" />,
}));

const makeScript = (overrides: Partial<Script> = {}): Script => ({
  id: "s1",
  entity_id: "script.test",
  alias: "Test Script",
  state: "off",
  ...overrides,
});

describe("ScriptTab", () => {
  it("renders running and total stat pills", () => {
    const scripts = [
      makeScript({ id: "s1", state: "off" }),
      makeScript({ id: "s2", state: "off" }),
      makeScript({ id: "s3", state: "off" }),
    ];
    render(
      <ScriptTab
        scripts={scripts}
        isLoading={false}
        searchQuery=""
        runningCount={1}
      />,
    );
    // Should show running count and total stat pills
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
