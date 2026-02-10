import { useState, useMemo } from "react";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";
import { Columns2, Rows2, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface YamlDiffViewerProps {
  /** Original YAML (before review) */
  originalYaml: string;
  /** Suggested YAML (after review) */
  suggestedYaml: string;
  /** Max height with scroll */
  maxHeight?: number;
  /** Title for the original pane */
  originalTitle?: string;
  /** Title for the suggested pane */
  suggestedTitle?: string;
  /** Additional class names */
  className?: string;
}

export function YamlDiffViewer({
  originalYaml,
  suggestedYaml,
  maxHeight = 500,
  originalTitle = "Original",
  suggestedTitle = "Suggested",
  className,
}: YamlDiffViewerProps) {
  const [splitView, setSplitView] = useState(true);
  const [copied, setCopied] = useState(false);

  const changeCount = useMemo(() => {
    const origLines = originalYaml.split("\n");
    const suggLines = suggestedYaml.split("\n");
    let changes = 0;
    const maxLen = Math.max(origLines.length, suggLines.length);
    for (let i = 0; i < maxLen; i++) {
      if (origLines[i] !== suggLines[i]) changes++;
    }
    return changes;
  }, [originalYaml, suggestedYaml]);

  const handleCopySuggested = async () => {
    await navigator.clipboard.writeText(suggestedYaml);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn("rounded-lg border border-border overflow-hidden", className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-border bg-muted/30 px-3 py-2">
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-muted-foreground">
            {changeCount} line{changeCount !== 1 ? "s" : ""} changed
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSplitView(!splitView)}
            className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            title={splitView ? "Switch to unified view" : "Switch to split view"}
          >
            {splitView ? (
              <Rows2 className="h-3.5 w-3.5" />
            ) : (
              <Columns2 className="h-3.5 w-3.5" />
            )}
            {splitView ? "Unified" : "Split"}
          </button>
          <button
            onClick={handleCopySuggested}
            className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            title="Copy suggested YAML"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
            Copy
          </button>
        </div>
      </div>

      {/* Diff viewer */}
      <div
        className="overflow-auto [&_.diff-viewer]:!bg-transparent"
        style={{ maxHeight }}
      >
        <ReactDiffViewer
          oldValue={originalYaml}
          newValue={suggestedYaml}
          splitView={splitView}
          compareMethod={DiffMethod.LINES}
          leftTitle={originalTitle}
          rightTitle={suggestedTitle}
          useDarkTheme={true}
          styles={{
            variables: {
              dark: {
                diffViewerBackground: "transparent",
                addedBackground: "rgba(34, 197, 94, 0.08)",
                addedColor: "#86efac",
                removedBackground: "rgba(239, 68, 68, 0.08)",
                removedColor: "#fca5a5",
                wordAddedBackground: "rgba(34, 197, 94, 0.2)",
                wordRemovedBackground: "rgba(239, 68, 68, 0.2)",
                addedGutterBackground: "rgba(34, 197, 94, 0.15)",
                removedGutterBackground: "rgba(239, 68, 68, 0.15)",
                gutterBackground: "transparent",
                gutterBackgroundDark: "transparent",
                codeFoldBackground: "rgba(255, 255, 255, 0.03)",
                codeFoldGutterBackground: "rgba(255, 255, 255, 0.03)",
                codeFoldContentColor: "rgba(255, 255, 255, 0.4)",
                emptyLineBackground: "transparent",
              },
            },
            contentText: {
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
              fontSize: "12px",
              lineHeight: "1.6",
            },
          }}
        />
      </div>
    </div>
  );
}
