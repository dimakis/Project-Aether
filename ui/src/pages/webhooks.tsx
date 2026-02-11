import { useState } from "react";
import {
  Webhook,
  ArrowDownToLine,
  ArrowUpFromLine,
  Copy,
  Send,
  Loader2,
  CheckCircle,
  AlertCircle,
  Info,
  TriangleAlert,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useInsightSchedules, useSystemStatus } from "@/api/hooks";
import { request } from "@/api/client/core";

// ─── Webhook Test ─────────────────────────────────────────────────────────────

function WebhookTester() {
  const [eventType, setEventType] = useState("state_changed");
  const [entityId, setEntityId] = useState("");
  const [webhookEvent, setWebhookEvent] = useState("");
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleTest = async () => {
    setTesting(true);
    setResult(null);
    try {
      const payload: Record<string, unknown> = {
        event_type: eventType,
        data: {},
      };
      if (entityId) payload.entity_id = entityId;
      if (webhookEvent) payload.webhook_event = webhookEvent;

      const res = await request<{ status: string; matched_schedules: number }>(
        "/webhooks/ha",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      );
      setResult({
        success: true,
        message: `Matched ${res.matched_schedules} schedule(s)`,
      });
    } catch (e: unknown) {
      setResult({
        success: false,
        message: e instanceof Error ? e.message : "Test failed",
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Send className="h-4 w-4 text-primary" />
          Test Webhook
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-3">
          <Input
            placeholder="Event type"
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
          />
          <Input
            placeholder="Entity ID (optional)"
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
          />
          <Input
            placeholder="Webhook event label"
            value={webhookEvent}
            onChange={(e) => setWebhookEvent(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-3">
          <Button
            size="sm"
            onClick={handleTest}
            disabled={testing || !eventType}
          >
            {testing ? (
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="mr-1.5 h-3.5 w-3.5" />
            )}
            Send Test
          </Button>
          {result && (
            <div className="flex items-center gap-1.5 text-sm">
              {result.success ? (
                <CheckCircle className="h-4 w-4 text-emerald-400" />
              ) : (
                <AlertCircle className="h-4 w-4 text-destructive" />
              )}
              <span
                className={
                  result.success ? "text-emerald-400" : "text-destructive"
                }
              >
                {result.message}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Setup Guide ──────────────────────────────────────────────────────────────

function SetupGuide({ publicUrl }: { publicUrl?: string | null }) {
  const browserOrigin =
    typeof window !== "undefined" ? window.location.origin : "";
  const baseUrl = publicUrl || browserOrigin;
  const webhookUrl = `${baseUrl}/api/v1/webhooks/ha`;
  const usingFallback = !publicUrl;
  const [copied, setCopied] = useState(false);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Info className="h-4 w-4 text-blue-400" />
          Setup Guide
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            1. Webhook URL
          </h4>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded-md bg-muted px-3 py-2 font-mono text-xs">
              {webhookUrl}
            </code>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                navigator.clipboard.writeText(webhookUrl);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
            >
              {copied ? (
                <CheckCircle className="h-4 w-4 text-emerald-400" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
          {usingFallback && (
            <div className="mt-2 flex items-start gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 p-2">
              <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
              <p className="text-[11px] text-amber-300/80">
                Using your browser URL. If HA cannot reach this address, set{" "}
                <code className="rounded bg-muted px-1 font-mono">PUBLIC_URL</code>{" "}
                in your <code className="rounded bg-muted px-1 font-mono">.env</code>{" "}
                to the externally reachable URL of this Aether instance.
              </p>
            </div>
          )}
        </div>

        <div>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            2. HA Automation Example
          </h4>
          <pre className="rounded-md bg-muted p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">
{`automation:
  - alias: "Notify Aether on device offline"
    trigger:
      - platform: state
        entity_id: sensor.power_meter
        to: "unavailable"
    action:
      - service: rest_command.notify_aether
        data:
          event_type: state_changed
          entity_id: "{{ trigger.entity_id }}"
          webhook_event: device_offline
          data:
            new_state: "{{ trigger.to_state.state }}"
            old_state: "{{ trigger.from_state.state }}"`}
          </pre>
        </div>

        <div>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            3. REST Command Config
          </h4>
          <pre className="rounded-md bg-muted p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">
{`rest_command:
  notify_aether:
    url: "${webhookUrl}"
    method: POST
    content_type: "application/json"
    payload: >
      {{ data | tojson }}`}
          </pre>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function WebhooksPage() {
  const { data: schedulesData } = useInsightSchedules();
  const { data: status } = useSystemStatus();

  const webhookSchedules = (schedulesData?.items ?? []).filter(
    (s) => s.trigger_type === "webhook",
  );
  const enabledCount = webhookSchedules.filter((s) => s.enabled).length;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Webhooks</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage inbound triggers from Home Assistant and test webhook delivery
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="bg-card/50">
          <CardContent className="flex items-center gap-3 pt-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-400/10">
              <ArrowDownToLine className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{webhookSchedules.length}</p>
              <p className="text-xs text-muted-foreground">
                Inbound triggers
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50">
          <CardContent className="flex items-center gap-3 pt-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-400/10">
              <Webhook className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{enabledCount}</p>
              <p className="text-xs text-muted-foreground">Active</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50">
          <CardContent className="flex items-center gap-3 pt-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-400/10">
              <ArrowUpFromLine className="h-5 w-5 text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                <Badge variant="outline" className="text-xs">
                  via HA notify
                </Badge>
              </p>
              <p className="text-xs text-muted-foreground">
                Outbound method
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Webhook test */}
      <WebhookTester />

      {/* Active triggers */}
      {webhookSchedules.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold">
            Registered Webhook Triggers
          </h2>
          <div className="space-y-2">
            {webhookSchedules.map((s) => (
              <Card key={s.id} className="bg-card/50">
                <CardContent className="flex items-center gap-3 pt-3 pb-3">
                  <Webhook
                    className={`h-4 w-4 ${s.enabled ? "text-emerald-400" : "text-muted-foreground/30"}`}
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{s.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {s.webhook_event ?? "any event"} /{" "}
                      {s.analysis_type}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className={
                      s.enabled
                        ? "border-emerald-500/30 text-emerald-400"
                        : "text-muted-foreground"
                    }
                  >
                    {s.enabled ? "active" : "disabled"}
                  </Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Setup guide */}
      <SetupGuide publicUrl={status?.public_url} />
    </div>
  );
}
