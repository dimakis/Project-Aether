import { memo } from "react";
import { cn } from "@/lib/utils";

interface StatPillProps {
  label: string;
  value: number;
  color: string;
}

export const StatPill = memo(function StatPill({ label, value, color }: StatPillProps) {
  return (
    <span className={cn("text-xs font-medium", color)}>
      {value}{" "}
      <span className="text-muted-foreground">{label}</span>
    </span>
  );
});
