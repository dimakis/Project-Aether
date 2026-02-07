import { cn } from "@/lib/utils";

interface StatPillProps {
  label: string;
  value: number;
  color: string;
}

export function StatPill({ label, value, color }: StatPillProps) {
  return (
    <span className={cn("text-xs font-medium", color)}>
      {value}{" "}
      <span className="text-muted-foreground">{label}</span>
    </span>
  );
}
