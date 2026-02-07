import { cn } from "@/lib/utils";
import { STATUS_FILTERS, TYPE_CONFIG } from "./types";

interface FilterGroupProps {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}

export function FilterGroup({
  label,
  options,
  value,
  onChange,
}: FilterGroupProps) {
  return (
    <div className="flex flex-wrap gap-1">
      <span className="mr-1 self-center text-xs text-muted-foreground">
        {label}:
      </span>
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
            value === o.value
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground hover:bg-accent",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function InsightFilters({
  typeFilter,
  statusFilter,
  onTypeFilterChange,
  onStatusFilterChange,
}: {
  typeFilter: string;
  statusFilter: string;
  onTypeFilterChange: (v: string) => void;
  onStatusFilterChange: (v: string) => void;
}) {
  return (
    <div className="mb-4 flex flex-wrap gap-4">
      <FilterGroup
        label="Status"
        options={STATUS_FILTERS}
        value={statusFilter}
        onChange={onStatusFilterChange}
      />
      <FilterGroup
        label="Type"
        options={[
          { value: "", label: "All" },
          ...Object.entries(TYPE_CONFIG).map(([key, c]) => ({
            value: key,
            label: c.label,
          })),
        ]}
        value={typeFilter}
        onChange={onTypeFilterChange}
      />
    </div>
  );
}
