import { useState, useMemo } from "react";
import { FileText, ChevronRight, Clock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DataViewer } from "@/components/ui/data-viewer";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { Script } from "@/lib/types";
import { EmptyState } from "./EmptyState";

interface ScriptTabProps {
  scripts: Script[];
  isLoading: boolean;
  searchQuery: string;
}

export function ScriptTab({
  scripts,
  isLoading,
  searchQuery,
}: ScriptTabProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!searchQuery) return scripts;
    const q = searchQuery.toLowerCase();
    return scripts.filter(
      (s) =>
        s.alias.toLowerCase().includes(q) ||
        s.entity_id.toLowerCase().includes(q) ||
        (s.description ?? "").toLowerCase().includes(q),
    );
  }, [scripts, searchQuery]);

  if (isLoading)
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );

  if (filtered.length === 0) return <EmptyState type="scripts" />;

  return (
    <div className="space-y-2">
      {filtered.map((script) => (
        <Card
          key={script.id}
          className={cn(
            "cursor-pointer transition-all hover:shadow-md",
            expandedId === script.id && "ring-1 ring-primary/30",
          )}
          onClick={() =>
            setExpandedId(expandedId === script.id ? null : script.id)
          }
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-lg",
                  script.state === "on"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-muted text-muted-foreground",
                )}
              >
                <FileText className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{script.alias}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {script.entity_id}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {script.state === "on" && (
                  <Badge className="bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20 text-[10px]">
                    Running
                  </Badge>
                )}
                {script.mode && (
                  <Badge variant="secondary" className="text-[10px]">
                    {script.mode}
                  </Badge>
                )}
                <ChevronRight
                  className={cn(
                    "h-3.5 w-3.5 text-muted-foreground transition-transform",
                    expandedId === script.id && "rotate-90",
                  )}
                />
              </div>
            </div>

            {expandedId === script.id && (
              <div
                className="mt-4 space-y-3 border-t border-border/50 pt-4"
                onClick={(e) => e.stopPropagation()}
              >
                {script.description && (
                  <p className="text-xs text-muted-foreground">
                    {script.description}
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  {script.last_triggered && (
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Clock className="h-2.5 w-2.5" />
                      Last: {formatRelativeTime(script.last_triggered)}
                    </span>
                  )}
                </div>
                {script.sequence && script.sequence.length > 0 && (
                  <div>
                    <h4 className="mb-2 text-xs font-medium text-muted-foreground">
                      Sequence
                    </h4>
                    <DataViewer
                      data={script.sequence}
                      defaultMode="yaml"
                      collapsible
                      maxHeight={300}
                    />
                  </div>
                )}
                {script.fields &&
                  Object.keys(script.fields).length > 0 && (
                    <div>
                      <h4 className="mb-2 text-xs font-medium text-muted-foreground">
                        Fields
                      </h4>
                      <DataViewer
                        data={script.fields}
                        defaultMode="yaml"
                        collapsible
                        maxHeight={200}
                      />
                    </div>
                  )}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
