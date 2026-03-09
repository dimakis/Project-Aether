import { Battery, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEntities } from "@/api/hooks";

export function ConsumptionSummary() {
  const { data, isLoading } = useEntities("sensor");

  const energySensors = (data?.entities ?? []).filter(
    (e) =>
      e.device_class === "energy" ||
      e.unit_of_measurement === "kWh" ||
      e.unit_of_measurement === "Wh",
  );

  const powerSensors = (data?.entities ?? []).filter(
    (e) =>
      e.device_class === "power" ||
      e.unit_of_measurement === "W" ||
      e.unit_of_measurement === "kW",
  );

  const topConsumers = energySensors
    .filter((e) => e.state != null && !isNaN(Number(e.state)))
    .sort((a, b) => Number(b.state) - Number(a.state))
    .slice(0, 6);

  const maxKwh = topConsumers.length > 0 ? Number(topConsumers[0].state) : 1;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Activity className="h-4 w-4 text-green-400" />
          Energy Sensors
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 rounded" />
            ))}
          </div>
        ) : energySensors.length === 0 ? (
          <div className="py-4 text-center">
            <Battery className="mx-auto mb-2 h-8 w-8 text-muted-foreground/30" />
            <p className="text-xs text-muted-foreground">
              No energy sensors found. Ensure your smart meter is integrated with HA.
            </p>
          </div>
        ) : (
          <>
            <div className="mb-3 flex items-center justify-between text-xs text-muted-foreground">
              <span>{energySensors.length} energy sensors</span>
              <span>{powerSensors.length} power sensors</span>
            </div>

            {topConsumers.length > 0 && (
              <div className="space-y-2">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  Top Consumers (by current reading)
                </p>
                {topConsumers.map((sensor) => {
                  const value = Number(sensor.state);
                  const pct = maxKwh > 0 ? (value / maxKwh) * 100 : 0;
                  const shortName = sensor.name || sensor.entity_id.split(".").pop() || sensor.entity_id;

                  return (
                    <div key={sensor.entity_id} className="group/bar">
                      <div className="mb-0.5 flex items-center justify-between text-xs">
                        <span
                          className="max-w-[180px] truncate font-mono text-muted-foreground"
                          title={sensor.entity_id}
                        >
                          {shortName}
                        </span>
                        <span className="font-semibold tabular-nums">
                          {value.toFixed(1)} {sensor.unit_of_measurement}
                        </span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-green-500 to-emerald-400 transition-all duration-500"
                          style={{ width: `${Math.min(Math.max(pct, 2), 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
