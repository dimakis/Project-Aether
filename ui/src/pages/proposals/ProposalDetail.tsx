import { useRef, useEffect, useState } from "react";
import {
  X,
  FileCheck,
  Check,
  Rocket,
  RotateCcw,
  Clock,
  Loader2,
  MessageSquare,
  Code,
  Sparkles,
  Trash2,
  Search,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { YamlViewer } from "@/components/ui/data-viewer";
import { YamlDiffViewer } from "@/components/ui/yaml-diff-viewer";
import { cn, formatRelativeTime } from "@/lib/utils";
import {
  useProposal,
  useApproveProposal,
  useRejectProposal,
  useDeployProposal,
  useRollbackProposal,
  useDeleteProposal,
} from "@/api/hooks";
import type { Proposal, ProposalWithYAML, ReviewNote } from "@/lib/types";
import { STATUS_CONFIG, TYPE_ICONS } from "./types";

interface ProposalDetailProps {
  proposalId: string;
  onClose: () => void;
}

function MetricPill({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Clock;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2">
      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      <div>
        <p className="text-[10px] text-muted-foreground">{label}</p>
        <p className="text-sm font-semibold">{value}</p>
      </div>
    </div>
  );
}

function TimelineEntry({
  icon: Icon,
  label,
  time,
  color,
}: {
  icon: typeof Clock;
  label: string;
  time: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className={cn("flex h-5 w-5 items-center justify-center rounded-full bg-muted")}>
        <Icon className={cn("h-3 w-3", color)} />
      </div>
      <span className="text-xs">{label}</span>
      <span className="ml-auto text-[10px] text-muted-foreground">
        {formatRelativeTime(time)}
      </span>
    </div>
  );
}

const CATEGORY_COLORS: Record<string, string> = {
  energy: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
  behavioral: "bg-blue-500/10 text-blue-400 ring-blue-500/20",
  efficiency: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20",
  security: "bg-red-500/10 text-red-400 ring-red-500/20",
  redundancy: "bg-zinc-500/10 text-zinc-400 ring-zinc-500/20",
};

function ReviewNotesPanel({ notes }: { notes: ReviewNote[] }) {
  return (
    <div>
      <h4 className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        <Search className="h-3 w-3" />
        Review Notes ({notes.length})
      </h4>
      <div className="space-y-2">
        {notes.map((note, i) => (
          <div
            key={i}
            className="rounded-lg border border-border bg-muted/20 p-3"
          >
            <div className="mb-1.5 flex items-center gap-2">
              <Badge
                className={cn(
                  "text-[10px] ring-1",
                  CATEGORY_COLORS[note.category] ?? CATEGORY_COLORS.efficiency,
                )}
              >
                {note.category}
              </Badge>
              <span className="text-xs font-medium">{note.change}</span>
            </div>
            <p className="text-xs text-muted-foreground">{note.rationale}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ProposalDetail({ proposalId, onClose }: ProposalDetailProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const { data: detail, isLoading } = useProposal(proposalId);
  const approveMut = useApproveProposal();
  const rejectMut = useRejectProposal();
  const deployMut = useDeployProposal();
  const rollbackMut = useRollbackProposal();
  const deleteMut = useDeleteProposal();
  const [deployResult, setDeployResult] = useState<{
    success: boolean;
    method?: string;
    instructions?: string;
    error?: string;
  } | null>(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (overlayRef.current && !overlayRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    window.addEventListener("mousedown", handler);
    return () => window.removeEventListener("mousedown", handler);
  }, [onClose]);

  if (isLoading || !detail) {
    return (
      <div className="fixed inset-0 z-50 flex items-start justify-center overflow-auto bg-black/60 p-4 pt-[8vh] backdrop-blur-sm">
        <div className="w-full max-w-2xl rounded-2xl border border-border bg-card p-8 shadow-2xl">
          <Skeleton className="mb-4 h-8 w-64" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  const config = STATUS_CONFIG[detail.status] ?? STATUS_CONFIG.proposed;
  const TypeIcon = TYPE_ICONS[(detail as Proposal).proposal_type ?? "automation"] ?? Sparkles;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-auto bg-black/60 p-4 pt-[8vh] backdrop-blur-sm">
      <div
        ref={overlayRef}
        className="w-full max-w-2xl animate-in rounded-2xl border border-border bg-card shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border p-6 pb-4">
          <div className="flex items-start gap-3">
            <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", config.bg)}>
              <TypeIcon className={cn("h-5 w-5", config.color)} />
            </div>
            <div>
              <div className="mb-1 flex items-center gap-2">
                <Badge className={cn("text-[10px] ring-1", config.bg, config.color, config.ring)}>
                  {config.label}
                </Badge>
                {(detail as Proposal).proposal_type && (detail as Proposal).proposal_type !== "automation" && (
                  <Badge variant="secondary" className="text-[10px]">
                    {((detail as Proposal).proposal_type ?? "").replace("_", " ")}
                  </Badge>
                )}
                {(detail as ProposalWithYAML).original_yaml && (
                  <Badge className="text-[10px] bg-violet-500/10 text-violet-400 ring-1 ring-violet-500/20">
                    <Search className="mr-1 h-2.5 w-2.5" />
                    Review
                  </Badge>
                )}
                {detail.conversation_id && (
                  <Badge variant="secondary" className="text-[10px]">
                    <MessageSquare className="mr-1 h-2.5 w-2.5" />
                    Conversation
                  </Badge>
                )}
              </div>
              <h2 className="text-lg font-semibold leading-snug">
                {detail.name}
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-5 p-6">
          {/* Description */}
          {detail.description && (
            <p className="text-sm leading-relaxed text-muted-foreground">
              {detail.description}
            </p>
          )}

          {/* Metrics */}
          <div className="flex gap-4">
            <MetricPill
              icon={Clock}
              label="Created"
              value={formatRelativeTime(detail.created_at)}
            />
            {detail.conversation_id && (
              <MetricPill
                icon={MessageSquare}
                label="Conversation"
                value={detail.conversation_id.slice(0, 8)}
              />
            )}
          </div>

          {/* YAML Diff Viewer (review) or plain YAML Viewer */}
          {(detail as ProposalWithYAML).original_yaml && detail.yaml_content ? (
            <div>
              <h4 className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <Code className="h-3 w-3" />
                Config Diff
              </h4>
              <YamlDiffViewer
                originalYaml={(detail as ProposalWithYAML).original_yaml!}
                suggestedYaml={detail.yaml_content}
                maxHeight={400}
              />
            </div>
          ) : detail.yaml_content ? (
            <div>
              <h4 className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <Code className="h-3 w-3" />
                {(detail as Proposal).proposal_type === "entity_command"
                  ? "Service Call"
                  : (detail as Proposal).proposal_type === "dashboard"
                    ? "Dashboard Config"
                    : "Automation YAML"}
              </h4>
              <div className="overflow-hidden rounded-lg border border-border">
                <YamlViewer
                  content={detail.yaml_content}
                  maxHeight={400}
                />
              </div>
            </div>
          ) : null}

          {/* Review Notes */}
          {(detail as ProposalWithYAML).review_notes &&
            (detail as ProposalWithYAML).review_notes!.length > 0 && (
              <ReviewNotesPanel notes={(detail as ProposalWithYAML).review_notes!} />
          )}

          {/* Timeline */}
          <div>
            <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Timeline
            </h4>
            <div className="space-y-0">
              {detail.proposed_at && (
                <TimelineEntry
                  icon={FileCheck}
                  label="Proposed"
                  time={detail.proposed_at}
                  color="text-amber-400"
                />
              )}
              {detail.approved_at && (
                <TimelineEntry
                  icon={Check}
                  label={`Approved${detail.approved_by ? ` by ${detail.approved_by}` : ""}`}
                  time={detail.approved_at}
                  color="text-blue-400"
                />
              )}
              {detail.deployed_at && (
                <TimelineEntry
                  icon={Rocket}
                  label="Deployed"
                  time={detail.deployed_at}
                  color="text-emerald-400"
                />
              )}
              {detail.rolled_back_at && (
                <TimelineEntry
                  icon={RotateCcw}
                  label="Rolled Back"
                  time={detail.rolled_back_at}
                  color="text-zinc-400"
                />
              )}
              {detail.rejection_reason && (
                <div className="mt-2 rounded-lg bg-red-500/5 p-3 ring-1 ring-red-500/20">
                  <p className="text-xs font-medium text-red-400">
                    Rejection Reason
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {detail.rejection_reason}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Deploy result feedback */}
          {deployResult && (
            <div
              className={cn(
                "rounded-lg p-3 ring-1",
                deployResult.success
                  ? "bg-emerald-500/5 ring-emerald-500/20"
                  : "bg-red-500/5 ring-red-500/20",
              )}
            >
              <p
                className={cn(
                  "text-xs font-medium",
                  deployResult.success ? "text-emerald-400" : "text-red-400",
                )}
              >
                {deployResult.success
                  ? `Deployed via ${deployResult.method === "rest_api" ? "HA REST API" : deployResult.method ?? "unknown"}`
                  : "Deployment failed"}
              </p>
              {deployResult.error && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {deployResult.error}
                </p>
              )}
              {deployResult.instructions && (
                <p className="mt-1 whitespace-pre-wrap text-xs text-muted-foreground">
                  {deployResult.instructions}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between border-t border-border p-4 px-6">
          <div className="flex items-center gap-2">
            {detail.ha_automation_id && (
              <span className="text-[10px] font-mono text-muted-foreground">
                HA: {detail.ha_automation_id}
              </span>
            )}
            {detail.status !== "deployed" && (
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                onClick={() =>
                  deleteMut.mutate(detail.id, {
                    onSuccess: () => onClose(),
                  })
                }
                disabled={deleteMut.isPending}
              >
                {deleteMut.isPending ? (
                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                ) : (
                  <Trash2 className="mr-1 h-3 w-3" />
                )}
                Delete
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            {detail.status === "proposed" && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    rejectMut.mutate({
                      id: detail.id,
                      reason: "Rejected via UI",
                    })
                  }
                  disabled={rejectMut.isPending}
                >
                  <X className="mr-1 h-3 w-3" />
                  Reject
                </Button>
                <Button
                  size="sm"
                  onClick={() => approveMut.mutate(detail.id)}
                  disabled={approveMut.isPending}
                >
                  {approveMut.isPending ? (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  ) : (
                    <Check className="mr-1 h-3 w-3" />
                  )}
                  Approve
                </Button>
              </>
            )}
            {detail.status === "approved" && (
              <Button
                size="sm"
                onClick={() =>
                  deployMut.mutate(detail.id, {
                    onSuccess: (data) => {
                      setDeployResult({
                        success: data.success,
                        method: data.method,
                        instructions: data.instructions ?? undefined,
                        error: data.error ?? undefined,
                      });
                    },
                    onError: (err) => {
                      setDeployResult({
                        success: false,
                        error: err instanceof Error ? err.message : "Deployment failed",
                      });
                    },
                  })
                }
                disabled={deployMut.isPending}
              >
                {deployMut.isPending ? (
                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                ) : (
                  <Rocket className="mr-1 h-3 w-3" />
                )}
                Deploy to HA
              </Button>
            )}
            {detail.status === "deployed" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => rollbackMut.mutate(detail.id)}
                disabled={rollbackMut.isPending}
              >
                {rollbackMut.isPending ? (
                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                ) : (
                  <RotateCcw className="mr-1 h-3 w-3" />
                )}
                Rollback
              </Button>
            )}
            {/* Rollback result feedback */}
            {rollbackMut.isSuccess && rollbackMut.data && (
              <div className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium",
                rollbackMut.data.ha_disabled
                  ? "bg-success/10 text-success"
                  : "bg-amber-500/10 text-amber-500",
              )}>
                {rollbackMut.data.ha_disabled
                  ? "Automation disabled in HA"
                  : rollbackMut.data.ha_error
                    ? `Rolled back in DB but HA disable failed: ${rollbackMut.data.ha_error}`
                    : "Rolled back (no HA automation to disable)"}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
