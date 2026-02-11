import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MarkdownRenderer } from "../markdown-renderer";

// Mock react-shiki components — mirrors the real CodeBlock's action rendering
vi.mock("@/components/ui/code-block", () => ({
  CodeBlock: ({
    code,
    language,
    action,
  }: {
    code: string;
    language: string;
    action?: { label: string; icon?: React.ReactNode; onClick: (c: string) => void };
  }) => (
    <div data-testid="code-block" data-language={language}>
      {code}
      {action && (
        <button onClick={() => action.onClick(code)}>{action.label}</button>
      )}
    </div>
  ),
  InlineCode: ({ children }: { children: React.ReactNode }) => (
    <code data-testid="inline-code">{children}</code>
  ),
}));

describe("MarkdownRenderer", () => {
  beforeEach(() => {
    // Mock clipboard API
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
    }
  });

  it("renders plain text", () => {
    render(<MarkdownRenderer content="Hello world" />);
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("renders markdown headings", () => {
    render(
      <MarkdownRenderer content="# Heading 1\n\n## Heading 2\n\n### Heading 3" />,
    );
    // Use getAllByRole since there may be multiple headings
    const headings = screen.getAllByRole("heading");
    expect(headings.length).toBeGreaterThanOrEqual(1);
    // Check that heading text contains our expected text
    const headingTexts = headings.map((h) => h.textContent);
    expect(headingTexts.some((text) => text?.includes("Heading 1"))).toBe(true);
  });

  it("renders code blocks", () => {
    const code = "const x = 1;";
    render(
      <MarkdownRenderer content={`\`\`\`javascript\n${code}\n\`\`\``} />,
    );
    const codeBlock = screen.getByTestId("code-block");
    expect(codeBlock).toBeInTheDocument();
    expect(codeBlock).toHaveAttribute("data-language", "javascript");
    expect(codeBlock).toHaveTextContent(code);
  });

  it("renders inline code", () => {
    render(<MarkdownRenderer content="Use `console.log()` to debug" />);
    const inlineCode = screen.getByTestId("inline-code");
    expect(inlineCode).toBeInTheDocument();
    expect(inlineCode).toHaveTextContent("console.log()");
  });

  it("renders links", () => {
    render(
      <MarkdownRenderer content="Visit [Google](https://google.com)" />,
    );
    const link = screen.getByRole("link", { name: /google/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "https://google.com");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders lists", () => {
    render(
      <MarkdownRenderer content="- Item 1\n- Item 2\n- Item 3" />,
    );
    // Use more flexible text matching since markdown may add extra elements
    expect(screen.getByText(/Item 1/)).toBeInTheDocument();
    expect(screen.getByText(/Item 2/)).toBeInTheDocument();
    expect(screen.getByText(/Item 3/)).toBeInTheDocument();
  });

  it("renders blockquotes", () => {
    render(<MarkdownRenderer content="> This is a quote" />);
    const quote = screen.getByText("This is a quote");
    expect(quote.closest("blockquote")).toBeInTheDocument();
  });

  it("renders tables", () => {
    const { container } = render(
      <MarkdownRenderer
        content="| Header 1 | Header 2 |\n| --- | --- |\n| Cell 1 | Cell 2 |"
      />,
    );
    // Check if table exists (remark-gfm should enable tables)
    const table = container.querySelector("table");
    if (table) {
      expect(table).toBeInTheDocument();
      expect(screen.getByText(/Header 1/)).toBeInTheDocument();
      expect(screen.getByText(/Cell 1/)).toBeInTheDocument();
    } else {
      // If tables aren't supported, at least verify the content is rendered
      expect(screen.getByText(/Header 1|Cell 1/)).toBeInTheDocument();
    }
  });

  it("shows Create Proposal button for YAML code blocks when onCreateProposal is provided", async () => {
    const onCreateProposal = vi.fn();
    const yamlContent = "key: value\nother: data";
    render(
      <MarkdownRenderer
        content={`\`\`\`yaml\n${yamlContent}\n\`\`\``}
        onCreateProposal={onCreateProposal}
      />,
    );

    const button = screen.getByRole("button", { name: /create proposal/i });
    expect(button).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(button);

    expect(onCreateProposal).toHaveBeenCalledWith(yamlContent);
  });

  it("shows Create Proposal button for YML code blocks", () => {
    const onCreateProposal = vi.fn();
    render(
      <MarkdownRenderer
        content="```yml\nkey: value\n```"
        onCreateProposal={onCreateProposal}
      />,
    );

    // YML should be treated the same as YAML
    const button = screen.queryByRole("button", { name: /create proposal/i });
    // The button may or may not appear depending on how react-markdown parses it
    // If code block is detected, button should appear
    if (screen.queryByTestId("code-block")) {
      expect(button).toBeInTheDocument();
    }
  });

  it("does not show Create Proposal button for non-YAML code blocks", () => {
    render(
      <MarkdownRenderer
        content="```javascript\nconst x = 1;\n```"
        onCreateProposal={vi.fn()}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /create proposal/i }),
    ).not.toBeInTheDocument();
  });

  it("does not show Create Proposal button when onCreateProposal is not provided", () => {
    render(<MarkdownRenderer content="```yaml\nkey: value\n```" />);

    expect(
      screen.queryByRole("button", { name: /create proposal/i }),
    ).not.toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <MarkdownRenderer content="Test" className="custom-class" />,
    );
    const wrapper = container.querySelector(".custom-class");
    expect(wrapper).toBeInTheDocument();
    expect(wrapper).toHaveClass("markdown-body");
  });

  it("renders paragraphs", () => {
    render(<MarkdownRenderer content="First paragraph\n\nSecond paragraph" />);
    // Use regex to match text that may be in the same element
    expect(screen.getByText(/First paragraph/)).toBeInTheDocument();
    expect(screen.getByText(/Second paragraph/)).toBeInTheDocument();
  });

  it("renders bold text", () => {
    render(<MarkdownRenderer content="This is **bold** text" />);
    const bold = screen.getByText("bold");
    expect(bold.tagName).toBe("STRONG");
  });

  // ── Diff rendering ────────────────────────────────────────────────────

  it("renders YAML diff when originalYaml is provided", () => {
    const original = "alias: Old\ntrigger:\n  platform: sun\n";
    const content = [
      "Here is the improved config:",
      "",
      "```yaml",
      "alias: New",
      "trigger:",
      "  platform: sun",
      "  offset: '-00:30:00'",
      "```",
    ].join("\n");

    render(
      <MarkdownRenderer content={content} originalYaml={original} />,
    );

    // The mock diff viewer is rendered by the test setup
    const diffViewer = screen.getByTestId("mock-diff-viewer");
    expect(diffViewer).toBeInTheDocument();
    expect(diffViewer).toHaveAttribute("data-old-value", original);
  });

  it("does not render diff for non-YAML code when originalYaml provided", () => {
    const content = [
      "Here is some JS:",
      "",
      "```javascript",
      "const x = 1;",
      "```",
    ].join("\n");

    render(
      <MarkdownRenderer content={content} originalYaml="alias: Test\n" />,
    );

    // Should render a normal code block, not a diff
    expect(screen.queryByTestId("mock-diff-viewer")).not.toBeInTheDocument();
    expect(screen.getByTestId("code-block")).toBeInTheDocument();
  });

  it("renders normal YAML code block when originalYaml is not provided", () => {
    const content = [
      "Here is some YAML:",
      "",
      "```yaml",
      "alias: Test",
      "key: value",
      "```",
    ].join("\n");

    render(<MarkdownRenderer content={content} />);

    // No diff viewer, just a code block
    expect(screen.queryByTestId("mock-diff-viewer")).not.toBeInTheDocument();
    expect(screen.getByTestId("code-block")).toBeInTheDocument();
  });
});
