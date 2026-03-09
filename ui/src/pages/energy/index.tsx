import { useNavigate } from "react-router-dom";
import { Zap, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTariffs } from "@/api/hooks";
import { CurrentRateBanner } from "./CurrentRateBanner";
import { TariffCard } from "./TariffCard";
import { ConsumptionSummary } from "./ConsumptionSummary";
import { CostBreakdownCard } from "./CostBreakdownCard";
import { QuickActionsCard } from "./QuickActionsCard";
import { RecentEnergyInsights } from "./RecentEnergyInsights";

export function EnergyPage() {
  const navigate = useNavigate();
  const { data: tariffs, isLoading } = useTariffs();

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Zap className="h-6 w-6 text-yellow-400" />
          Energy
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Electricity tariffs, consumption, and cost analysis
        </p>
      </div>

      {/* Not-configured state */}
      {!isLoading && !tariffs?.configured && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-border py-16">
          <Zap className="mb-4 h-12 w-12 text-muted-foreground/30" />
          <h2 className="mb-2 text-lg font-medium">No Tariff Configured</h2>
          <p className="mb-6 max-w-md text-center text-sm text-muted-foreground">
            Tell Aether your electricity rates to unlock cost tracking and
            energy optimization insights. Just paste your tariff details in the
            chat.
          </p>
          <Button onClick={() => navigate("/chat")}>
            <MessageSquare className="mr-2 h-4 w-4" />
            Set Up Tariffs via Chat
          </Button>
        </div>
      )}

      {/* Configured state */}
      {(isLoading || tariffs?.configured) && (
        <>
          {/* Top stat cards */}
          <div className="mb-6">
            <CurrentRateBanner tariffs={tariffs} loading={isLoading} />
          </div>

          {/* Main grid */}
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Left column (2 cols) */}
            <div className="space-y-6 lg:col-span-2">
              {tariffs?.configured && <TariffCard tariffs={tariffs} />}
              <ConsumptionSummary />
            </div>

            {/* Right column */}
            <div className="space-y-6">
              {tariffs?.configured && <CostBreakdownCard tariffs={tariffs} />}
              <QuickActionsCard />
              <RecentEnergyInsights />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
