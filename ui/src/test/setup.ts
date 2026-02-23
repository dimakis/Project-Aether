import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Mock react-diff-viewer-continued — its ESM workerBundle import
// breaks in jsdom. Provide a lightweight stub that renders props.
vi.mock("react-diff-viewer-continued", () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    // @ts-expect-error -- CJS require in vi.mock factory (no top-level await)
    const React = require("react");
    return React.createElement("div", {
      "data-testid": "mock-diff-viewer",
      "data-old-value": props.oldValue,
      "data-new-value": props.newValue,
    });
  },
  DiffMethod: {
    CHARS: "diffChars",
    WORDS: "diffWords",
    LINES: "diffLines",
    SENTENCES: "diffSentences",
    CSS: "diffCss",
  },
}));
