import { useNavigate } from "react-router-dom";
import { Activity, Wifi, WifiOff } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { SystemStatus } from "@/lib/types";
import { COMPONENT_ICONS, STATUS_COLORS } from "../constants";
import { formatUptime } from "../helpers";

export interface SystemOverviewCardProps {
  status?: SystemStatus | null;
  isLoading: boolean;
}

export function SystemOverviewCard({ status, isLoading }: SystemOverviewCardProps) {
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-4">
      {/* Overall status */}
      <Card
        className={cn(
          "cursor-pointer border transition-all hover:shadow-md",
          status?.status === "healthy"
            ? "border-emerald-500/20"
            : "border-amber-500/20",
        )}
        onClick={() => navigate("/diagnostics")}
      >
        <CardContent className="flex items-center gap-3 p-4">
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg",
              STATUS_COLORS[status?.status ?? "healthy"]?.bg,
            )}
          >
            <Activity
              className={cn(
                "h-5 w-5",
                STATUS_COLORS[status?.status ?? "healthy"]?.text,
              )}
            />
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
              System
            </p>
            <p className="text-sm font-semibold capitalize">
              {status?.status ?? "Unknown"}
            </p>
            {status?.uptime_seconds != null && (
              <p className="text-[10px] text-muted-foreground">
                Up {formatUptime(status.uptime_seconds)}
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Individual components */}
      {status?.components?.map((comp) => {
        const colors = STATUS_COLORS[comp.status] ?? STATUS_COLORS.healthy;
        const Icon = COMPONENT_ICONS[comp.name] ?? Wifi;
        return (
          <Card
            key={comp.name}
            className="cursor-pointer transition-all hover:shadow-md"
            onClick={() => navigate("/diagnostics")}
          >
            <CardContent className="flex items-center gap-3 p-4">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg",
                  colors.bg,
                )}
              >
                {comp.status === "unhealthy" ? (
                  <WifiOff className={cn("h-5 w-5", colors.text)} />
                ) : (
                  <Icon className={cn("h-5 w-5", colors.text)} />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  {comp.name.replace(/_/g, " ")}
                </p>
                <p className="text-sm font-semibold capitalize">
                  {comp.status}
                </p>
                {comp.latency_ms != null && (
                  <p className="text-[10px] text-muted-foreground">
                    {comp.latency_ms.toFixed(0)}ms
                  </p>
                )}
              </div>
              <div
                className={cn("h-2 w-2 rounded-full", colors.dot)}
              />
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
