import { Sun, Moon, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { TariffResponse } from "@/api/client/energy";

const PERIOD_CONFIG = {
  day: {
    icon: Sun,
    label: "Day",
    color: "text-amber-400",
    bg: "bg-amber-400/10",
    ring: "ring-amber-500/20",
  },
  night: {
    icon: Moon,
    label: "Night",
    color: "text-blue-400",
    bg: "bg-blue-400/10",
    ring: "ring-blue-500/20",
  },
  peak: {
    icon: Zap,
    label: "Peak",
    color: "text-red-400",
    bg: "bg-red-400/10",
    ring: "ring-red-500/20",
  },
} as const;

type Period = keyof typeof PERIOD_CONFIG;

export function TariffCard({ tariffs }: { tariffs: TariffResponse }) {
  if (!tariffs.configured || !tariffs.rates) return null;
  const currentPeriod = (tariffs.current_period ?? "day") as Period;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Zap className="h-4 w-4 text-yellow-400" />
            Tariff Schedule
          </CardTitle>
          {tariffs.plan_name && (
            <Badge variant="outline" className="text-[10px]">
              {tariffs.plan_name}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {(["day", "night", "peak"] as const).map((period) => {
          const config = PERIOD_CONFIG[period];
          const rate = tariffs.rates![period];
          const Icon = config.icon;
          const isActive = currentPeriod === period;

          return (
            <div
              key={period}
              className={cn(
                "flex items-center justify-between rounded-lg px-3 py-2.5 transition-all",
                isActive
                  ? `${config.bg} ring-1 ${config.ring}`
                  : "bg-muted/30",
              )}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={cn("h-4 w-4", config.color)} />
                <div>
                  <p className={cn("text-xs font-medium", isActive && config.color)}>
                    {config.label}
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    {rate.start} – {rate.end}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn("text-sm font-bold tabular-nums", isActive && config.color)}>
                  {rate.rate.toFixed(2)}
                </span>
                <span className="text-[10px] text-muted-foreground">c/kWh</span>
                {isActive && (
                  <Badge className={cn("ml-1 text-[9px]", config.bg, config.color)}>
                    NOW
                  </Badge>
                )}
              </div>
            </div>
          );
        })}

        {tariffs.vat_rate != null && (
          <p className="pt-1 text-center text-[10px] text-muted-foreground">
            All rates include {tariffs.vat_rate}% VAT
          </p>
        )}
      </CardContent>
    </Card>
  );
}
