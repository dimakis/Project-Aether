import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useCreateWorkflowDefinition } from "@/api/hooks";

export interface CreateWorkflowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateWorkflowDialog({
  open,
  onOpenChange,
}: CreateWorkflowDialogProps) {
  const createMut = useCreateWorkflowDefinition();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [stateType, setStateType] = useState("ConversationState");
  const [nodesJson, setNodesJson] = useState('[\n  { "name": "start_node", "func": "route_request" }\n]');
  const [edgesJson, setEdgesJson] = useState("[]");
  const [intentPatterns, setIntentPatterns] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const handleSubmit = () => {
    setError(null);
    let nodes, edges;
    try {
      nodes = JSON.parse(nodesJson);
    } catch {
      setError("Invalid JSON in nodes field");
      return;
    }
    try {
      edges = JSON.parse(edgesJson);
    } catch {
      setError("Invalid JSON in edges field");
      return;
    }

    const patterns = intentPatterns
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    createMut.mutate(
      {
        name,
        description,
        state_type: stateType,
        nodes,
        edges,
        intent_patterns: patterns,
      },
      {
        onSuccess: () => {
          onOpenChange(false);
          setName("");
          setDescription("");
          setNodesJson('[\n  { "name": "start_node", "func": "route_request" }\n]');
          setEdgesJson("[]");
          setIntentPatterns("");
        },
        onError: (err: unknown) => {
          const msg =
            err instanceof Error ? err.message : "Failed to create workflow";
          setError(msg);
        },
      },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <Card className="w-full max-w-lg p-6">
        <h2 className="mb-4 text-lg font-bold">Create Workflow Definition</h2>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-custom-workflow"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Description
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A workflow for..."
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              State Type
            </label>
            <select
              value={stateType}
              onChange={(e) => setStateType(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="ConversationState">ConversationState</option>
              <option value="AnalysisState">AnalysisState</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Nodes (JSON array) *
            </label>
            <textarea
              value={nodesJson}
              onChange={(e) => setNodesJson(e.target.value)}
              rows={4}
              className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Edges (JSON array)
            </label>
            <textarea
              value={edgesJson}
              onChange={(e) => setEdgesJson(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Intent Patterns (comma-separated)
            </label>
            <input
              type="text"
              value={intentPatterns}
              onChange={(e) => setIntentPatterns(e.target.value)}
              placeholder="energy_analysis, usage_patterns"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {error && (
            <p className="text-xs text-red-400">{error}</p>
          )}
        </div>

        <div className="mt-5 flex items-center justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={!name.trim() || createMut.isPending}
          >
            {createMut.isPending && (
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            )}
            Create
          </Button>
        </div>
      </Card>
    </div>
  );
}
