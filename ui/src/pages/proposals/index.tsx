import { useState, useMemo } from "react";
import { FileCheck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useProposals } from "@/api/hooks";
import { ProposalCard } from "./ProposalCard";
import { ProposalDetail } from "./ProposalDetail";
import { ProposalFilters } from "./ProposalFilters";
import { ArchitectPrompt } from "./ArchitectPrompt";

export function ProposalsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading } = useProposals(statusFilter || undefined);
  const proposalList = data?.items ?? [];

  const statusCounts = useMemo(() => {
    return proposalList.reduce<Record<string, number>>((acc, p) => {
      acc[p.status] = (acc[p.status] || 0) + 1;
      return acc;
    }, {});
  }, [proposalList]);

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

      {/* Filters */}
      <ProposalFilters
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusCounts={statusCounts}
      />

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
        <ProposalDetail
          proposalId={expandedId}
          onClose={() => setExpandedId(null)}
        />
      )}
    </div>
  );
}

export default ProposalsPage;
