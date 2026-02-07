import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SceneTab } from "../SceneTab";
import type { Scene } from "@/lib/types";

// Mock DataViewer to avoid Shiki/syntax highlighting in tests
vi.mock("@/components/ui/data-viewer", () => ({
  DataViewer: () => <div data-testid="data-viewer" />,
}));

const makeScene = (overrides: Partial<Scene> = {}): Scene => ({
  id: "sc1",
  entity_id: "scene.test",
  name: "Test Scene",
  ...overrides,
});

describe("SceneTab", () => {
  it("renders total stat pill", () => {
    const scenes = [
      makeScene({ id: "sc1" }),
      makeScene({ id: "sc2", name: "Scene 2" }),
    ];
    render(
      <SceneTab scenes={scenes} isLoading={false} searchQuery="" />,
    );
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});
