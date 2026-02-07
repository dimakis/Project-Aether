import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  Loader2,
  Check,
  ArrowUpCircle,
  RotateCcw,
  Trash2,
  FileText,
  Sparkles,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  useAgentPromptVersions,
  useCreatePromptVersion,
  usePromotePromptVersion,
  useRollbackPrompt,
  useDeletePromptVersion,
  useGeneratePrompt,
} from "@/api/hooks";
import type { PromptVersion, VersionStatusValue } from "@/lib/types";
import { VERSION_STATUS_COLORS } from "./constants";

// ─── Prompt Tab ──────────────────────────────────────────────────────────────

export function PromptTab({ agentName }: { agentName: string }) {
  const { data: versions, isLoading } = useAgentPromptVersions(agentName);
  const [showCreate, setShowCreate] = useState(false);
  const [promptTemplate, setPromptTemplate] = useState("");
  const [changeSummary, setChangeSummary] = useState("");
  const [showGenerate, setShowGenerate] = useState(false);
  const [genInput, setGenInput] = useState("");

  const createMutation = useCreatePromptVersion();
  const promoteMutation = usePromotePromptVersion();
  const rollbackMutation = useRollbackPrompt();
  const deleteMutation = useDeletePromptVersion();
  const generateMutation = useGeneratePrompt();

  const handleCreate = () => {
    if (!promptTemplate.trim()) return;
    createMutation.mutate(
      {
        name: agentName,
        data: {
          prompt_template: promptTemplate,
          change_summary: changeSummary || undefined,
        },
      },
      {
        onSuccess: () => {
          setShowCreate(false);
          setPromptTemplate("");
          setChangeSummary("");
        },
      },
    );
  };

  const handleGenerate = () => {
    generateMutation.mutate(
      { name: agentName, userInput: genInput || undefined },
      {
        onSuccess: (data) => {
          setPromptTemplate(data.generated_prompt);
          setShowGenerate(false);
          setGenInput("");
          // Ensure the create form is open so user can see the result
          setShowCreate(true);
        },
      },
    );
  };

  const hasDraft = versions?.some((v) => v.status === "draft");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Prompt Versions</h3>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => rollbackMutation.mutate(agentName)}
            disabled={rollbackMutation.isPending || hasDraft}
          >
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
            Rollback
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowGenerate(!showGenerate)}
            disabled={hasDraft}
          >
            <Sparkles className="mr-1.5 h-3.5 w-3.5" />
            Generate with AI
          </Button>
          <Button
            size="sm"
            onClick={() => setShowCreate(true)}
            disabled={showCreate || hasDraft}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            New Version
          </Button>
        </div>
      </div>

      {/* AI Generate form */}
      <AnimatePresence>
        {showGenerate && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <Card className="border-purple-500/30 bg-purple-500/5">
              <CardContent className="space-y-3 pt-4">
                <div className="flex items-center gap-2 text-sm font-medium text-purple-400">
                  <Sparkles className="h-4 w-4" />
                  AI Prompt Generation
                </div>
                <p className="text-xs text-muted-foreground">
                  The AI will generate a system prompt based on this agent's role,
                  tools, and current behavior. Add custom instructions below (optional).
                </p>
                <textarea
                  className="min-h-[80px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  placeholder="Optional: Add specific instructions (e.g. 'Focus on energy optimization', 'Be more concise')"
                  value={genInput}
                  onChange={(e) => setGenInput(e.target.value)}
                />
                {generateMutation.isError && (
                  <p className="text-xs text-destructive">
                    Generation failed. Please try again.
                  </p>
                )}
                <div className="flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setShowGenerate(false);
                      setGenInput("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleGenerate}
                    disabled={generateMutation.isPending}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {generateMutation.isPending ? (
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                    )}
                    Generate
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Create form */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <Card className="border-blue-500/30 bg-blue-500/5">
              <CardContent className="space-y-3 pt-4">
                <textarea
                  className="min-h-[200px] w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="Enter system prompt template..."
                  value={promptTemplate}
                  onChange={(e) => setPromptTemplate(e.target.value)}
                />
                <Input
                  placeholder="Change summary"
                  value={changeSummary}
                  onChange={(e) => setChangeSummary(e.target.value)}
                />
                <div className="flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowCreate(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleCreate}
                    disabled={createMutation.isPending || !promptTemplate.trim()}
                  >
                    {createMutation.isPending && (
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    )}
                    Create Draft
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Version list */}
      {isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-2">
          {versions?.map((v) => (
            <PromptVersionRow
              key={v.id}
              version={v}
              onPromote={() =>
                promoteMutation.mutate({ name: agentName, versionId: v.id })
              }
              onDelete={() =>
                deleteMutation.mutate({ name: agentName, versionId: v.id })
              }
              promotePending={promoteMutation.isPending}
              deletePending={deleteMutation.isPending}
            />
          ))}
          {versions?.length === 0 && (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No prompt versions yet. Create one or seed defaults.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Prompt Version Row ──────────────────────────────────────────────────────

function PromptVersionRow({
  version,
  onPromote,
  onDelete,
  promotePending,
  deletePending,
}: {
  version: PromptVersion;
  onPromote: () => void;
  onDelete: () => void;
  promotePending: boolean;
  deletePending: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-3",
        version.status === "draft" && "border-blue-500/30 bg-blue-500/5",
        version.status === "active" && "border-emerald-500/30 bg-emerald-500/5",
        version.status === "archived" && "border-border",
      )}
    >
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">
              v{version.version_number}
            </span>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] ring-1",
                VERSION_STATUS_COLORS[version.status as VersionStatusValue],
              )}
            >
              {version.status}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {version.prompt_template.length} chars
            </span>
          </div>
          {version.change_summary && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {version.change_summary}
            </p>
          )}
        </div>
        <div className="flex gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setExpanded(!expanded)}
            title="Toggle prompt text"
          >
            <FileText className="h-4 w-4" />
          </Button>
          {version.status === "draft" && (
            <>
              <Button
                size="sm"
                variant="ghost"
                onClick={onPromote}
                disabled={promotePending}
                title="Promote to active"
              >
                <ArrowUpCircle className="h-4 w-4 text-emerald-400" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={onDelete}
                disabled={deletePending}
                title="Delete draft"
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </>
          )}
          {version.status === "active" && (
            <Check className="h-4 w-4 text-emerald-400" />
          )}
        </div>
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <pre className="mt-3 max-h-[300px] overflow-auto rounded-md bg-background/50 p-3 font-mono text-xs leading-relaxed text-muted-foreground">
              {version.prompt_template}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
