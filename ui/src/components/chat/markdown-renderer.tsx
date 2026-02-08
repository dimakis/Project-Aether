import { useMemo, type ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { isInlineCode } from "react-shiki";
import { FileCheck } from "lucide-react";
import { CodeBlock, InlineCode } from "@/components/ui/code-block";
import { cn } from "@/lib/utils";

// ─── JSON auto-detection ─────────────────────────────────────────────────────

/** Regex that splits content on existing fenced code blocks so we never double-wrap. */
const FENCE_SPLIT = /(```[\s\S]*?```)/g;

/**
 * Try to parse `text` as JSON. Returns the parsed value if it is a non-trivial
 * object or array (i.e. not a bare string/number/boolean/null), otherwise null.
 */
function tryParseJson(text: string): object | unknown[] | null {
  try {
    const parsed: unknown = JSON.parse(text);
    if (parsed !== null && typeof parsed === "object") {
      return parsed as object | unknown[];
    }
  } catch {
    /* not valid JSON */
  }
  return null;
}

/**
 * Wrap a JSON value in a fenced code block with pretty-printing.
 */
function wrapJson(value: object | unknown[]): string {
  return "```json\n" + JSON.stringify(value, null, 2) + "\n```";
}

/**
 * Within a single *unfenced* text segment, find standalone multi-line JSON
 * blocks (lines starting with `{` or `[` through to the matching close brace)
 * and wrap them in ```json fences.
 *
 * Uses a simple brace/bracket depth counter so it works on prettified and
 * minified JSON alike, without back-tracking regexes.
 */
function wrapJsonBlocksInSegment(segment: string): string {
  const lines = segment.split("\n");
  const result: string[] = [];
  let jsonLines: string[] | null = null;
  let depth = 0;
  let openChar: "{" | "[" | null = null;
  const closeFor = { "{": "}", "[": "]" } as const;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trimStart();

    // Start accumulating if a line begins with { or [
    if (jsonLines === null && (trimmed.startsWith("{") || trimmed.startsWith("["))) {
      openChar = trimmed[0] as "{" | "[";
      jsonLines = [line];
      depth = 0;

      // Count depth across the whole line
      for (const ch of line) {
        if (ch === openChar) depth++;
        else if (ch === closeFor[openChar]) depth--;
      }

      if (depth <= 0) {
        // Single-line JSON candidate
        const candidate = jsonLines.join("\n");
        const parsed = tryParseJson(candidate.trim());
        if (parsed) {
          result.push(wrapJson(parsed));
        } else {
          result.push(candidate);
        }
        jsonLines = null;
        depth = 0;
        openChar = null;
      }
      continue;
    }

    // Accumulating a JSON block
    if (jsonLines !== null && openChar !== null) {
      jsonLines.push(line);
      for (const ch of line) {
        if (ch === openChar) depth++;
        else if (ch === closeFor[openChar]) depth--;
      }

      if (depth <= 0) {
        const candidate = jsonLines.join("\n");
        const parsed = tryParseJson(candidate.trim());
        if (parsed) {
          result.push(wrapJson(parsed));
        } else {
          // Not valid JSON — flush accumulated lines as-is
          result.push(candidate);
        }
        jsonLines = null;
        depth = 0;
        openChar = null;
      }
      continue;
    }

    // Normal line
    result.push(line);
  }

  // Flush any unterminated accumulation
  if (jsonLines !== null) {
    result.push(jsonLines.join("\n"));
  }

  return result.join("\n");
}

/**
 * Pre-process content so that raw (unfenced) JSON blocks are wrapped in
 * ```json fences before react-markdown sees them.
 *
 * Already-fenced code blocks are left untouched.
 */
function preprocessContent(content: string): string {
  // Fast path: nothing that looks like JSON
  if (!content.includes("{") && !content.includes("[")) return content;

  // Split on existing code fences so we never modify them
  const parts = content.split(FENCE_SPLIT);

  return parts
    .map((part) => {
      // Existing fenced block — pass through unchanged
      if (part.startsWith("```")) return part;
      return wrapJsonBlocksInSegment(part);
    })
    .join("");
}

// ─── Component ───────────────────────────────────────────────────────────────

interface MarkdownRendererProps {
  content: string;
  className?: string;
  /** When provided, YAML code blocks get a "Create Proposal" button */
  onCreateProposal?: (yamlContent: string) => void;
}

/** Custom markdown renderer that routes code blocks to shiki CodeBlock component */
export function MarkdownRenderer({ content, className, onCreateProposal }: MarkdownRendererProps) {
  const components = useMemo(() => ({
    // Route fenced code blocks through our shiki CodeBlock
    // Uses react-shiki's isInlineCode helper to distinguish inline vs fenced
    code(props: ComponentPropsWithoutRef<"code"> & { node?: unknown }) {
      const { children, className: codeClassName, node, ...rest } = props;
      const match = /language-(\w+)/.exec(codeClassName || "");
      const isInline = node ? isInlineCode(node as Parameters<typeof isInlineCode>[0]) : !match;

      if (!isInline) {
        const lang = match ? match[1] : "text";
        const codeStr = String(children).replace(/\n$/, "");
        const isYaml = lang === "yaml" || lang === "yml";

        return (
          <div>
            <CodeBlock
              code={codeStr}
              language={lang}
              collapsible={codeStr.split("\n").length > 30}
              action={
                isYaml && onCreateProposal
                  ? { label: "Create Proposal", icon: <FileCheck className="h-3 w-3" />, onClick: onCreateProposal }
                  : undefined
              }
            />
          </div>
        );
      }

      // Inline code
      return <InlineCode>{children}</InlineCode>;
    },

    // Override <pre> to avoid double-wrapping when CodeBlock is used
    pre(props: ComponentPropsWithoutRef<"pre">) {
      const { children } = props;
      // If children is our CodeBlock, don't wrap in <pre>
      return <>{children}</>;
    },

    // Enhanced table styling
    table(props: ComponentPropsWithoutRef<"table">) {
      return (
        <div className="my-4 overflow-x-auto rounded-lg border border-border/50">
          <table className="w-full text-sm" {...props} />
        </div>
      );
    },
    thead(props: ComponentPropsWithoutRef<"thead">) {
      return <thead className="border-b border-border/50 bg-muted/30" {...props} />;
    },
    th(props: ComponentPropsWithoutRef<"th">) {
      return (
        <th
          className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground"
          {...props}
        />
      );
    },
    td(props: ComponentPropsWithoutRef<"td">) {
      return (
        <td
          className="border-t border-border/30 px-4 py-2 text-sm"
          {...props}
        />
      );
    },

    // Enhanced blockquote
    blockquote(props: ComponentPropsWithoutRef<"blockquote">) {
      return (
        <blockquote
          className="my-3 border-l-2 border-primary/40 pl-4 text-muted-foreground italic"
          {...props}
        />
      );
    },

    // Enhanced links
    a(props: ComponentPropsWithoutRef<"a">) {
      return (
        <a
          className="text-primary underline decoration-primary/30 underline-offset-2 transition-colors hover:decoration-primary"
          target="_blank"
          rel="noopener noreferrer"
          {...props}
        />
      );
    },

    // Enhanced headings
    h1(props: ComponentPropsWithoutRef<"h1">) {
      return <h1 className="mb-4 mt-6 text-xl font-bold first:mt-0" {...props} />;
    },
    h2(props: ComponentPropsWithoutRef<"h2">) {
      return <h2 className="mb-3 mt-5 text-lg font-semibold first:mt-0" {...props} />;
    },
    h3(props: ComponentPropsWithoutRef<"h3">) {
      return <h3 className="mb-2 mt-4 text-base font-semibold first:mt-0" {...props} />;
    },

    // Enhanced lists
    ul(props: ComponentPropsWithoutRef<"ul">) {
      return <ul className="my-2 ml-1 list-none space-y-1" {...props} />;
    },
    ol(props: ComponentPropsWithoutRef<"ol">) {
      return <ol className="my-2 ml-1 list-decimal space-y-1 pl-4" {...props} />;
    },
    li(props: ComponentPropsWithoutRef<"li">) {
      const { children, ...rest } = props;
      return (
        <li className="relative pl-5 text-sm leading-relaxed" {...rest}>
          <span className="absolute left-0 top-[0.45em] h-1.5 w-1.5 rounded-full bg-primary/40" />
          {children}
        </li>
      );
    },

    // Paragraphs
    p(props: ComponentPropsWithoutRef<"p">) {
      return <p className="my-2 text-sm leading-relaxed first:mt-0 last:mb-0" {...props} />;
    },

    // Horizontal rule
    hr() {
      return <hr className="my-6 border-border/50" />;
    },

    // Strong / emphasis
    strong(props: ComponentPropsWithoutRef<"strong">) {
      return <strong className="font-semibold text-foreground" {...props} />;
    },
  }), [onCreateProposal]);

  const processed = useMemo(() => preprocessContent(content), [content]);

  return (
    <div className={cn("markdown-body", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={components}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}
