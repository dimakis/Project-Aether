import { useState, useMemo } from "react";
import { Clapperboard, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DataViewer } from "@/components/ui/data-viewer";
import { cn } from "@/lib/utils";
import type { Scene } from "@/lib/types";
import { EmptyState } from "./EmptyState";
import { StatPill } from "./StatPill";

interface SceneTabProps {
  scenes: Scene[];
  isLoading: boolean;
  searchQuery: string;
}

export function SceneTab({
  scenes,
  isLoading,
  searchQuery,
}: SceneTabProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!searchQuery) return scenes;
    const q = searchQuery.toLowerCase();
    return scenes.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.entity_id.toLowerCase().includes(q),
    );
  }, [scenes, searchQuery]);

  if (isLoading)
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );

  if (filtered.length === 0) return <EmptyState type="scenes" />;

  return (
    <div>
      {/* Stats row */}
      <div className="mb-4 flex gap-3">
        <StatPill label="Total" value={scenes.length} color="text-primary" />
      </div>

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

            {expandedId === scene.id && (
              <div
                className="mt-4 space-y-3 border-t border-border/50 pt-4"
                onClick={(e) => e.stopPropagation()}
              >
                {scene.entity_states &&
                Object.keys(scene.entity_states).length > 0 ? (
                  <div>
                    <h4 className="mb-2 text-xs font-medium text-muted-foreground">
                      Entity States
                    </h4>
                    <DataViewer
                      data={scene.entity_states}
                      defaultMode="yaml"
                      collapsible
                      maxHeight={300}
                    />
                  </div>
                ) : (
                  <p className="text-[10px] text-muted-foreground">
                    Entity states not available (MCP gap)
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
      </div>
    </div>
  );
}
