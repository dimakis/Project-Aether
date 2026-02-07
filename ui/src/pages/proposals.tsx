import { useState, useRef, useEffect } from "react";
import {
  FileCheck,
  Check,
  X,
  Rocket,
  RotateCcw,
  Clock,
  Loader2,
  ArrowRight,
  Sparkles,
  MessageSquare,
  Code,
  Target,
  Activity,
  Send,
  Zap,
  Home,
  Sun,
  Lightbulb,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { YamlViewer } from "@/components/ui/data-viewer";
import { cn, formatRelativeTime } from "@/lib/utils";
import {
  useProposals,
  useProposal,
  useApproveProposal,
  useRejectProposal,
  useDeployProposal,
  useRollbackProposal,
} from "@/api/hooks";
import { streamChat } from "@/api/client";
import type { Proposal, ProposalStatus, ChatMessage, ProposalTypeValue } from "@/lib/types";

// ─── Config ──────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; ring: string }
> = {
  draft: {
    label: "Draft",
    color: "text-zinc-400",
    bg: "bg-zinc-500/10",
    ring: "ring-zinc-500/30",
  },
  proposed: {
    label: "Pending",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    ring: "ring-amber-500/30",
  },
  approved: {
    label: "Approved",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    ring: "ring-blue-500/30",
  },
  rejected: {
    label: "Rejected",
    color: "text-red-400",
    bg: "bg-red-500/10",
    ring: "ring-red-500/30",
  },
  deployed: {
    label: "Deployed",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    ring: "ring-emerald-500/30",
  },
  rolled_back: {
    label: "Rolled Back",
    color: "text-zinc-400",
    bg: "bg-zinc-500/10",
    ring: "ring-zinc-500/30",
  },
  archived: {
    label: "Archived",
    color: "text-zinc-400",
    bg: "bg-zinc-500/10",
    ring: "ring-zinc-500/30",
  },
  failed: {
    label: "Failed",
    color: "text-red-400",
    bg: "bg-red-500/10",
    ring: "ring-red-500/30",
  },
};

const STATUS_STRIP: Record<string, string> = {
  draft: "bg-zinc-500",
  proposed: "bg-amber-500",
  approved: "bg-blue-500",
  rejected: "bg-red-500",
  deployed: "bg-emerald-500",
  rolled_back: "bg-zinc-500",
  archived: "bg-zinc-500",
  failed: "bg-red-500",
};

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "proposed", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "deployed", label: "Deployed" },
  { value: "rejected", label: "Rejected" },
  { value: "rolled_back", label: "Rolled Back" },
];

const TYPE_ICONS: Record<string, typeof Sparkles> = {
  automation: Zap,
  entity_command: Target,
  script: Code,
  scene: Home,
};

const PROMPT_SUGGESTIONS = [
  {
    icon: Sun,
    label: "Automate lights at sunset",
    message: "Create an automation that turns on the living room lights at sunset",
  },
  {
    icon: Home,
    label: "Create a motion-activated scene",
    message: "Create a scene that activates lights when motion is detected in the hallway",
  },
  {
    icon: Lightbulb,
    label: "Optimize heating schedule",
    message: "Create an automation to optimize my heating schedule based on time of day",
  },
];

// ─── Page ────────────────────────────────────────────────────────────────────

export function ProposalsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading } = useProposals(statusFilter || undefined);
  const proposalList = data?.items ?? [];

  return (
    <div className="relative p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <FileCheck className="h-6 w-6" />
          Proposals
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Automation proposals from the Architect agent
        </p>
      </div>

      {/* Architect Prompt */}
      <ArchitectPrompt />

      {/* Summary stats */}
      {!isLoading && proposalList.length > 0 && (
        <div className="mb-6 flex gap-3">
          {Object.entries(
            proposalList.reduce<Record<string, number>>((acc, p) => {
              acc[p.status] = (acc[p.status] || 0) + 1;
              return acc;
            }, {}),
          ).map(([status, count]) => {
            const config = STATUS_CONFIG[status as ProposalStatus];
            return (
              <button
                key={status}
                onClick={() =>
                  setStatusFilter(statusFilter === status ? "" : status)
                }
                className={cn(
                  "rounded-lg px-3 py-1.5 text-xs font-medium ring-1 transition-all",
                  config?.bg,
                  config?.color,
                  config?.ring,
                  statusFilter === status && "ring-2",
                )}
              >
                {count} {config?.label ?? status}
              </button>
            );
          })}
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-1">
        <span className="mr-1 self-center text-xs text-muted-foreground">
          Status:
        </span>
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={cn(
              "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
              statusFilter === f.value
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground hover:bg-accent",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Proposal Cards */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44" />
          ))}
        </div>
      ) : proposalList.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-16">
            <FileCheck className="mb-3 h-10 w-10 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              No proposals found. Use the prompt above or chat with the Architect to create automations.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {proposalList.map((proposal) => (
            <ProposalCard
              key={proposal.id}
              proposal={proposal}
              isExpanded={expandedId === proposal.id}
              onExpand={() =>
                setExpandedId(expandedId === proposal.id ? null : proposal.id)
              }
            />
          ))}
        </div>
      )}

      {/* Expanded Detail Overlay */}
      {expandedId && (
        <ProposalDetailOverlay
          proposalId={expandedId}
          onClose={() => setExpandedId(null)}
        />
      )}
    </div>
  );
}

// ─── Architect Prompt ─────────────────────────────────────────────────────────

function ArchitectPrompt() {
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [response, setResponse] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async (message: string) => {
    if (!message.trim() || isStreaming) return;

    setInput("");
    setIsStreaming(true);
    setResponse(null);

    const chatHistory: ChatMessage[] = [
      {
        role: "system",
        content:
          "The user is on the Proposals page and wants you to create a proposal. " +
          "Use the seek_approval tool to submit your proposal. " +
          "Be concise and action-oriented.",
      },
      { role: "user", content: message.trim() },
    ];

    try {
      let fullContent = "";
      for await (const chunk of streamChat("gpt-4o-mini", chatHistory)) {
        if (typeof chunk === "object" && "type" in chunk && chunk.type === "metadata") {
          continue;
        }
        const text = typeof chunk === "string" ? chunk : "";
        fullContent += text;
        setResponse(fullContent);
      }
    } catch {
      setResponse("Sorry, I encountered an error. Please try again.");
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(input);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height =
        Math.min(inputRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  return (
    <div className="mb-6">
      <Card>
        <CardContent className="p-4">
          {/* Input area */}
          <div className="flex items-end gap-2">
            <div className="flex min-w-0 flex-1 items-end gap-2 rounded-lg border border-border bg-background p-2 transition-colors focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20">
              <Sparkles className="mb-1 h-4 w-4 shrink-0 text-primary/60" />
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask the Architect to design an automation..."
                rows={1}
                className="flex-1 resize-none border-0 bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none"
                disabled={isStreaming}
              />
              <Button
                size="icon"
                variant="ghost"
                onClick={() => handleSubmit(input)}
                disabled={!input.trim() || isStreaming}
                className="shrink-0"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Suggestion chips */}
          {!response && !isStreaming && (
            <div className="mt-3 flex flex-wrap gap-2">
              {PROMPT_SUGGESTIONS.map((s) => (
                <button
                  key={s.label}
                  onClick={() => handleSubmit(s.message)}
                  className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/30 hover:bg-accent hover:text-foreground"
                >
                  <s.icon className="h-3 w-3" />
                  {s.label}
                </button>
              ))}
            </div>
          )}

          {/* Response area */}
          {(response || isStreaming) && (
            <div className="mt-3 rounded-lg bg-muted/50 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
                <Sparkles className="h-3 w-3" />
                Architect
                {isStreaming && <Loader2 className="h-2.5 w-2.5 animate-spin" />}
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                {response || "Thinking..."}
              </p>
              {!isStreaming && response && (
                <button
                  onClick={() => setResponse(null)}
                  className="mt-2 text-xs text-muted-foreground/50 transition-colors hover:text-foreground"
                >
                  Dismiss
                </button>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Proposal Card ───────────────────────────────────────────────────────────

function ProposalCard({
  proposal,
  isExpanded,
  onExpand,
}: {
  proposal: Proposal;
  isExpanded: boolean;
  onExpand: () => void;
}) {
  const config = STATUS_CONFIG[proposal.status] ?? STATUS_CONFIG.proposed;
  const TypeIcon = TYPE_ICONS[proposal.proposal_type ?? "automation"] ?? Sparkles;

  return (
    <button
      onClick={onExpand}
      className={cn(
        "group relative flex flex-col rounded-xl border text-left transition-all duration-200",
        "hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5",
        isExpanded
          ? "border-primary/50 ring-2 ring-primary/20"
          : "border-border",
      )}
    >
      {/* Status indicator strip */}
      <div
        className={cn(
          "absolute left-0 top-0 h-full w-1 rounded-l-xl",
          STATUS_STRIP[proposal.status] ?? "bg-zinc-600",
        )}
      />

      <div className="flex flex-col gap-3 p-4 pl-5">
        {/* Top: icon + status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", config.bg)}>
              <TypeIcon className={cn("h-4 w-4", config.color)} />
            </div>
            <div className="flex flex-col">
              {proposal.proposal_type && proposal.proposal_type !== "automation" && (
                <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
                  {proposal.proposal_type.replace("_", " ")}
                </span>
              )}
              {proposal.conversation_id && (
                <span className="text-[10px] text-muted-foreground">
                  from conversation
                </span>
              )}
            </div>
          </div>
          <Badge
            className={cn(
              "text-[10px] ring-1",
              config.bg,
              config.color,
              config.ring,
            )}
          >
            {config.label}
          </Badge>
        </div>

        {/* Name */}
        <h3 className="text-sm font-semibold leading-snug">{proposal.name}</h3>

        {/* Description */}
        <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2">
          {proposal.description || "No description provided"}
        </p>

        {/* Service call info for entity commands */}
        {proposal.service_call && (
          <div className="rounded-md bg-muted/50 px-2 py-1 text-[10px] font-mono text-muted-foreground">
            {proposal.service_call.domain}.{proposal.service_call.service}
            {proposal.service_call.entity_id && (
              <span className="text-primary"> {proposal.service_call.entity_id}</span>
            )}
          </div>
        )}

        {/* Bottom */}
        <div className="flex items-center gap-3 pt-1">
          <span className="text-[10px] text-muted-foreground">
            {formatRelativeTime(proposal.created_at)}
          </span>
          <div className="ml-auto text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
            <ArrowRight className="h-3.5 w-3.5" />
          </div>
        </div>
      </div>
    </button>
  );
}

// ─── Detail Overlay ──────────────────────────────────────────────────────────

function ProposalDetailOverlay({
  proposalId,
  onClose,
}: {
  proposalId: string;
  onClose: () => void;
}) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const { data: detail, isLoading } = useProposal(proposalId);
  const approveMut = useApproveProposal();
  const rejectMut = useRejectProposal();
  const deployMut = useDeployProposal();
  const rollbackMut = useRollbackProposal();
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

          {/* YAML Viewer */}
          {detail.yaml_content && (
            <div>
              <h4 className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <Code className="h-3 w-3" />
                {(detail as Proposal).proposal_type === "entity_command" ? "Service Call" : "Automation YAML"}
              </h4>
              <div className="overflow-hidden rounded-lg border border-border">
                <YamlViewer
                  content={detail.yaml_content}
                  collapsible
                  maxHeight={400}
                />
              </div>
            </div>
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
          {detail.ha_automation_id && (
            <span className="text-[10px] font-mono text-muted-foreground">
              HA: {detail.ha_automation_id}
            </span>
          )}
          <div className="ml-auto flex gap-2">
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
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Metric pill ─────────────────────────────────────────────────────────────

function MetricPill({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Activity;
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

// ─── Timeline entry ──────────────────────────────────────────────────────────

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
