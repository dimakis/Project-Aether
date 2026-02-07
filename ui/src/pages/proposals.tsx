import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileCheck,
  Check,
  X,
  Rocket,
  RotateCcw,
  Clock,
  Loader2,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import type { Proposal, ProposalStatus } from "@/lib/types";

const STATUS_CONFIG: Record<
  ProposalStatus,
  {
    label: string;
    emoji: string;
    variant: "warning" | "success" | "destructive" | "info" | "secondary";
  }
> = {
  pending: { label: "Pending", emoji: "⏳", variant: "warning" },
  approved: { label: "Approved", emoji: "✅", variant: "info" },
  rejected: { label: "Rejected", emoji: "❌", variant: "destructive" },
  deployed: { label: "Deployed", emoji: "🚀", variant: "success" },
  rolled_back: { label: "Rolled Back", emoji: "↩️", variant: "secondary" },
  failed: { label: "Failed", emoji: "💥", variant: "destructive" },
};

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "pending", label: "⏳ Pending" },
  { value: "approved", label: "✅ Approved" },
  { value: "deployed", label: "🚀 Deployed" },
  { value: "rejected", label: "❌ Rejected" },
];

export function ProposalsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useProposals(statusFilter || undefined);
  const { data: detail, isLoading: detailLoading } = useProposal(
    selectedId ?? "",
  );

  const approveMut = useApproveProposal();
  const rejectMut = useRejectProposal();
  const deployMut = useDeployProposal();
  const rollbackMut = useRollbackProposal();

  const proposalList = data?.items ?? [];

  return (
    <div className="flex h-full">
      {/* List Panel */}
      <div className="flex w-96 flex-col border-r border-border">
        <div className="border-b border-border p-4">
          <h1 className="flex items-center gap-2 text-lg font-semibold">
            <FileCheck className="h-5 w-5" />
            Proposals
          </h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Automation proposals from the Architect agent
          </p>
          {/* Filters */}
          <div className="mt-3 flex flex-wrap gap-1">
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
        </div>

        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="space-y-2 p-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : proposalList.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-center">
              <FileCheck className="mb-2 h-8 w-8 text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">No proposals found</p>
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {proposalList.map((p) => (
                <ProposalListItem
                  key={p.id}
                  proposal={p}
                  isSelected={p.id === selectedId}
                  onClick={() => setSelectedId(p.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detail Panel */}
      <div className="flex-1 overflow-auto">
        <AnimatePresence mode="wait">
          {selectedId && detail ? (
            <motion.div
              key={detail.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="p-6"
            >
              <div className="mb-6 flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-primary" />
                    <h2 className="text-xl font-semibold">{detail.name}</h2>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {detail.description || "No description"}
                  </p>
                </div>
                <Badge
                  variant={STATUS_CONFIG[detail.status]?.variant ?? "secondary"}
                >
                  {STATUS_CONFIG[detail.status]?.emoji}{" "}
                  {STATUS_CONFIG[detail.status]?.label ?? detail.status}
                </Badge>
              </div>

              {/* Actions */}
              <div className="mb-6 flex gap-2">
                {detail.status === "pending" && (
                  <>
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
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() =>
                        rejectMut.mutate({
                          id: detail.id,
                          reason: "Rejected via UI",
                        })
                      }
                      disabled={rejectMut.isPending}
                    >
                      {rejectMut.isPending ? (
                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      ) : (
                        <X className="mr-1 h-3 w-3" />
                      )}
                      Reject
                    </Button>
                  </>
                )}
                {detail.status === "approved" && (
                  <Button
                    size="sm"
                    onClick={() => deployMut.mutate(detail.id)}
                    disabled={deployMut.isPending}
                  >
                    {deployMut.isPending ? (
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    ) : (
                      <Rocket className="mr-1 h-3 w-3" />
                    )}
                    Deploy
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

              {/* YAML with syntax highlighting */}
              {detail.yaml_content && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-sm">
                      <span>📝</span>
                      Automation YAML
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <YamlViewer
                      content={detail.yaml_content}
                      collapsible
                      maxHeight={600}
                    />
                  </CardContent>
                </Card>
              )}

              {/* Timeline */}
              <Card className="mt-4">
                <CardHeader>
                  <CardTitle className="text-sm">Timeline</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    {detail.proposed_at && (
                      <TimelineEntry
                        label="📋 Proposed"
                        time={detail.proposed_at}
                      />
                    )}
                    {detail.approved_at && (
                      <TimelineEntry
                        label={`✅ Approved by ${detail.approved_by}`}
                        time={detail.approved_at}
                      />
                    )}
                    {detail.deployed_at && (
                      <TimelineEntry
                        label="🚀 Deployed"
                        time={detail.deployed_at}
                      />
                    )}
                    {detail.rolled_back_at && (
                      <TimelineEntry
                        label="↩️ Rolled Back"
                        time={detail.rolled_back_at}
                      />
                    )}
                    {detail.rejection_reason && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="rounded-lg bg-destructive/5 p-3"
                      >
                        <p className="text-xs font-medium text-destructive">
                          ❌ Rejection reason
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {detail.rejection_reason}
                        </p>
                      </motion.div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ) : detailLoading ? (
            <div className="p-6">
              <Skeleton className="mb-4 h-8 w-64" />
              <Skeleton className="h-96 w-full" />
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex h-full flex-col items-center justify-center text-muted-foreground"
            >
              <FileCheck className="mb-3 h-10 w-10 text-muted-foreground/20" />
              <p className="text-sm">Select a proposal to view details</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function ProposalListItem({
  proposal,
  isSelected,
  onClick,
}: {
  proposal: Proposal;
  isSelected: boolean;
  onClick: () => void;
}) {
  const config = STATUS_CONFIG[proposal.status];
  return (
    <motion.button
      layout
      onClick={onClick}
      whileHover={{ x: 2 }}
      className={cn(
        "w-full rounded-lg border p-3 text-left transition-colors",
        isSelected
          ? "border-primary/50 bg-primary/5"
          : "border-transparent hover:bg-accent",
      )}
    >
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium">{proposal.name}</p>
        <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
      </div>
      <div className="mt-1 flex items-center gap-2">
        <Badge variant={config?.variant ?? "secondary"} className="text-[10px]">
          {config?.emoji} {config?.label ?? proposal.status}
        </Badge>
        <span className="text-xs text-muted-foreground">
          {formatRelativeTime(proposal.created_at)}
        </span>
      </div>
    </motion.button>
  );
}

function TimelineEntry({ label, time }: { label: string; time: string }) {
  return (
    <div className="flex items-center gap-3">
      <Clock className="h-3 w-3 shrink-0 text-muted-foreground" />
      <span className="text-muted-foreground">{label}</span>
      <span className="ml-auto text-xs text-muted-foreground">
        {formatRelativeTime(time)}
      </span>
    </div>
  );
}
