import { Badge } from "@/components/ui/badge";

export function InfoRow({
  label,
  value,
  emoji,
}: {
  label: string;
  value: string;
  emoji?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Badge variant="secondary" className="text-[10px]">
        {emoji && <span className="mr-1">{emoji}</span>}
        {value}
      </Badge>
    </div>
  );
}
