/**
 * YamlEditor — a view/edit toggle for YAML configuration.
 *
 * In view mode, renders the read-only YamlViewer (CodeBlock).
 * In edit mode, renders a textarea with live YAML syntax validation,
 * Cancel, and "Send to Architect for Review" action buttons.
 */

import { useState, useMemo, useEffect } from "react";
import { CheckCircle2, AlertCircle, Send, X } from "lucide-react";
import yaml from "js-yaml";
import { Button } from "./button";
import { CodeBlock } from "./code-block";
import { cn } from "@/lib/utils";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface YamlEditorProps {
  /** The original (read-only) YAML string */
  originalYaml: string;
  /** Whether the editor is in edit mode */
  isEditing: boolean;
  /** Called with the edited YAML when the user submits */
  onSubmitEdit: (editedYaml: string) => void;
  /** Called when the user cancels editing */
  onCancelEdit: () => void;
  /** Max height for the code block / textarea */
  maxHeight?: number;
  /** Whether the code block is collapsible (view mode only) */
  collapsible?: boolean;
  /** Label for the submit button (default: "Save Changes") */
  submitLabel?: string;
  /** Whether the submit is in progress */
  isSaving?: boolean;
  /** Additional class names */
  className?: string;
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function validateYaml(content: string): { valid: boolean; error?: string } {
  try {
    yaml.load(content);
    return { valid: true };
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Invalid YAML";
    return { valid: false, error: msg };
  }
}

// ─── Component ──────────────────────────────────────────────────────────────

export function YamlEditor({
  originalYaml,
  isEditing,
  onSubmitEdit,
  onCancelEdit,
  maxHeight = 400,
  collapsible = false,
  submitLabel = "Save Changes",
  isSaving = false,
  className,
}: YamlEditorProps) {
  const [editedContent, setEditedContent] = useState(originalYaml);

  // Reset editor content when entering edit mode or when the original changes
  useEffect(() => {
    setEditedContent(originalYaml);
  }, [originalYaml, isEditing]);

  const validation = useMemo(
    () => validateYaml(editedContent),
    [editedContent],
  );

  const isUnchanged = editedContent === originalYaml;
  const canSubmit = validation.valid && !isUnchanged;

  // ─── View mode ──────────────────────────────────────────────────────────

  if (!isEditing) {
    return (
      <CodeBlock
        code={originalYaml}
        language="yaml"
        collapsible={collapsible}
        maxHeight={maxHeight}
        className={className}
      />
    );
  }

  // ─── Edit mode ──────────────────────────────────────────────────────────

  return (
    <div className={cn("space-y-2", className)}>
      {/* Textarea */}
      <textarea
        value={editedContent}
        onChange={(e) => setEditedContent(e.target.value)}
        className={cn(
          "w-full rounded-lg border bg-muted/30 p-3 font-mono text-xs leading-relaxed",
          "resize-y focus:outline-none focus:ring-1",
          validation.valid
            ? "border-border focus:ring-primary/30"
            : "border-destructive/50 focus:ring-destructive/30",
        )}
        style={{ maxHeight, minHeight: 120 }}
        spellCheck={false}
      />

      {/* Validation indicator + actions */}
      <div className="flex items-center justify-between gap-2">
        {/* Validation status */}
        <div className="flex items-center gap-1.5 text-[10px]">
          {validation.valid ? (
            <>
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              <span className="text-emerald-400">Valid YAML</span>
            </>
          ) : (
            <>
              <AlertCircle className="h-3 w-3 text-destructive" />
              <span className="text-destructive">Invalid YAML</span>
            </>
          )}
          {isUnchanged && validation.valid && (
            <span className="ml-2 text-muted-foreground">No changes</span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={onCancelEdit}
            className="h-7 gap-1.5 text-xs"
          >
            <X className="h-3 w-3" />
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => onSubmitEdit(editedContent)}
            disabled={!canSubmit || isSaving}
            className="h-7 gap-1.5 text-xs"
          >
            {isSaving ? (
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : (
              <Send className="h-3 w-3" />
            )}
            {submitLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
