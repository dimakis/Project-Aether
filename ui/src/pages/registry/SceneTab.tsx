import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Clapperboard, ChevronRight, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DataViewer } from "@/components/ui/data-viewer";
import { YamlEditor } from "@/components/ui/yaml-editor";
import { YamlDiffViewer } from "@/components/ui/yaml-diff-viewer";
import { cn } from "@/lib/utils";
import {
  useRegistryState,
  setSubmittedEdit,
  clearSubmittedEdit,
} from "@/lib/registry-store";
import yaml from "js-yaml";
import type { Scene } from "@/lib/types";
import { EmptyState } from "./EmptyState";
import { StatPill } from "./StatPill";
import { EntityActionMenu } from "./EntityActionMenu";
import type { EntityAction, OnEntityAction } from "./EntityActionMenu";

interface SceneTabProps {
  scenes: Scene[];
  isLoading: boolean;
  searchQuery: string;
  onSync?: () => void;
  isSyncing?: boolean;
  onEntityAction?: OnEntityAction;
}

function SceneDetail({
  scene,
  onEntityAction,
}: {
  scene: Scene;
  onEntityAction?: OnEntityAction;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const { submittedEdits } = useRegistryState();
  const submittedYaml = submittedEdits[scene.entity_id] ?? null;

  const sceneYaml = useMemo(() => {
    if (!scene.entity_states || Object.keys(scene.entity_states).length === 0) return undefined;
    try {
      return yaml.dump({ entities: scene.entity_states }, { indent: 2, lineWidth: 120, noRefs: true }).trimEnd();
    } catch {
      return undefined;
    }
  }, [scene]);

  const handleAction = (action: EntityAction) => {
    if (action === "edit_yaml") {
      setIsEditing(true);
      return;
    }
    onEntityAction?.(scene.entity_id, "scene", scene.name, sceneYaml, action);
  };

  const handleSubmitEdit = (editedYaml: string) => {
    setIsEditing(false);
    setSubmittedEdit(scene.entity_id, editedYaml);
    onEntityAction?.(scene.entity_id, "scene", scene.name, sceneYaml, "edit_yaml", editedYaml);
  };

  return (
    <div
      className="mt-4 space-y-3 border-t border-border/50 pt-4"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Action menu row */}
      <div className="flex items-start justify-end">
        <EntityActionMenu
          entityId={scene.entity_id}
          entityType="scene"
          entityLabel={scene.name}
          onAction={handleAction}
        />
      </div>

      {/* Editable YAML, diff view, or read-only view */}
      {isEditing && sceneYaml ? (
        <div className="overflow-hidden rounded-lg border border-border/50">
          <YamlEditor
            originalYaml={sceneYaml}
            isEditing={true}
            onSubmitEdit={handleSubmitEdit}
            onCancelEdit={() => setIsEditing(false)}
            collapsible
            maxHeight={300}
          />
        </div>
      ) : submittedYaml && sceneYaml ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-medium text-violet-400">
              Submitted edit — awaiting Architect review
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 gap-1 text-[10px]"
              onClick={() => clearSubmittedEdit(scene.entity_id)}
            >
              <X className="h-3 w-3" />
              Dismiss
            </Button>
          </div>
          <YamlDiffViewer
            originalYaml={sceneYaml}
            suggestedYaml={submittedYaml}
            originalTitle="Original"
            suggestedTitle="Your Edit"
            maxHeight={300}
          />
        </div>
      ) : scene.entity_states && Object.keys(scene.entity_states).length > 0 ? (
        <div>
          <h4 className="mb-2 text-xs font-medium text-muted-foreground">Entity States</h4>
          <DataViewer data={scene.entity_states} defaultMode="yaml" collapsible maxHeight={300} />
        </div>
      ) : (
        <p className="text-[10px] text-muted-foreground">Entity states not available (MCP gap)</p>
      )}
    </div>
  );
}

export function SceneTab({
  scenes,
  isLoading,
  searchQuery,
  onSync,
  isSyncing,
  onEntityAction,
}: SceneTabProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let result = scenes;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.entity_id.toLowerCase().includes(q),
      );
    }
    return [...result].sort((a, b) => a.name.localeCompare(b.name));
  }, [scenes, searchQuery]);

  if (isLoading)
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );

  if (filtered.length === 0) return <EmptyState type="scenes" onSync={onSync} isSyncing={isSyncing} />;

  return (
    <div>
      {/* Stats row */}
      <div className="mb-4 flex gap-3">
        <StatPill label="Total" value={scenes.length} color="text-primary" />
      </div>

      {searchQuery && filtered.length !== scenes.length && (
        <p className="mb-2 text-xs text-muted-foreground">
          Showing {filtered.length} of {scenes.length}
        </p>
      )}

      <div className="space-y-2">
      {filtered.map((scene) => (
        <Card
          key={scene.id}
          className={cn(
            "cursor-pointer transition-all hover:shadow-md",
            expandedId === scene.id && "ring-1 ring-primary/30",
          )}
          onClick={() =>
            setExpandedId(expandedId === scene.id ? null : scene.id)
          }
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10 text-purple-400">
                <Clapperboard className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{scene.name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {scene.entity_id}
                </p>
              </div>
              <ChevronRight
                className={cn(
                  "h-3.5 w-3.5 text-muted-foreground transition-transform",
                  expandedId === scene.id && "rotate-90",
                )}
              />
            </div>

            <AnimatePresence>
              {expandedId === scene.id && (
                <motion.div
                  data-testid="expand-motion"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <SceneDetail scene={scene} onEntityAction={onEntityAction} />
                </motion.div>
              )}
            </AnimatePresence>
          </CardContent>
        </Card>
      ))}
      </div>
    </div>
  );
}
