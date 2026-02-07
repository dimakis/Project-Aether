import { ArrowRight, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { Proposal } from "@/lib/types";
import { STATUS_CONFIG, STATUS_STRIP, TYPE_ICONS } from "./types";

interface ProposalCardProps {
  proposal: Proposal;
  isExpanded: boolean;
  onExpand: () => void;
}

export function ProposalCard({
  proposal,
  isExpanded,
  onExpand,
}: ProposalCardProps) {
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
