import { useState, useEffect, useRef, useCallback } from "react";
import {
  Bell,
  CheckCircle,
  XCircle,
  Loader2,
  Send,
  Smartphone,
  RefreshCw,
  ShieldCheck,
  ThumbsUp,
  ThumbsDown,
  Clock,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { request } from "@/api/client";

interface NotifyService {
  id: string;
  label: string;
}

interface TestResult {
  success: boolean;
  service: string;
  error?: string;
  result?: unknown;
  test_proposal_id?: string;
  skipped?: boolean;
  reason?: string;
}

interface ActionStatus {
  received: boolean;
  action?: "approve" | "reject";
  status?: string;
  timestamp?: number;
}

export default function HITLTestPage() {
  const [services, setServices] = useState<NotifyService[]>([]);
  const [selectedService, setSelectedService] = useState("");
  const [customService, setCustomService] = useState("");
  const [loadingServices, setLoadingServices] = useState(false);
  const [testMessage, setTestMessage] = useState(
    "Hello from Aether! Testing push notifications.",
  );
  const [approvalTitle, setApprovalTitle] = useState("Preheat Oven");
  const [approvalDesc, setApprovalDesc] = useState(
    "Preheat oven to 200C for pizza",
  );
  const [sendingTest, setSendingTest] = useState(false);
  const [sendingApproval, setSendingApproval] = useState(false);
  const [lastResult, setLastResult] = useState<TestResult | null>(null);
  const [actionStatus, setActionStatus] = useState<ActionStatus | null>(null);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const effectiveService = customService || selectedService;

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setPolling(false);
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  async function discoverServices() {
    setLoadingServices(true);
    try {
      const data = await request<{ services: string[]; count: number }>(
        "/hitl/notify-services",
      );
      const svcs: NotifyService[] = (data.services || []).map((s: string) => ({
        id: s,
        label: s.replace("notify.mobile_app_", "").replaceAll("_", " "),
      }));
      setServices(svcs);
      if (svcs.length > 0 && !selectedService) {
        setSelectedService(svcs[0].id);
      }
    } catch {
      setServices([]);
    } finally {
      setLoadingServices(false);
    }
  }

  useEffect(() => {
    discoverServices();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function sendTestNotification() {
    if (!effectiveService) return;
    setSendingTest(true);
    setLastResult(null);
    setActionStatus(null);
    stopPolling();
    try {
      const data = await request<TestResult>("/hitl/test-notification", {
        method: "POST",
        body: JSON.stringify({
          notify_service: effectiveService,
          message: testMessage,
        }),
      });
      setLastResult(data);
    } catch (e) {
      setLastResult({
        success: false,
        service: effectiveService,
        error: String(e),
      });
    } finally {
      setSendingTest(false);
    }
  }

  function startPolling(proposalId: string) {
    stopPolling();
    setPolling(true);
    setActionStatus(null);

    let attempts = 0;
    const maxAttempts = 60; // 2 minutes at 2s intervals

    pollRef.current = setInterval(async () => {
      attempts++;
      if (attempts > maxAttempts) {
        stopPolling();
        setActionStatus({ received: false });
        return;
      }
      try {
        const status = await request<ActionStatus>(
          `/hitl/action-status/${proposalId}`,
        );
        if (status.received) {
          setActionStatus(status);
          stopPolling();
        }
      } catch {
        // keep polling
      }
    }, 2000);
  }

  async function sendTestApproval() {
    if (!effectiveService) return;
    setSendingApproval(true);
    setLastResult(null);
    setActionStatus(null);
    stopPolling();
    try {
      const data = await request<TestResult>("/hitl/test-approval", {
        method: "POST",
        body: JSON.stringify({
          notify_service: effectiveService,
          title: approvalTitle,
          description: approvalDesc,
        }),
      });
      setLastResult(data);
      if (data.success && data.test_proposal_id) {
        startPolling(data.test_proposal_id);
      }
    } catch (e) {
      setLastResult({
        success: false,
        service: effectiveService,
        error: String(e),
      });
    } finally {
      setSendingApproval(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Push Notification HITL</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Test and configure approval notifications for iPhone / Apple Watch
        </p>
      </div>

      {/* Service Discovery */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Smartphone className="h-4 w-4" />
            Notify Service
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Label className="text-xs text-muted-foreground">
                Discovered services from HA
              </Label>
              {loadingServices ? (
                <div className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Discovering...
                </div>
              ) : services.length > 0 ? (
                <select
                  value={selectedService}
                  onChange={(e) => {
                    setSelectedService(e.target.value);
                    setCustomService("");
                  }}
                  className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                >
                  {services.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label} ({s.id})
                    </option>
                  ))}
                </select>
              ) : (
                <p className="py-2 text-sm text-muted-foreground">
                  No mobile_app services found. Enter one manually below.
                </p>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={discoverServices}
              disabled={loadingServices}
            >
              <RefreshCw
                className={`h-4 w-4 ${loadingServices ? "animate-spin" : ""}`}
              />
            </Button>
          </div>

          <div>
            <Label
              htmlFor="custom-service"
              className="text-xs text-muted-foreground"
            >
              Or enter manually (e.g. notify.mobile_app_dans_iphone)
            </Label>
            <Input
              id="custom-service"
              value={customService}
              onChange={(e) => setCustomService(e.target.value)}
              placeholder="notify.mobile_app_your_device"
              className="mt-1"
            />
          </div>

          {effectiveService && (
            <div className="rounded-md bg-accent/30 px-3 py-2 text-sm">
              Using:{" "}
              <code className="font-mono text-primary">{effectiveService}</code>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Test Simple Notification */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Bell className="h-4 w-4" />
            Step 1: Test Simple Notification
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Send a plain notification to verify the service name and
            connectivity.
          </p>
          <div>
            <Label htmlFor="test-message">Message</Label>
            <Input
              id="test-message"
              value={testMessage}
              onChange={(e) => setTestMessage(e.target.value)}
              className="mt-1"
            />
          </div>
          <Button
            onClick={sendTestNotification}
            disabled={!effectiveService || sendingTest}
            className="w-full"
          >
            {sendingTest ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Send className="mr-2 h-4 w-4" />
            )}
            Send Test Notification
          </Button>
        </CardContent>
      </Card>

      {/* Test Approval Notification */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-4 w-4" />
            Step 2: Test Approval Flow
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Send an actionable notification with Approve/Reject buttons. After
            sending, tap a button on your phone or watch — the response will
            appear below in real time.
          </p>
          <div>
            <Label htmlFor="approval-title">Title</Label>
            <Input
              id="approval-title"
              value={approvalTitle}
              onChange={(e) => setApprovalTitle(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="approval-desc">Description</Label>
            <Input
              id="approval-desc"
              value={approvalDesc}
              onChange={(e) => setApprovalDesc(e.target.value)}
              className="mt-1"
            />
          </div>
          <Button
            onClick={sendTestApproval}
            disabled={!effectiveService || sendingApproval}
            className="w-full"
            variant="default"
          >
            {sendingApproval ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ShieldCheck className="mr-2 h-4 w-4" />
            )}
            Send Approval Notification
          </Button>
        </CardContent>
      </Card>

      {/* Send Result */}
      {lastResult && (
        <Card
          className={
            lastResult.success ? "border-emerald-500/30" : "border-red-500/30"
          }
        >
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              {lastResult.success ? (
                <CheckCircle className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500" />
              ) : (
                <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
              )}
              <div className="min-w-0 flex-1">
                <p className="font-medium">
                  {lastResult.success ? "Notification sent!" : "Failed to send"}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Service: <code>{lastResult.service}</code>
                </p>
                {lastResult.error && (
                  <p className="mt-1 text-sm text-red-400">
                    Error: {String(lastResult.error)}
                  </p>
                )}
                {lastResult.skipped && (
                  <p className="mt-1 text-sm text-amber-400">
                    Skipped: {lastResult.reason}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Approval Action Response */}
      {lastResult?.success && lastResult.test_proposal_id && (
        <Card
          className={
            actionStatus?.received
              ? actionStatus.action === "approve"
                ? "border-emerald-500/50 bg-emerald-500/5"
                : "border-red-500/50 bg-red-500/5"
              : "border-border"
          }
        >
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              {actionStatus?.received ? (
                actionStatus.action === "approve" ? (
                  <ThumbsUp className="h-4 w-4 text-emerald-500" />
                ) : (
                  <ThumbsDown className="h-4 w-4 text-red-500" />
                )
              ) : polling ? (
                <Clock className="h-4 w-4 animate-pulse text-amber-400" />
              ) : (
                <Clock className="h-4 w-4 text-muted-foreground" />
              )}
              Action Response
            </CardTitle>
          </CardHeader>
          <CardContent>
            {actionStatus?.received ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      actionStatus.action === "approve"
                        ? "bg-emerald-500/15 text-emerald-400"
                        : "bg-red-500/15 text-red-400"
                    }`}
                  >
                    {actionStatus.action === "approve"
                      ? "Approved"
                      : "Rejected"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    via push notification
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  The full HITL approval flow is working. When a real mutating
                  action creates a proposal, the same Approve/Reject buttons
                  will appear on your phone and the action will execute on
                  approval.
                </p>
                <p className="text-xs text-muted-foreground">
                  Proposal: <code>{lastResult.test_proposal_id}</code>
                </p>
              </div>
            ) : polling ? (
              <div className="flex items-center gap-3">
                <Loader2 className="h-4 w-4 animate-spin text-amber-400" />
                <div>
                  <p className="text-sm">
                    Waiting for you to tap Approve or Reject...
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Check your phone or Apple Watch for the notification.
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Polling timed out. The webhook may not have been configured in
                HA, or the notification was dismissed without tapping an action
                button.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
