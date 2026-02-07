import { useState, useCallback, useMemo } from "react";
import { Check, Copy, FileJson, FileCode } from "lucide-react";
import yaml from "js-yaml";
import { CodeBlock } from "./code-block";
import { cn } from "@/lib/utils";

type ViewMode = "json" | "yaml";

interface DataViewerProps {
  /** The data object to display */
  data: Record<string, unknown> | unknown[];
  /** Default view mode */
  defaultMode?: ViewMode;
  /** Allow toggling between JSON and YAML */
  allowToggle?: boolean;
  /** Whether the code block should be collapsible */
  collapsible?: boolean;
  /** Max height for scroll */
  maxHeight?: number;
  /** Additional class names */
  className?: string;
}

export function DataViewer({
  data,
  defaultMode = "yaml",
  allowToggle = true,
  collapsible = false,
  maxHeight,
  className,
}: DataViewerProps) {
  const [mode, setMode] = useState<ViewMode>(defaultMode);

  const formatted = useMemo(() => {
    try {
      if (mode === "yaml") {
        return yaml.dump(data, {
          indent: 2,
          lineWidth: 120,
          noRefs: true,
          sortKeys: false,
        }).trimEnd();
      }
      return JSON.stringify(data, null, 2);
    } catch {
      return JSON.stringify(data, null, 2);
    }
  }, [data, mode]);

  return (
    <div className={cn("space-y-2", className)}>
      {allowToggle && (
        <div className="flex items-center gap-1">
          <button
            onClick={() => setMode("yaml")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              mode === "yaml"
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            <FileCode className="h-3 w-3" />
            YAML
          </button>
          <button
            onClick={() => setMode("json")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              mode === "json"
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            <FileJson className="h-3 w-3" />
            JSON
          </button>
        </div>
      )}
      <CodeBlock
        code={formatted}
        language={mode}
        collapsible={collapsible}
        maxHeight={maxHeight}
      />
    </div>
  );
}

/** Simple YAML viewer without toggle, for proposals / read-only views */
interface YamlViewerProps {
  content: string;
  collapsible?: boolean;
  maxHeight?: number;
  className?: string;
}

export function YamlViewer({
  content,
  collapsible = false,
  maxHeight,
  className,
}: YamlViewerProps) {
  return (
    <CodeBlock
      code={content}
      language="yaml"
      collapsible={collapsible}
      maxHeight={maxHeight}
      className={className}
    />
  );
}
