import { useState } from "react";
import {
  Workflow,
  Plus,
  Trash2,
  Loader2,
  Clock,
  Layers,
  Tag,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useWorkflowDefinitions,
  useCreateWorkflowDefinition,
  useDeleteWorkflowDefinition,
} from "@/api/hooks";
import type { WorkflowDefinition } from "@/api/client/workflows";
import { CreateWorkflowDialog } from "./CreateWorkflowDialog";

export function WorkflowDefinitionsPage() {
  const { data, isLoading } = useWorkflowDefinitions();
  const deleteMut = useDeleteWorkflowDefinition();
  const [createOpen, setCreateOpen] = useState(false);

  const definitions = data?.definitions ?? [];

  const statusColor = (status: string) => {
    switch (status) {
      case "active":
        return "text-emerald-400 border-emerald-400/30";
      case "draft":
        return "text-amber-400 border-amber-400/30";
      case "archived":
        return "text-red-400 border-red-400/30";
      default:
        return "text-muted-foreground";
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Workflow className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">
              Workflow Definitions
            </h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage dynamic workflow definitions for agent orchestration.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} size="sm">
          <Plus className="mr-1 h-3 w-3" />
          Create Workflow
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : definitions.length === 0 ? (
        <Card className="flex flex-col items-center justify-center py-16 text-center">
          <Workflow className="mb-4 h-12 w-12 text-muted-foreground/20" />
          <p className="text-muted-foreground">No workflow definitions yet</p>
          <p className="mt-1 text-xs text-muted-foreground/60">
            Create one to define custom agent orchestration flows
          </p>
          <Button
            onClick={() => setCreateOpen(true)}
            variant="outline"
            size="sm"
            className="mt-4"
          >
            <Plus className="mr-1 h-3 w-3" />
            Create First Workflow
          </Button>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {definitions.map((def) => (
            <WorkflowCard
              key={def.id}
              definition={def}
              statusColor={statusColor}
              onDelete={() => deleteMut.mutate(def.id)}
              isDeleting={deleteMut.isPending}
            />
          ))}
        </div>
      )}

      <CreateWorkflowDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}

function WorkflowCard({
  definition,
  statusColor,
  onDelete,
  isDeleting,
}: {
  definition: WorkflowDefinition;
  statusColor: (s: string) => string;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const nodeCount =
    Array.isArray(definition.config?.nodes) ? definition.config.nodes.length : 0;
  const edgeCount =
    Array.isArray(definition.config?.edges) ? definition.config.edges.length : 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base">{definition.name}</CardTitle>
            {definition.description && (
              <p className="mt-1 text-xs text-muted-foreground">
                {definition.description}
              </p>
            )}
          </div>
          <Badge
            variant="outline"
            className={`text-[10px] ${statusColor(definition.status)}`}
          >
            {definition.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Layers className="h-3 w-3" />
            <span>
              {nodeCount} node{nodeCount !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Workflow className="h-3 w-3" />
            <span>
              {edgeCount} edge{edgeCount !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Tag className="h-3 w-3" />
            <span>v{definition.version}</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{new Date(definition.updated_at).toLocaleDateString()}</span>
          </div>
        </div>

        {definition.intent_patterns.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {definition.intent_patterns.slice(0, 5).map((pattern) => (
              <Badge
                key={pattern}
                variant="outline"
                className="text-[9px] font-normal"
              >
                {pattern}
              </Badge>
            ))}
            {definition.intent_patterns.length > 5 && (
              <Badge variant="outline" className="text-[9px] font-normal">
                +{definition.intent_patterns.length - 5}
              </Badge>
            )}
          </div>
        )}

        <div className="flex items-center justify-between border-t border-border/50 pt-2">
          <span className="text-[10px] text-muted-foreground/60">
            {definition.state_type}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDelete}
            disabled={isDeleting}
            className="h-7 text-xs text-red-400 hover:text-red-300"
          >
            <Trash2 className="mr-1 h-3 w-3" />
            Archive
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default WorkflowDefinitionsPage;
