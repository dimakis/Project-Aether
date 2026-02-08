import { useState, useCallback, type ReactNode } from "react";
import ShikiHighlighter from "react-shiki";
import { Check, Copy, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

// Supported languages for our domain
const LANG_LABELS: Record<string, string> = {
  yaml: "YAML",
  yml: "YAML",
  json: "JSON",
  python: "Python",
  py: "Python",
  typescript: "TypeScript",
  ts: "TypeScript",
  javascript: "JavaScript",
  js: "JavaScript",
  bash: "Bash",
  sh: "Shell",
  shell: "Shell",
  sql: "SQL",
  markdown: "Markdown",
  md: "Markdown",
  text: "Text",
  plaintext: "Text",
};

/** Optional action button rendered below the code block. */
export interface CodeBlockAction {
  label: string;
  icon?: ReactNode;
  /** Called with the full code content. */
  onClick: (fullCode: string) => void;
}

interface CodeBlockProps {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
  collapsible?: boolean;
  maxHeight?: number;
  className?: string;
  /** Action button rendered below the code block. */
  action?: CodeBlockAction;
}

/** Height (px) used when the code block is in its collapsed state. */
const COLLAPSED_HEIGHT = 240;

export function CodeBlock({
  code,
  language = "text",
  showLineNumbers = false,
  collapsible = false,
  maxHeight,
  className,
  action,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const lineCount = code.split("\n").length;
  const canCollapse = collapsible && lineCount > 25;
  const [collapsed, setCollapsed] = useState(canCollapse);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  const langLabel = LANG_LABELS[language] ?? language;

  // When collapsed, constrain height via CSS — never truncate the actual code.
  const effectiveMaxHeight = collapsed ? COLLAPSED_HEIGHT : maxHeight;

  return (
    <div>
      <div className={cn("group relative rounded-lg border border-border/50 bg-[#0d1117] overflow-hidden", className)}>
        {/* Header bar */}
        <div className="flex items-center justify-between border-b border-border/30 px-3 py-1.5">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
              {langLabel}
            </span>
            {lineCount > 1 && (
              <span className="text-[10px] text-muted-foreground/40">
                {lineCount} lines
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {canCollapse && (
              <button
                onClick={() => setCollapsed(!collapsed)}
                className="rounded p-1 text-muted-foreground/50 transition-colors hover:bg-white/5 hover:text-muted-foreground"
                title={collapsed ? "Expand" : "Collapse"}
              >
                {collapsed ? (
                  <ChevronDown className="h-3.5 w-3.5" />
                ) : (
                  <ChevronUp className="h-3.5 w-3.5" />
                )}
              </button>
            )}
            <button
              onClick={handleCopy}
              className="rounded p-1 text-muted-foreground/50 transition-colors hover:bg-white/5 hover:text-muted-foreground"
              title="Copy code"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-success" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
        </div>

        {/* Code content — full code is always rendered; height is constrained via CSS */}
        <div
          className={cn("overflow-auto", showLineNumbers && "code-with-lines")}
          style={effectiveMaxHeight ? { maxHeight: effectiveMaxHeight } : undefined}
        >
          <ShikiHighlighter
            language={language}
            theme="github-dark"
            showLanguage={false}
            addDefaultStyles={false}
          >
            {code}
          </ShikiHighlighter>
        </div>
      </div>

      {/* Action button */}
      {action && (
        <button
          onClick={() => action.onClick(code)}
          className="mt-1 flex items-center gap-1.5 rounded-md border border-border/50 bg-card px-2.5 py-1.5 text-[11px] font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary"
        >
          {action.icon}
          {action.label}
        </button>
      )}
    </div>
  );
}

/** Inline code component for use in markdown */
export function InlineCode({ children }: { children: ReactNode }) {
  return (
    <code className="rounded-md bg-muted/80 px-1.5 py-0.5 text-[0.85em] font-mono text-primary/90">
      {children}
    </code>
  );
}
