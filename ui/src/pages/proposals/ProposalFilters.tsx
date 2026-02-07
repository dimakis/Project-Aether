import { cn } from "@/lib/utils";
import { STATUS_FILTERS, STATUS_CONFIG } from "./types";
import type { ProposalStatus } from "@/lib/types";

interface ProposalFiltersProps {
  statusFilter: string;
  onStatusFilterChange: (value: string) => void;
  statusCounts: Record<string, number>;
}

export function ProposalFilters({
  statusFilter,
  onStatusFilterChange,
  statusCounts,
}: ProposalFiltersProps) {
  return (
    <>
      {/* Summary stats */}
      {Object.keys(statusCounts).length > 0 && (
        <div className="mb-6 flex gap-3">
          {Object.entries(statusCounts).map(([status, count]) => {
            const config = STATUS_CONFIG[status as ProposalStatus];
            return (
              <button
                key={status}
                onClick={() =>
                  onStatusFilterChange(statusFilter === status ? "" : status)
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
            onClick={() => onStatusFilterChange(f.value)}
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
    </>
  );
}
