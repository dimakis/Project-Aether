import {
  X,
  Zap,
  ThumbsUp,
  ThumbsDown,
  Info,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { AutomationSuggestion } from "@/api/client/optimization";
import { useAcceptSuggestion, useRejectSuggestion } from "@/api/hooks";

interface SuggestionDetailProps {
  suggestion: AutomationSuggestion;
  onClose: () => void;
}

const ACCEPT_EXPLANATION =
  "Accept creates an automation proposal from this suggestion. You can then review and edit the YAML in Proposals, and deploy it to Home Assistant when ready.";

const REJECT_EXPLANATION =
  "Reject dismisses this suggestion. No proposal is created and no automation will be added. Use this when the suggestion is not relevant or you don't want to automate this pattern.";

export function SuggestionDetail({ suggestion, onClose }: SuggestionDetailProps) {
  const acceptMut = useAcceptSuggestion();
  const rejectMut = useRejectSuggestion();
  const isPending = suggestion.status === "pending";

  const handleAccept = () => {
    acceptMut.mutate(
      { id: suggestion.id },
      { onSuccess: () => onClose() },
    );
  };

  const handleReject = () => {
    rejectMut.mutate(
      { id: suggestion.id, reason: "Not needed" },
      { onSuccess: () => onClose() },
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-auto bg-black/60 p-4 pt-[8vh] backdrop-blur-sm"
      role="presentation"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-xl animate-in rounded-2xl border border-border bg-card shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="suggestion-detail-title"
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border p-6 pb-4">
          <div className="flex items-start gap-3 min-w-0">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <Zap className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0">
              <Badge
                variant={suggestion.status === "pending" ? "secondary" : suggestion.status === "accepted" ? "default" : "outline"}
                className="mb-1.5 text-[10px]"
              >
                {suggestion.status}
              </Badge>
              <h2 id="suggestion-detail-title" className="text-lg font-semibold leading-snug break-words">
                {suggestion.pattern}
              </h2>
              <p className="mt-1 text-[11px] text-muted-foreground">
                {formatRelativeTime(suggestion.created_at)} · {Math.round(suggestion.confidence * 100)}% confidence
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-5 p-6">
          <div>
            <h4 className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Trigger
            </h4>
            <p className="text-sm">{suggestion.proposed_trigger}</p>
          </div>
          <div>
            <h4 className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Action
            </h4>
            <p className="text-sm">{suggestion.proposed_action}</p>
          </div>

          {suggestion.entities.length > 0 && (
            <div>
              <h4 className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Entities involved
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {suggestion.entities.map((e) => (
                  <Badge key={e} variant="outline" className="text-[10px] font-mono">
                    {e}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {suggestion.source_insight_type && (
            <p className="text-[11px] text-muted-foreground">
              Source: {suggestion.source_insight_type.replace(/_/g, " ")}
            </p>
          )}

          {isPending && (
            <>
              <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-3">
                <h4 className="flex items-center gap-2 text-xs font-medium text-foreground">
                  <Info className="h-3.5 w-3.5" />
                  What do Accept and Reject do?
                </h4>
                <div className="space-y-2 text-xs text-muted-foreground">
                  <p>
                    <strong className="text-foreground">Accept:</strong> {ACCEPT_EXPLANATION}
                  </p>
                  <p>
                    <strong className="text-foreground">Reject:</strong> {REJECT_EXPLANATION}
                  </p>
                </div>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
                <Button
                  variant="outline"
                  onClick={handleReject}
                  disabled={rejectMut.isPending}
                  className="sm:order-1"
                >
                  {rejectMut.isPending ? (
                    <span className="flex items-center gap-2">
                      <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      Rejecting…
                    </span>
                  ) : (
                    <>
                      <ThumbsDown className="mr-2 h-3.5 w-3.5" />
                      Reject
                    </>
                  )}
                </Button>
                <Button
                  onClick={handleAccept}
                  disabled={acceptMut.isPending}
                  className="sm:order-2"
                >
                  {acceptMut.isPending ? (
                    <span className="flex items-center gap-2">
                      <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      Accepting…
                    </span>
                  ) : (
                    <>
                      <ThumbsUp className="mr-2 h-3.5 w-3.5" />
                      Accept & create proposal
                    </>
                  )}
                </Button>
              </div>
            </>
          )}

          {suggestion.status === "accepted" && (
            <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2 text-sm text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>Accepted. Check Proposals to review and deploy the automation.</span>
            </div>
          )}

          {suggestion.status === "rejected" && (
            <div className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">
              <XCircle className="h-4 w-4 shrink-0" />
              <span>Rejected. No automation was created.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
