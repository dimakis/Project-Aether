import { XCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface EvidencePanelProps {
  evidence: Record<string, unknown>;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toFixed(1);
}

/** Safely coerce a value to a number, returning the fallback if NaN/undefined. */
function safeNum(v: unknown, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

/**
 * Normalise a peak/off-peak hours entry.
 *
 * LLM-generated evidence can vary widely:
 *   - Plain ISO string: "2026-02-07T19:00:00"
 *   - Object with `hour_start_utc`, `kwh`, `pct_of_period`
 *   - Object with `hour` instead of `hour_start_utc`
 *   - Object missing `pct_of_period`
 */
function normaliseHourEntry(raw: unknown): {
  key: string;
  hour: number;
  kwh: number;
  pct: number;
} | null {
  if (typeof raw === "string") {
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return null;
    return { key: raw, hour: d.getHours(), kwh: 0, pct: 0 };
  }
  if (raw && typeof raw === "object") {
    const obj = raw as Record<string, unknown>;
    const ts = (obj.hour_start_utc ?? obj.hour ?? obj.time ?? "") as string;
    const d = new Date(String(ts));
    const hour = Number.isNaN(d.getTime()) ? 0 : d.getHours();
    return {
      key: String(ts) || String(Math.random()),
      hour,
      kwh: safeNum(obj.kwh),
      pct: safeNum(obj.pct_of_period ?? obj.pct ?? obj.percentage),
    };
  }
  return null;
}

/**
 * Normalise a consumer entry.
 *
 * LLM evidence may use `kwh` or `total_kwh`, and may omit `pct_of_total`.
 */
function normaliseConsumer(
  raw: unknown,
  maxKwh: number,
): {
  entity_id: string;
  kwh: number;
  pct: number;
} | null {
  if (!raw || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;
  const entity_id = String(obj.entity_id ?? "unknown");
  const kwh = safeNum(obj.total_kwh ?? obj.kwh);
  const pct = safeNum(
    obj.pct_of_total ?? obj.percentage ?? (maxKwh > 0 ? (kwh / maxKwh) * 100 : 0),
  );
  return { entity_id, kwh, pct };
}

/**
 * Normalise a shifting-candidate entry.
 *
 * Field names vary: `share_in_peak` vs `peak_share` vs computed from
 * `kwh_in_peak_hours / total_kwh`.
 */
function normaliseCandidate(raw: unknown): {
  entity_id: string;
  total_kwh: number;
  share_in_peak: number;
  flexible: boolean;
} | null {
  if (!raw || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;
  const entity_id = String(obj.entity_id ?? "unknown");
  const total_kwh = safeNum(obj.total_kwh ?? obj.kwh);
  let share_in_peak = safeNum(obj.share_in_peak ?? obj.peak_share);
  if (share_in_peak === 0 && total_kwh > 0) {
    const peakKwh = safeNum(obj.kwh_in_peak_hours ?? obj.peak_kwh);
    if (peakKwh > 0) share_in_peak = peakKwh / total_kwh;
  }
  const flexible = Boolean(obj.keyword_flexible ?? obj.flexible ?? false);
  return { entity_id, total_kwh, share_in_peak, flexible };
}

export function EvidencePanel({ evidence }: EvidencePanelProps) {
  const sections: React.ReactNode[] = [];

  // ── Cost savings highlight ─────────────────────────────────────────────────
  if ("estimated_cost_saving_usd" in evidence) {
    const saving = safeNum(evidence.estimated_cost_saving_usd);
    const shiftable = safeNum(evidence.total_shiftable_kwh);
    const peakRate = safeNum(evidence.assumed_peak_rate_usd_per_kwh);
    const offpeakRate = safeNum(evidence.assumed_offpeak_rate_usd_per_kwh);

    sections.push(
      <div key="savings" className="rounded-xl bg-green-500/5 p-4 ring-1 ring-green-500/20">
        <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-green-400">
          Estimated Savings
        </h4>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-bold text-green-400">
            ${formatNumber(saving)}
          </span>
          <span className="text-sm text-muted-foreground">potential savings</span>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
          <div>
            <p className="text-muted-foreground">Shiftable kWh</p>
            <p className="font-semibold">{formatNumber(shiftable)}</p>
          </div>
          {peakRate > 0 && (
            <div>
              <p className="text-muted-foreground">Peak rate</p>
              <p className="font-semibold">${peakRate}/kWh</p>
            </div>
          )}
          {offpeakRate > 0 && (
            <div>
              <p className="text-muted-foreground">Off-peak rate</p>
              <p className="font-semibold">${offpeakRate}/kWh</p>
            </div>
          )}
        </div>
      </div>,
    );
  }

  // ── Top consumers bar chart ────────────────────────────────────────────────
  if ("top_consumers" in evidence && Array.isArray(evidence.top_consumers)) {
    const rawConsumers = evidence.top_consumers as unknown[];
    const maxKwh = rawConsumers.reduce<number>((mx, r) => {
      if (r && typeof r === "object") {
        const obj = r as Record<string, unknown>;
        return Math.max(mx, safeNum(obj.total_kwh ?? obj.kwh));
      }
      return mx;
    }, 0);
    const consumers = rawConsumers
      .map((r) => normaliseConsumer(r, maxKwh))
      .filter(Boolean) as Array<{ entity_id: string; kwh: number; pct: number }>;

    if (consumers.length > 0) {
      sections.push(
        <div key="consumers">
          <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Top Energy Consumers
          </h4>
          <div className="space-y-2">
            {consumers.map((c) => {
              const shortName = c.entity_id.split(".").pop() ?? c.entity_id;
              return (
                <div key={c.entity_id} className="group/bar">
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span
                      className="truncate font-mono text-muted-foreground"
                      title={c.entity_id}
                    >
                      {shortName}
                    </span>
                    <div className="flex gap-3 text-right">
                      <span className="font-semibold">
                        {formatNumber(c.kwh)} kWh
                      </span>
                      {c.pct > 0 && (
                        <span className="w-12 text-muted-foreground">
                          {c.pct.toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-500"
                      style={{ width: `${Math.min(Math.max(c.pct * 2.5, 1), 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>,
      );
    }
  }

  // ── Peak / off-peak hours chart ────────────────────────────────────────────
  if ("peak_hours" in evidence && "off_peak_hours" in evidence) {
    const rawPeak = Array.isArray(evidence.peak_hours) ? evidence.peak_hours : [];
    const rawOffPeak = Array.isArray(evidence.off_peak_hours) ? evidence.off_peak_hours : [];

    const peakHours = rawPeak.map(normaliseHourEntry).filter(Boolean) as Array<{
      key: string; hour: number; kwh: number; pct: number;
    }>;
    const offPeakHours = rawOffPeak.map(normaliseHourEntry).filter(Boolean) as Array<{
      key: string; hour: number; kwh: number; pct: number;
    }>;
    const totalKwh = safeNum(evidence.hourly_profile_total_kwh) || 1;
    const hasDetailedPeak = peakHours.some((h) => h.kwh > 0 || h.pct > 0);

    if (peakHours.length > 0 || offPeakHours.length > 0) {
      sections.push(
        <div key="peak-hours">
          <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Peak &amp; Off-Peak Hours
          </h4>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-orange-500/5 p-3 ring-1 ring-orange-500/20">
              <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-orange-400">
                Peak Hours
              </p>
              {peakHours.map((h) => (
                <div
                  key={h.key}
                  className="flex items-center justify-between py-1 text-xs"
                >
                  <span className="font-mono text-muted-foreground">
                    {String(h.hour).padStart(2, "0")}:00
                  </span>
                  {hasDetailedPeak ? (
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-orange-400"
                          style={{
                            width: `${Math.min((h.kwh / totalKwh) * 100 * 4, 100)}%`,
                          }}
                        />
                      </div>
                      {h.pct > 0 && (
                        <span className="w-12 text-right font-semibold">
                          {h.pct.toFixed(1)}%
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="font-semibold text-orange-400">Peak</span>
                  )}
                </div>
              ))}
            </div>
            <div className="rounded-lg bg-blue-500/5 p-3 ring-1 ring-blue-500/20">
              <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-blue-400">
                Off-Peak Hours
              </p>
              {offPeakHours.map((h) => (
                <div
                  key={h.key}
                  className="flex items-center justify-between py-1 text-xs"
                >
                  <span className="font-mono text-muted-foreground">
                    {String(h.hour).padStart(2, "0")}:00
                  </span>
                  <span className="font-semibold text-blue-400">
                    {h.kwh === 0 ? "Idle" : `${formatNumber(h.kwh)} kWh`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>,
      );
    }
  }

  // ── Candidates table (shifting opportunities) ──────────────────────────────
  if ("candidates_reported" in evidence && Array.isArray(evidence.candidates_reported)) {
    const candidates = (evidence.candidates_reported as unknown[])
      .map(normaliseCandidate)
      .filter(Boolean) as Array<{
        entity_id: string; total_kwh: number; share_in_peak: number; flexible: boolean;
      }>;

    if (candidates.length > 0) {
      sections.push(
        <div key="candidates">
          <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Shifting Candidates
          </h4>
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                    Entity
                  </th>
                  <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                    kWh
                  </th>
                  <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                    Peak Share
                  </th>
                  <th className="px-3 py-2 text-center font-medium text-muted-foreground">
                    Flexible
                  </th>
                </tr>
              </thead>
              <tbody>
                {candidates.slice(0, 8).map((c) => {
                  const shortName =
                    c.entity_id.split(".").pop() ?? c.entity_id;
                  return (
                    <tr
                      key={c.entity_id}
                      className="border-b border-border/50 last:border-0"
                    >
                      <td
                        className="max-w-[180px] truncate px-3 py-2 font-mono"
                        title={c.entity_id}
                      >
                        {shortName}
                      </td>
                      <td className="px-3 py-2 text-right font-semibold">
                        {formatNumber(c.total_kwh)}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="h-1.5 w-12 overflow-hidden rounded-full bg-muted">
                            <div
                              className={cn(
                                "h-full rounded-full",
                                c.share_in_peak > 0.6
                                  ? "bg-red-400"
                                  : c.share_in_peak > 0.3
                                    ? "bg-orange-400"
                                    : "bg-green-400",
                              )}
                              style={{
                                width: `${c.share_in_peak * 100}%`,
                              }}
                            />
                          </div>
                          <span className="w-10 text-right">
                            {(c.share_in_peak * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-center">
                        {c.flexible ? (
                          <CheckCircle2 className="mx-auto h-3.5 w-3.5 text-green-400" />
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {candidates.length > 8 && (
              <div className="border-t border-border bg-muted/20 px-3 py-1.5 text-center text-[10px] text-muted-foreground">
                +{candidates.length - 8} more candidates
              </div>
            )}
          </div>
        </div>,
      );
    }
  }

  // ── Failed analysis ────────────────────────────────────────────────────────
  if ("exit_code" in evidence) {
    sections.push(
      <div
        key="failed"
        className="rounded-lg bg-red-500/5 p-4 ring-1 ring-red-500/20"
      >
        <div className="flex items-center gap-2 text-sm text-red-400">
          <XCircle className="h-4 w-4" />
          <span className="font-medium">Analysis Failed</span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Exit code: {String(evidence.exit_code)} | Timed out:{" "}
          {String(evidence.timed_out ?? false)}
        </p>
      </div>,
    );
  }

  if (sections.length === 0) {
    // Fallback: render evidence as formatted JSON
    return (
      <div>
        <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Evidence
        </h4>
        <pre className="overflow-auto rounded-lg bg-muted p-3 text-[11px] text-muted-foreground">
          {JSON.stringify(evidence, null, 2)}
        </pre>
      </div>
    );
  }

  return <div className="space-y-5">{sections}</div>;
}
