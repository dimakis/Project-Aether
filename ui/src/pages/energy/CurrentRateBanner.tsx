import { Zap, Sun, Moon, TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { TariffResponse } from "@/api/client/energy";

const PERIOD_STYLES: Record<string, { icon: typeof Zap; color: string; bg: string }> = {
  day: { icon: Sun, color: "text-amber-400", bg: "bg-amber-400/10" },
  night: { icon: Moon, color: "text-blue-400", bg: "bg-blue-400/10" },
  peak: { icon: Zap, color: "text-red-400", bg: "bg-red-400/10" },
};

interface Props {
  tariffs: TariffResponse | undefined;
  loading: boolean;
}

export function CurrentRateBanner({ tariffs, loading }: Props) {
  if (loading) {
    return (
      <div className="grid gap-3 sm:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardContent className="flex items-center gap-3 p-4">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="space-y-1.5">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-6 w-16" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!tariffs?.configured) {
    return null;
  }

  const period = tariffs.current_period ?? "day";
  const style = PERIOD_STYLES[period] ?? PERIOD_STYLES.day;
  const PeriodIcon = style.icon;

  const nightRate = tariffs.rates?.night?.rate ?? 0;
  const currentRate = tariffs.current_rate ?? 0;
  const cheapestRate = Math.min(
    tariffs.rates?.day?.rate ?? 100,
    tariffs.rates?.night?.rate ?? 100,
    tariffs.rates?.peak?.rate ?? 100,
  );
  const isAtCheapest = currentRate <= cheapestRate;

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg", style.bg)}>
            <PeriodIcon className={cn("h-5 w-5", style.color)} />
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Current Rate
            </p>
            <p className="text-lg font-bold tabular-nums">
              {currentRate.toFixed(2)}{" "}
              <span className="text-xs font-normal text-muted-foreground">c/kWh</span>
            </p>
            <p className={cn("text-[10px] font-medium capitalize", style.color)}>
              {period} period
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-400/10">
            <Moon className="h-5 w-5 text-blue-400" />
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Cheapest Rate
            </p>
            <p className="text-lg font-bold tabular-nums">
              {nightRate.toFixed(2)}{" "}
              <span className="text-xs font-normal text-muted-foreground">c/kWh</span>
            </p>
            <p className="text-[10px] text-muted-foreground">Night (23:00–08:00)</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg",
              isAtCheapest ? "bg-green-400/10" : "bg-orange-400/10",
            )}
          >
            {isAtCheapest ? (
              <TrendingDown className="h-5 w-5 text-green-400" />
            ) : (
              <TrendingUp className="h-5 w-5 text-orange-400" />
            )}
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Savings Opportunity
            </p>
            {isAtCheapest ? (
              <p className="text-sm font-medium text-green-400">
                You're on the cheapest rate
              </p>
            ) : (
              <>
                <p className="text-lg font-bold tabular-nums">
                  {(currentRate - nightRate).toFixed(2)}{" "}
                  <span className="text-xs font-normal text-muted-foreground">c/kWh</span>
                </p>
                <p className="text-[10px] text-muted-foreground">
                  saving vs night rate
                </p>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
