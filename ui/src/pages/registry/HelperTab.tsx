import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ToggleLeft,
  Hash,
  Type,
  List,
  Calendar,
  CircleDot,
  Timer,
  ChevronRight,
  Plus,
  Trash2,
  Loader2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DataViewer } from "@/components/ui/data-viewer";
import { cn } from "@/lib/utils";
import type { Helper } from "@/lib/types";
import { useRegistryHelpers, useDeleteHelper } from "@/api/hooks";
import { StatPill } from "./StatPill";
import { CreateHelperForm } from "./CreateHelperForm";

const DOMAIN_META: Record<string, { label: string; icon: typeof ToggleLeft; color: string }> = {
  input_boolean: { label: "Toggle", icon: ToggleLeft, color: "text-green-400 bg-green-500/10" },
  input_number: { label: "Number", icon: Hash, color: "text-blue-400 bg-blue-500/10" },
  input_text: { label: "Text", icon: Type, color: "text-yellow-400 bg-yellow-500/10" },
  input_select: { label: "Dropdown", icon: List, color: "text-purple-400 bg-purple-500/10" },
  input_datetime: { label: "Date/Time", icon: Calendar, color: "text-orange-400 bg-orange-500/10" },
  input_button: { label: "Button", icon: CircleDot, color: "text-red-400 bg-red-500/10" },
  counter: { label: "Counter", icon: Hash, color: "text-cyan-400 bg-cyan-500/10" },
  timer: { label: "Timer", icon: Timer, color: "text-pink-400 bg-pink-500/10" },
};

interface HelperTabProps {
  searchQuery: string;
}

export function HelperTab({ searchQuery }: HelperTabProps) {
  const { data, isLoading } = useRegistryHelpers({ enabled: true });
  const deleteMut = useDeleteHelper();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [filterDomain, setFilterDomain] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const helpers = data?.helpers ?? [];
  const byType = data?.by_type ?? {};

  const domains = useMemo(() => {
    return Object.keys(byType).sort();
  }, [byType]);

  const filtered = useMemo(() => {
    let result = helpers;
    if (filterDomain) {
      result = result.filter((h) => h.domain === filterDomain);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (h) =>
          h.name.toLowerCase().includes(q) ||
          h.entity_id.toLowerCase().includes(q),
      );
    }
    return [...result].sort((a, b) => a.name.localeCompare(b.name));
  }, [helpers, filterDomain, searchQuery]);

  function handleDelete(helper: Helper) {
    const parts = helper.entity_id.split(".");
    if (parts.length < 2) return;
    const domain = parts[0];
    const inputId = parts.slice(1).join(".");
    deleteMut.mutate({ domain, inputId });
    setConfirmDelete(null);
    setExpandedId(null);
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Stats + Create button */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-3">
          <StatPill label="Total" value={helpers.length} color="text-primary" />
          {Object.entries(byType).map(([domain, count]) => {
            const meta = DOMAIN_META[domain];
            return meta ? (
              <StatPill
                key={domain}
                label={meta.label}
                value={count}
                color={meta.color.split(" ")[0]}
              />
            ) : null;
          })}
        </div>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Create Helper
        </Button>
      </div>

      {/* Create form */}
      <AnimatePresence>
        {showCreate && <CreateHelperForm onClose={() => setShowCreate(false)} />}
      </AnimatePresence>

      {/* Domain filter chips */}
      {domains.length > 1 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          <button
            onClick={() => setFilterDomain(null)}
            className={cn(
              "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              filterDomain === null
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground",
            )}
          >
            All
          </button>
          {domains.map((d) => {
            const meta = DOMAIN_META[d];
            return (
              <button
                key={d}
                onClick={() => setFilterDomain(filterDomain === d ? null : d)}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                  filterDomain === d
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:text-foreground",
                )}
              >
                {meta?.label ?? d} ({byType[d]})
              </button>
            );
          })}
        </div>
      )}

      {searchQuery && filtered.length !== helpers.length && (
        <p className="mb-2 text-xs text-muted-foreground">
          Showing {filtered.length} of {helpers.length}
        </p>
      )}

      {helpers.length === 0 && !showCreate ? (
        <Card>
          <CardContent className="flex flex-col items-center py-16">
            <ToggleLeft className="mb-3 h-10 w-10 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              No helpers found. Create one to get started.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => setShowCreate(true)}
            >
              <Plus className="mr-2 h-3.5 w-3.5" />
              Create Helper
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {filtered.map((helper) => {
            const meta = DOMAIN_META[helper.domain] ?? {
              label: helper.domain,
              icon: ToggleLeft,
              color: "text-muted-foreground bg-muted",
            };
            const Icon = meta.icon;

            return (
              <Card
                key={helper.entity_id}
                className={cn(
                  "cursor-pointer transition-all hover:shadow-md",
                  expandedId === helper.entity_id && "ring-1 ring-primary/30",
                )}
                onClick={() =>
                  setExpandedId(expandedId === helper.entity_id ? null : helper.entity_id)
                }
              >
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-lg",
                        meta.color,
                      )}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{helper.name}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {helper.entity_id}
                      </p>
                    </div>
                    <Badge
                      variant="secondary"
                      className="text-[10px]"
                    >
                      {meta.label}
                    </Badge>
                    <span className="text-xs font-mono text-muted-foreground">
                      {helper.state}
                    </span>
                    <ChevronRight
                      className={cn(
                        "h-3.5 w-3.5 text-muted-foreground transition-transform",
                        expandedId === helper.entity_id && "rotate-90",
                      )}
                    />
                  </div>

                  <AnimatePresence>
                    {expandedId === helper.entity_id && (
                      <motion.div
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
                          {Object.keys(helper.attributes).length > 0 && (
                            <div>
                              <h4 className="mb-2 text-xs font-medium text-muted-foreground">
                                Attributes
                              </h4>
                              <DataViewer
                                data={helper.attributes}
                                defaultMode="yaml"
                                collapsible
                                maxHeight={250}
                              />
                            </div>
                          )}

                          <div className="flex justify-end">
                            {confirmDelete === helper.entity_id ? (
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-destructive">
                                  Delete this helper?
                                </span>
                                <Button
                                  variant="destructive"
                                  size="sm"
                                  onClick={() => handleDelete(helper)}
                                  disabled={deleteMut.isPending}
                                >
                                  {deleteMut.isPending ? (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                  ) : (
                                    "Confirm"
                                  )}
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setConfirmDelete(null)}
                                >
                                  Cancel
                                </Button>
                              </div>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:text-destructive"
                                onClick={() => setConfirmDelete(helper.entity_id)}
                              >
                                <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                                Delete
                              </Button>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
