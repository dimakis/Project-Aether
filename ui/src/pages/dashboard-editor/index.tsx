/**
 * DashboardEditorPage — hybrid Lovelace dashboard editor.
 *
 * Split-pane layout:
 *   Left:  Dashboard picker + YAML editor (read/edit Lovelace config)
 *   Right: Live HA iframe preview (or fallback when iframe is blocked)
 */

import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import {
  LayoutDashboard,
  ChevronDown,
  Loader2,
  AlertTriangle,
  ExternalLink,
  RefreshCw,
  Pencil,
  Eye,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import yaml from "js-yaml";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { YamlEditor } from "@/components/ui/yaml-editor";
import {
  useDashboards,
  useDashboardConfig,
  useHAZones,
  useCreateProposal,
} from "@/api/hooks";
import { cn } from "@/lib/utils";

// ─── Types ──────────────────────────────────────────────────────────────────

type IframeStatus = "loading" | "loaded" | "blocked" | "error";

// ─── Dashboard Picker ───────────────────────────────────────────────────────

function DashboardPicker({
  dashboards,
  selected,
  onSelect,
}: {
  dashboards: Array<{ url_path: string; title: string; mode: string }>;
  selected: string | null;
  onSelect: (urlPath: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const current = dashboards.find((d) => d.url_path === selected);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex w-full items-center justify-between gap-2 rounded-lg border border-border",
          "bg-muted/30 px-3 py-2 text-sm font-medium transition-colors",
          "hover:bg-accent hover:text-accent-foreground",
        )}
      >
        <div className="flex items-center gap-2">
          <LayoutDashboard className="h-4 w-4 text-muted-foreground" />
          <span>{current?.title ?? "Select a dashboard..."}</span>
          {current && (
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
              {current.mode}
            </span>
          )}
        </div>
        <ChevronDown
          className={cn(
            "h-4 w-4 text-muted-foreground transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-64 overflow-y-auto rounded-lg border border-border bg-card shadow-lg">
          {/* Default dashboard option */}
          <button
            onClick={() => {
              onSelect("default");
              setOpen(false);
            }}
            className={cn(
              "flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors",
              "hover:bg-accent hover:text-accent-foreground",
              selected === "default" && "bg-primary/10 text-primary",
            )}
          >
            <LayoutDashboard className="h-3.5 w-3.5" />
            <span>Default Overview</span>
            <span className="ml-auto rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              built-in
            </span>
          </button>

          {dashboards.map((db) => (
            <button
              key={db.url_path}
              onClick={() => {
                onSelect(db.url_path);
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                selected === db.url_path && "bg-primary/10 text-primary",
              )}
            >
              <LayoutDashboard className="h-3.5 w-3.5" />
              <span>{db.title}</span>
              <span className="ml-auto rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                {db.mode}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── iframe Preview ─────────────────────────────────────────────────────────

function IframePreview({
  haUrl,
  dashboardPath,
}: {
  haUrl: string | null;
  dashboardPath: string | null;
}) {
  const [status, setStatus] = useState<IframeStatus>("loading");
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const iframeUrl = useMemo(() => {
    if (!haUrl || !dashboardPath) return null;
    const base = haUrl.replace(/\/+$/, "");
    const path =
      dashboardPath === "default" ? "lovelace/0" : `lovelace/${dashboardPath}`;
    return `${base}/${path}`;
  }, [haUrl, dashboardPath]);

  // Reset status when URL changes
  useEffect(() => {
    if (iframeUrl) {
      setStatus("loading");
      // If the iframe doesn't fire onLoad within 10s, assume blocked
      timerRef.current = setTimeout(() => {
        setStatus((prev) => (prev === "loading" ? "blocked" : prev));
      }, 10_000);
    }
    return () => clearTimeout(timerRef.current);
  }, [iframeUrl]);

  const handleLoad = useCallback(() => {
    clearTimeout(timerRef.current);
    setStatus("loaded");
  }, []);

  const handleError = useCallback(() => {
    clearTimeout(timerRef.current);
    setStatus("error");
  }, []);

  const handleRefresh = useCallback(() => {
    setStatus("loading");
    if (iframeRef.current && iframeUrl) {
      iframeRef.current.src = iframeUrl;
      timerRef.current = setTimeout(() => {
        setStatus((prev) => (prev === "loading" ? "blocked" : prev));
      }, 10_000);
    }
  }, [iframeUrl]);

  // ─── No HA URL configured ─────────────────────────────────────────────
  if (!haUrl) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
        <AlertTriangle className="h-8 w-8" />
        <p className="text-sm font-medium">No HA connection configured</p>
        <p className="text-xs">
          Add a Home Assistant zone in Settings to enable live preview.
        </p>
      </div>
    );
  }

  // ─── No dashboard selected ────────────────────────────────────────────
  if (!iframeUrl) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
        <Eye className="h-8 w-8" />
        <p className="text-sm font-medium">Select a dashboard to preview</p>
      </div>
    );
  }

  return (
    <div className="relative h-full">
      {/* Status bar */}
      <div className="flex items-center justify-between border-b border-border bg-muted/20 px-3 py-1.5">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {status === "loading" && (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Loading preview...</span>
            </>
          )}
          {status === "loaded" && (
            <>
              <div className="h-2 w-2 rounded-full bg-emerald-400" />
              <span>Live preview</span>
            </>
          )}
          {(status === "blocked" || status === "error") && (
            <>
              <AlertTriangle className="h-3 w-3 text-amber-400" />
              <span>
                {status === "blocked"
                  ? "iframe blocked by HA"
                  : "Failed to load"}
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            className="h-6 w-6 p-0"
            title="Refresh preview"
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 gap-1 px-1.5 text-[10px]"
            onClick={() => window.open(iframeUrl, "_blank")}
            title="Open in Home Assistant"
          >
            <ExternalLink className="h-3 w-3" />
            Open in HA
          </Button>
        </div>
      </div>

      {/* iframe or fallback */}
      {status === "blocked" || status === "error" ? (
        <div className="flex h-[calc(100%-36px)] flex-col items-center justify-center gap-4 p-6 text-center">
          <AlertTriangle className="h-10 w-10 text-amber-400" />
          <div>
            <p className="text-sm font-medium">
              {status === "blocked"
                ? "Home Assistant is blocking embedded preview"
                : "Could not load the dashboard preview"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {status === "blocked"
                ? "HA may have X-Frame-Options or CSP headers that prevent iframe embedding from a different origin."
                : "Check that Home Assistant is reachable from your browser."}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(iframeUrl, "_blank")}
              className="gap-1.5"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open in Home Assistant
            </Button>
            <Button variant="ghost" size="sm" onClick={handleRefresh}>
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </Button>
          </div>
        </div>
      ) : (
        <iframe
          ref={iframeRef}
          src={iframeUrl}
          className="h-[calc(100%-36px)] w-full border-0"
          onLoad={handleLoad}
          onError={handleError}
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          title="Home Assistant Dashboard Preview"
        />
      )}
    </div>
  );
}

// ─── Structured Preview ──────────────────────────────────────────────────────

/** Tree-based preview of dashboard structure: views → sections → cards. */
function DashboardStructurePreview({
  config,
}: {
  config: Record<string, unknown> | null;
}) {
  const [expandedViews, setExpandedViews] = useState<Set<number>>(new Set());

  if (!config) return null;

  const views = (config.views ?? []) as Array<Record<string, unknown>>;
  if (views.length === 0) return null;

  const toggleView = (idx: number) => {
    setExpandedViews((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <div className="space-y-1">
      <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Structure
      </h4>
      <div className="rounded-lg border border-border bg-muted/20 text-xs">
        {views.map((view, vi) => {
          const viewTitle = (view.title as string) ?? `View ${vi + 1}`;
          const sections = (view.sections ?? []) as Array<
            Record<string, unknown>
          >;
          const cards = (view.cards ?? []) as Array<Record<string, unknown>>;
          const isExpanded = expandedViews.has(vi);

          return (
            <div key={vi} className="border-b border-border/50 last:border-0">
              <button
                onClick={() => toggleView(vi)}
                className={cn(
                  "flex w-full items-center gap-2 px-3 py-1.5 text-left transition-colors",
                  "hover:bg-accent/50",
                )}
              >
                <ChevronDown
                  className={cn(
                    "h-3 w-3 text-muted-foreground transition-transform",
                    !isExpanded && "-rotate-90",
                  )}
                />
                <LayoutDashboard className="h-3 w-3 text-primary" />
                <span className="font-medium">{viewTitle}</span>
                <span className="ml-auto text-muted-foreground">
                  {cards.length > 0 && `${cards.length} card${cards.length !== 1 ? "s" : ""}`}
                  {sections.length > 0 &&
                    `${sections.length} section${sections.length !== 1 ? "s" : ""}`}
                </span>
              </button>

              {isExpanded && (
                <div className="pb-1.5 pl-8 pr-3">
                  {/* Sections */}
                  {sections.map((section, si) => {
                    const sectionTitle =
                      (section.title as string) ?? `Section ${si + 1}`;
                    const sectionCards = (section.cards ?? []) as Array<
                      Record<string, unknown>
                    >;
                    return (
                      <div key={`s-${si}`} className="mt-1">
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                          <span className="font-medium text-foreground">
                            {sectionTitle}
                          </span>
                          <span>
                            · {sectionCards.length} card
                            {sectionCards.length !== 1 ? "s" : ""}
                          </span>
                        </div>
                        <div className="ml-3 mt-0.5 space-y-0.5">
                          {sectionCards.map((card, ci) => (
                            <CardNode key={`sc-${ci}`} card={card} />
                          ))}
                        </div>
                      </div>
                    );
                  })}

                  {/* Direct cards */}
                  {cards.length > 0 && (
                    <div className="mt-1 space-y-0.5">
                      {cards.map((card, ci) => (
                        <CardNode key={`c-${ci}`} card={card} />
                      ))}
                    </div>
                  )}

                  {sections.length === 0 && cards.length === 0 && (
                    <p className="py-1 text-muted-foreground italic">
                      Empty view
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Renders a single card node in the tree. */
function CardNode({ card }: { card: Record<string, unknown> }) {
  const cardType = (card.type as string) ?? "unknown";
  const cardTitle = (card.title as string) ?? (card.name as string) ?? null;
  const entity = card.entity as string | undefined;

  return (
    <div className="flex items-center gap-1.5 text-muted-foreground">
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary/50" />
      <span className="font-mono text-foreground">{cardType}</span>
      {cardTitle && <span>— {cardTitle}</span>}
      {!cardTitle && entity && (
        <span className="font-mono text-[10px]">{entity}</span>
      )}
    </div>
  );
}

// ─── Main Page ──────────────────────────────────────────────────────────────

export function DashboardEditorPage() {
  const [selectedDashboard, setSelectedDashboard] = useState<string | null>(
    null,
  );
  const [isEditing, setIsEditing] = useState(false);
  const [submitFeedback, setSubmitFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Fetch dashboards list
  const { data: dashboardList, isLoading: loadingList, error: listError } = useDashboards();

  // Fetch config for selected dashboard
  const { data: dashboardConfig, isLoading: loadingConfig } =
    useDashboardConfig(selectedDashboard);

  // Auto-select the first available dashboard when data loads
  useEffect(() => {
    if (selectedDashboard) return; // user already picked one
    if (dashboardList && dashboardList.length > 0) {
      setSelectedDashboard(dashboardList[0].url_path);
    } else if (dashboardList !== undefined) {
      // List loaded but empty — fall back to the built-in default
      setSelectedDashboard("default");
    }
  }, [dashboardList, selectedDashboard]);

  // Get HA URL from zones (default zone).
  // The iframe runs in the user's browser, not the backend server,
  // so prefer ha_url_remote when available.
  // Falls back to VITE_HA_URL env var if no zones are configured.
  const { data: zones } = useHAZones();
  const defaultZone = zones?.find((z) => z.is_default) ?? zones?.[0];
  const haUrl = useMemo(() => {
    const viteHaUrl = (import.meta as unknown as { env: Record<string, string> }).env.VITE_HA_URL;
    if (!defaultZone) return viteHaUrl || null;
    const { ha_url, ha_url_remote, url_preference } = defaultZone;
    if (url_preference === "local") return ha_url || viteHaUrl || null;
    if (url_preference === "remote") return ha_url_remote ?? ha_url ?? viteHaUrl ?? null;
    // "auto" — prefer remote for browser context, fall back to local
    return ha_url_remote ?? ha_url ?? viteHaUrl ?? null;
  }, [defaultZone]);

  // Create proposal mutation
  const createProposal = useCreateProposal();

  // Convert config to YAML for the editor
  const configYaml = useMemo(() => {
    if (!dashboardConfig) return "";
    try {
      return yaml.dump(dashboardConfig, {
        indent: 2,
        lineWidth: 120,
        noRefs: true,
        sortKeys: false,
      });
    } catch {
      return "# Error converting config to YAML";
    }
  }, [dashboardConfig]);

  // Clear feedback after 5 seconds
  useEffect(() => {
    if (!submitFeedback) return;
    const timer = setTimeout(() => setSubmitFeedback(null), 5000);
    return () => clearTimeout(timer);
  }, [submitFeedback]);

  const handleSubmitEdit = useCallback(
    (editedYaml: string) => {
      // Parse the edited YAML into a config object
      let parsedConfig: Record<string, unknown>;
      try {
        parsedConfig = yaml.load(editedYaml) as Record<string, unknown>;
        if (!parsedConfig || typeof parsedConfig !== "object") {
          setSubmitFeedback({
            type: "error",
            message: "Invalid YAML: config must be an object.",
          });
          return;
        }
      } catch (e) {
        setSubmitFeedback({
          type: "error",
          message: `Invalid YAML: ${e instanceof Error ? e.message : "parse error"}`,
        });
        return;
      }

      const dashTitle =
        (parsedConfig.title as string) ?? selectedDashboard ?? "Dashboard";
      const urlPath =
        selectedDashboard === "default" ? undefined : selectedDashboard;

      createProposal.mutate(
        {
          name: `Dashboard update: ${dashTitle}`,
          description: `Lovelace config update for "${dashTitle}" dashboard`,
          proposal_type: "dashboard",
          dashboard_config: parsedConfig,
          service_call: { url_path: urlPath ?? null },
          trigger: {},
          actions: {},
        },
        {
          onSuccess: () => {
            setSubmitFeedback({
              type: "success",
              message:
                "Dashboard proposal submitted for approval. View it on the Proposals page.",
            });
            setIsEditing(false);
          },
          onError: (err) => {
            setSubmitFeedback({
              type: "error",
              message: `Failed to create proposal: ${err instanceof Error ? err.message : "unknown error"}`,
            });
          },
        },
      );
    },
    [selectedDashboard, createProposal],
  );

  return (
    <div className="flex h-[calc(100vh-theme(spacing.14))] flex-col">
      {/* Page header */}
      <div className="flex shrink-0 items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            Dashboard Editor
          </h1>
          <p className="text-xs text-muted-foreground">
            View and edit Lovelace dashboard configurations with live HA preview
          </p>
        </div>
      </div>

      {/* Split pane content */}
      <div className="flex min-h-0 flex-1">
        {/* ─── Left pane: Picker + YAML editor ─────────────────────────── */}
        <div className="flex w-1/2 flex-col border-r border-border">
          {/* Dashboard picker */}
          <div className="shrink-0 border-b border-border p-4">
            {loadingList ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading dashboards...
              </div>
            ) : (
              <>
                <DashboardPicker
                  dashboards={dashboardList ?? []}
                  selected={selectedDashboard}
                  onSelect={setSelectedDashboard}
                />
                {listError && (
                  <div className="mt-2 flex items-center gap-2 rounded-md bg-amber-400/10 px-3 py-1.5 text-xs text-amber-400">
                    <AlertTriangle className="h-3 w-3 shrink-0" />
                    <span>Could not load dashboards from HA. Only the default overview is available.</span>
                  </div>
                )}
              </>
            )}
          </div>

          {/* YAML editor area */}
          <div className="flex-1 overflow-auto p-4">
            {!selectedDashboard ? (
              <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
                <LayoutDashboard className="h-8 w-8" />
                <p className="text-sm font-medium">No dashboard selected</p>
                <p className="text-xs">
                  Choose a dashboard above to view its Lovelace configuration.
                </p>
              </div>
            ) : loadingConfig ? (
              <div className="flex h-32 items-center justify-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading configuration...
              </div>
            ) : !dashboardConfig ? (
              <Card>
                <CardContent className="flex flex-col items-center gap-2 py-8 text-center">
                  <AlertTriangle className="h-6 w-6 text-amber-400" />
                  <p className="text-sm font-medium">
                    Could not load dashboard config
                  </p>
                  <p className="text-xs text-muted-foreground">
                    This dashboard may use YAML mode or may not be accessible
                    via the API.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {/* Config header with edit toggle */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-medium">
                      Lovelace Configuration
                    </h3>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                      {dashboardConfig.views?.length ?? 0} view
                      {(dashboardConfig.views?.length ?? 0) !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsEditing(!isEditing)}
                    className="h-7 gap-1.5 text-xs"
                  >
                    {isEditing ? (
                      <>
                        <Eye className="h-3 w-3" />
                        View
                      </>
                    ) : (
                      <>
                        <Pencil className="h-3 w-3" />
                        Edit
                      </>
                    )}
                  </Button>
                </div>

                {/* Feedback banner */}
                {submitFeedback && (
                  <div
                    className={cn(
                      "flex items-center gap-2 rounded-lg px-3 py-2 text-sm",
                      submitFeedback.type === "success"
                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        : "bg-destructive/10 text-destructive",
                    )}
                  >
                    {submitFeedback.type === "success" ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 shrink-0" />
                    )}
                    <span>{submitFeedback.message}</span>
                  </div>
                )}

                {isEditing && (
                  <p className="text-xs text-muted-foreground">
                    Edits are submitted as a proposal for HITL approval before
                    deployment to Home Assistant.
                  </p>
                )}

                <YamlEditor
                  originalYaml={configYaml}
                  isEditing={isEditing}
                  onSubmitEdit={handleSubmitEdit}
                  onCancelEdit={() => setIsEditing(false)}
                  maxHeight={600}
                />

                {/* Collapsible structure preview */}
                <DashboardStructurePreview config={dashboardConfig} />
              </div>
            )}
          </div>
        </div>

        {/* ─── Right pane: iframe preview ──────────────────────────────── */}
        <div className="w-1/2">
          <IframePreview
            haUrl={haUrl}
            dashboardPath={selectedDashboard}
          />
        </div>
      </div>
    </div>
  );
}
