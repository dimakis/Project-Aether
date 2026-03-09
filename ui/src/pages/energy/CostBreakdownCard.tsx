import { PieChart } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { TariffResponse } from "@/api/client/energy";

const PERIOD_COLORS: Record<string, { bar: string; text: string; label: string }> = {
  day: { bar: "bg-amber-400", text: "text-amber-400", label: "Day (08-17, 19-23)" },
  peak: { bar: "bg-red-400", text: "text-red-400", label: "Peak (17-19)" },
  night: { bar: "bg-blue-400", text: "text-blue-400", label: "Night (23-08)" },
};

const HOURS_PER_DAY: Record<string, number> = {
  day: 13,
  peak: 2,
  night: 9,
};

export function CostBreakdownCard({ tariffs }: { tariffs: TariffResponse }) {
  if (!tariffs.configured || !tariffs.rates) return null;

  const periods = (["day", "peak", "night"] as const).map((period) => {
    const rate = tariffs.rates![period].rate;
    const hours = HOURS_PER_DAY[period];
    return { period, rate, hours, ...PERIOD_COLORS[period] };
  });

  const maxRate = Math.max(...periods.map((p) => p.rate));

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <PieChart className="h-4 w-4 text-purple-400" />
          Cost Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {periods.map(({ period, rate, hours, bar, text, label }) => {
          const pct = maxRate > 0 ? (rate / maxRate) * 100 : 0;
          return (
            <div key={period}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{label}</span>
                <div className="flex items-center gap-2">
                  <span className={cn("font-bold tabular-nums", text)}>
                    {rate.toFixed(2)}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    c/kWh &middot; {hours}h/day
                  </span>
                </div>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className={cn("h-full rounded-full transition-all duration-500", bar)}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}

        <div className="mt-2 rounded-lg bg-muted/30 p-3">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Rate Spread
          </p>
          <p className="mt-1 text-xs">
            <span className="font-bold tabular-nums text-red-400">
              {(tariffs.rates.peak.rate - tariffs.rates.night.rate).toFixed(2)}
            </span>{" "}
            <span className="text-muted-foreground">
              c/kWh difference between peak and night
            </span>
          </p>
          <p className="mt-0.5 text-[10px] text-muted-foreground">
            Shift heavy loads to night hours to save up to{" "}
            {(
              ((tariffs.rates.peak.rate - tariffs.rates.night.rate) /
                tariffs.rates.peak.rate) *
              100
            ).toFixed(0)}
            % per kWh
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
