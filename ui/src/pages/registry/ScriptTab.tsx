import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, ChevronRight, Clock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DataViewer } from "@/components/ui/data-viewer";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { Script } from "@/lib/types";
import { EmptyState } from "./EmptyState";
import { StatPill } from "./StatPill";

interface ScriptTabProps {
  scripts: Script[];
  isLoading: boolean;
  searchQuery: string;
  runningCount?: number;
}

type SortKey = "name" | "last_triggered";

export function ScriptTab({
  scripts,
  isLoading,
  searchQuery,
  runningCount,
}: ScriptTabProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("name");

  const filtered = useMemo(() => {
    let result = scripts;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (s) =>
          s.alias.toLowerCase().includes(q) ||
          s.entity_id.toLowerCase().includes(q) ||
          (s.description ?? "").toLowerCase().includes(q),
      );
    }
    return [...result].sort((a, b) => {
      if (sortKey === "name") return a.alias.localeCompare(b.alias);
      return (b.last_triggered ?? "").localeCompare(a.last_triggered ?? "");
    });
  }, [scripts, searchQuery, sortKey]);

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
    <div>
      {/* Stats + Sort row */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-3">
          <StatPill
            label="Running"
            value={runningCount ?? 0}
            color="text-emerald-400"
          />
          <StatPill label="Total" value={scripts.length} color="text-primary" />
        </div>
        <select
          aria-label="Sort"
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as SortKey)}
          className="rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground"
        >
          <option value="name">Name</option>
          <option value="last_triggered">Last Triggered</option>
        </select>
      </div>

      {searchQuery && filtered.length !== scripts.length && (
        <p className="mb-2 text-xs text-muted-foreground">
          Showing {filtered.length} of {scripts.length}
        </p>
      )}

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

            <AnimatePresence>
              {expandedId === script.id && (
                <motion.div
                  data-testid="expand-motion"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
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
