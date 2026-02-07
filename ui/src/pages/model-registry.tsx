import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Star,
  Plus,
  Loader2,
  BarChart3,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Settings2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  useModelSummary,
  useModelRatings,
  useCreateModelRating,
  useModels,
} from "@/api/hooks";
import type { ModelSummaryItem, ModelRatingItem } from "@/api/client";

// ─── Star Rating Component ──────────────────────────────────────────────────

function StarRating({
  value,
  onChange,
  size = "sm",
  readonly = false,
}: {
  value: number;
  onChange?: (v: number) => void;
  size?: "sm" | "md";
  readonly?: boolean;
}) {
  const [hover, setHover] = useState(0);
  const sz = size === "md" ? "h-5 w-5" : "h-3.5 w-3.5";
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={readonly}
          className={cn(
            "transition-colors",
            readonly ? "cursor-default" : "cursor-pointer hover:scale-110",
          )}
          onMouseEnter={() => !readonly && setHover(star)}
          onMouseLeave={() => !readonly && setHover(0)}
          onClick={() => onChange?.(star)}
        >
          <Star
            className={cn(
              sz,
              (hover || value) >= star
                ? "fill-amber-400 text-amber-400"
                : "text-muted-foreground/30",
            )}
          />
        </button>
      ))}
    </div>
  );
}

// ─── Rate Model Dialog ──────────────────────────────────────────────────────

const AGENT_ROLES = [
  "architect",
  "data_scientist",
  "orchestrator",
  "developer",
  "librarian",
];

function RateModelDialog({ onClose }: { onClose: () => void }) {
  const { data: modelsData } = useModels();
  const createMutation = useCreateModelRating();
  const [modelName, setModelName] = useState("");
  const [agentRole, setAgentRole] = useState("architect");
  const [rating, setRating] = useState(0);
  const [notes, setNotes] = useState("");

  const handleSubmit = () => {
    if (!modelName || !rating) return;
    createMutation.mutate(
      {
        model_name: modelName,
        agent_role: agentRole,
        rating,
        notes: notes || null,
        config_snapshot: null,
      },
      { onSuccess: () => onClose() },
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
    >
      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardContent className="space-y-4 pt-4">
          <div className="flex items-center gap-2 text-sm font-medium text-amber-400">
            <Star className="h-4 w-4 fill-amber-400" />
            Rate a Model
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">
                Model
              </label>
              <select
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
              >
                <option value="">Select model...</option>
                {modelsData?.data?.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id} ({m.owned_by})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">
                Agent Role
              </label>
              <select
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                value={agentRole}
                onChange={(e) => setAgentRole(e.target.value)}
              >
                {AGENT_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Rating
            </label>
            <StarRating value={rating} onChange={setRating} size="md" />
          </div>

          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Notes (optional)
            </label>
            <textarea
              className="min-h-[60px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="How well did this model perform for this role?"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSubmit}
              disabled={!modelName || !rating || createMutation.isPending}
            >
              {createMutation.isPending && (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              )}
              Submit Rating
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ─── Expandable Summary Row ─────────────────────────────────────────────────

function SummaryRow({ summary }: { summary: ModelSummaryItem }) {
  const [expanded, setExpanded] = useState(false);
  const { data: ratingsData, isLoading } = useModelRatings(
    expanded ? summary.model_name : undefined,
    expanded ? summary.agent_role : undefined,
  );

  return (
    <div className="rounded-lg border border-border">
      <button
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/50"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{summary.model_name}</span>
            <Badge variant="outline" className="text-[10px] capitalize">
              {summary.agent_role.replace(/_/g, " ")}
            </Badge>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <StarRating value={Math.round(summary.avg_rating)} readonly />
          <span className="text-sm font-medium text-amber-400">
            {summary.avg_rating.toFixed(1)}
          </span>
          <span className="text-xs text-muted-foreground">
            {summary.rating_count} rating{summary.rating_count !== 1 ? "s" : ""}
          </span>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-4 py-3 space-y-2">
              {/* Config snapshot */}
              {summary.latest_config && (
                <div className="mb-3">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-1">
                    <Settings2 className="h-3 w-3" />
                    Latest Config
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(summary.latest_config).map(([k, v]) => (
                      <Badge key={k} variant="secondary" className="text-[10px]">
                        {k}: {String(v)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Individual ratings */}
              {isLoading ? (
                <div className="flex justify-center py-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : (
                ratingsData?.items?.map((r: ModelRatingItem) => (
                  <div
                    key={r.id}
                    className="flex items-start gap-3 rounded-md bg-muted/30 px-3 py-2"
                  >
                    <StarRating value={r.rating} readonly />
                    <div className="flex-1 min-w-0">
                      {r.notes && (
                        <p className="text-xs text-muted-foreground flex items-start gap-1">
                          <MessageSquare className="mt-0.5 h-3 w-3 shrink-0" />
                          {r.notes}
                        </p>
                      )}
                      <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                        {new Date(r.created_at).toLocaleDateString()}{" "}
                        {new Date(r.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))
              )}
              {!isLoading && ratingsData?.items?.length === 0 && (
                <p className="text-xs text-muted-foreground text-center py-2">
                  No individual ratings.
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

export function ModelRegistryPage() {
  const { data: summaries, isLoading } = useModelSummary();
  const [showRate, setShowRate] = useState(false);
  const [roleFilter, setRoleFilter] = useState("");

  const filtered = roleFilter
    ? summaries?.filter((s) => s.agent_role === roleFilter)
    : summaries;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <BarChart3 className="h-6 w-6" />
            Model Registry
          </h1>
          <p className="text-sm text-muted-foreground">
            Per-agent model quality ratings and configuration snapshots.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowRate(true)} disabled={showRate}>
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Rate Model
        </Button>
      </div>

      {/* Rate dialog */}
      <AnimatePresence>
        {showRate && <RateModelDialog onClose={() => setShowRate(false)} />}
      </AnimatePresence>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-muted-foreground">Filter by role:</span>
        <div className="flex gap-1.5">
          <Button
            size="sm"
            variant={!roleFilter ? "secondary" : "ghost"}
            className="h-7 text-xs"
            onClick={() => setRoleFilter("")}
          >
            All
          </Button>
          {AGENT_ROLES.map((r) => (
            <Button
              key={r}
              size="sm"
              variant={roleFilter === r ? "secondary" : "ghost"}
              className="h-7 text-xs capitalize"
              onClick={() => setRoleFilter(roleFilter === r ? "" : r)}
            >
              {r.replace(/_/g, " ")}
            </Button>
          ))}
        </div>
      </div>

      {/* Summary table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : filtered && filtered.length > 0 ? (
        <div className="space-y-2">
          {filtered.map((s) => (
            <SummaryRow
              key={`${s.model_name}-${s.agent_role}`}
              summary={s}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <Star className="mb-2 h-8 w-8 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              No model ratings yet. Rate a model to get started.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
