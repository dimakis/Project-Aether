import { Link } from "react-router-dom";
import { Activity, FileCheck, Lightbulb } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn, formatRelativeTime } from "@/lib/utils";

export interface ActivityItem {
  id: string;
  type: "proposal" | "insight";
  title: string;
  status: string;
  timestamp: string;
  link: string;
}

export function RecentActivityFeed({
  proposals,
  insights,
}: {
  proposals: Array<{ id: string; name: string; status: string; created_at: string }>;
  insights: Array<{ id: string; title: string; status: string; created_at: string }>;
}) {
  // Merge and sort by timestamp
  const items: ActivityItem[] = [
    ...proposals.slice(0, 5).map((p) => ({
      id: p.id,
      type: "proposal" as const,
      title: p.name,
      status: p.status,
      timestamp: p.created_at,
      link: `/proposals?id=${p.id}`,
    })),
    ...insights.slice(0, 5).map((i) => ({
      id: i.id,
      type: "insight" as const,
      title: i.title,
      status: i.status,
      timestamp: i.created_at,
      link: "/insights",
    })),
  ].sort(
    (a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  );

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center py-8 text-center">
        <Activity className="mb-2 h-6 w-6 text-muted-foreground/20" />
        <p className="text-xs text-muted-foreground">No recent activity</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {items.slice(0, 8).map((item) => (
        <Link
          key={`${item.type}-${item.id}`}
          to={item.link}
          className="flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-accent/50"
        >
          <div
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-md",
              item.type === "proposal"
                ? "bg-amber-400/10 text-amber-400"
                : "bg-blue-400/10 text-blue-400",
            )}
          >
            {item.type === "proposal" ? (
              <FileCheck className="h-3 w-3" />
            ) : (
              <Lightbulb className="h-3 w-3" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium">{item.title}</p>
          </div>
          <Badge
            variant="secondary"
            className="shrink-0 text-[9px] capitalize"
          >
            {item.status}
          </Badge>
          <span className="shrink-0 text-[10px] text-muted-foreground">
            {formatRelativeTime(item.timestamp)}
          </span>
        </Link>
      ))}
    </div>
  );
}
