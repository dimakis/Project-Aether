/**
 * Global SSE subscription for system-wide LLM activity events.
 *
 * Connects to /api/v1/activity/stream and updates the agent activity
 * store so the neural panel reacts to ALL LLM calls — not just chat.
 *
 * Source coordination: when the chat stream is active (isActive === true
 * and the chat page owns the stream), global events are silently
 * dropped to prevent conflicting state updates.
 */

import { useEffect, useRef } from "react";
import {
  setAgentActivity,
  completeAgentActivity,
  getActivitySnapshot,
  registerJob,
  updateJobStatus,
  type JobType,
} from "@/lib/agent-activity-store";

const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;

export function useGlobalActivityStream() {
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const esRef = useRef<EventSource | null>(null);
  /** Track all auto-complete timeouts so we can cancel on unmount. */
  const pendingTimeouts = useRef(new Set<ReturnType<typeof setTimeout>>());

  useEffect(() => {
    function connect() {
      if (esRef.current) {
        esRef.current.close();
      }

      const apiBase =
        (import.meta as unknown as { env: Record<string, string> }).env
          .VITE_API_BASE_URL ?? "";
      const url = `${apiBase}/api/v1/activity/stream`;
      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        retriesRef.current = 0;
      };

      es.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);

          // ─── Job lifecycle events ───────────────────────────────
          if (data.type === "job") {
            const jobId: string = data.job_id;
            const event: string = data.event;

            if (event === "start") {
              registerJob({
                jobId,
                jobType: (data.job_type ?? "other") as JobType,
                title: data.title ?? "Job",
                status: "running",
                startedAt: (data.ts ?? Date.now() / 1000) * 1000,
              });

              const snap = getActivitySnapshot();
              if (!snap.isActive) {
                setAgentActivity({
                  isActive: true,
                  activeAgent: null,
                  agentsSeen: ["aether"],
                  agentStates: { aether: "firing" },
                  liveTimeline: [
                    { ts: data.ts ?? Date.now() / 1000, event: "start", agent: data.job_type ?? "system" },
                  ],
                });
              }
            } else if (event === "agent_start" && data.agent) {
              const snap = getActivitySnapshot();
              const nextStates = { ...snap.agentStates };
              nextStates[data.agent] = "firing";
              const seen = snap.agentsSeen.includes(data.agent)
                ? snap.agentsSeen
                : [...snap.agentsSeen, data.agent];
              setAgentActivity({
                isActive: true,
                activeAgent: data.agent,
                agentsSeen: seen,
                agentStates: nextStates,
                liveTimeline: [
                  ...snap.liveTimeline,
                  { ts: data.ts ?? Date.now() / 1000, event: "start", agent: data.agent },
                ],
              });
            } else if (event === "agent_end" && data.agent) {
              const snap = getActivitySnapshot();
              const nextStates = { ...snap.agentStates };
              nextStates[data.agent] = "done";
              setAgentActivity({
                agentStates: nextStates,
                liveTimeline: [
                  ...snap.liveTimeline,
                  { ts: data.ts ?? Date.now() / 1000, event: "end", agent: data.agent },
                ],
              });
            } else if (event === "status" && data.message) {
              const snap = getActivitySnapshot();
              setAgentActivity({
                liveTimeline: [
                  ...snap.liveTimeline,
                  { ts: data.ts ?? Date.now() / 1000, event: "status", agent: data.agent ?? "system", tool: data.message },
                ],
              });
            } else if (event === "complete") {
              updateJobStatus(jobId, "completed");
              const handle = setTimeout(() => {
                pendingTimeouts.current.delete(handle);
                const latest = getActivitySnapshot();
                const stillFiring = Object.values(latest.agentStates).some((v) => v === "firing");
                if (!stillFiring) completeAgentActivity();
              }, 1500);
              pendingTimeouts.current.add(handle);
            } else if (event === "failed") {
              updateJobStatus(jobId, "failed");
              completeAgentActivity();
            }
            return;
          }

          // ─── Legacy LLM activity events ─────────────────────────
          if (data.type !== "llm") return;

          const snap = getActivitySnapshot();

          // If the chat stream is driving state, defer to it.
          if (snap.isActive) return;

          const role: string = data.agent_role ?? "system";

          if (data.event === "start") {
            // Mark this agent as firing; set system as active
            const nextStates = { ...snap.agentStates };
            nextStates[role] = "firing";
            nextStates["aether"] = "firing";

            const seen = snap.agentsSeen.includes(role)
              ? snap.agentsSeen
              : [...snap.agentsSeen, role];

            setAgentActivity({
              isActive: true,
              activeAgent: role,
              agentsSeen: seen,
              agentStates: nextStates,
              liveTimeline: [
                ...snap.liveTimeline,
                {
                  ts: data.ts ?? Date.now() / 1000,
                  event: "start",
                  agent: role,
                },
              ],
            });
          } else if (data.event === "end") {
            const nextStates = { ...snap.agentStates };
            nextStates[role] = "done";
            const anyOtherFiring = Object.entries(nextStates).some(
              ([k, v]) => k !== "aether" && k !== role && v === "firing",
            );
            if (!anyOtherFiring) {
              nextStates["aether"] = "done";
            }

            setAgentActivity({
              activeAgent: anyOtherFiring ? snap.activeAgent : null,
              agentStates: nextStates,
              liveTimeline: [
                ...snap.liveTimeline,
                {
                  ts: data.ts ?? Date.now() / 1000,
                  event: "end",
                  agent: role,
                  tool: data.latency_ms
                    ? `${data.model} (${data.latency_ms}ms)`
                    : data.model,
                },
              ],
            });

            // If nothing is still firing, transition to completed after a delay
            if (!anyOtherFiring) {
              const handle = setTimeout(() => {
                pendingTimeouts.current.delete(handle);
                const latest = getActivitySnapshot();
                const stillFiring = Object.values(latest.agentStates).some(
                  (v) => v === "firing",
                );
                if (!stillFiring) {
                  completeAgentActivity();
                }
              }, 2000);
              pendingTimeouts.current.add(handle);
            }
          }
        } catch {
          // Ignore parse errors from malformed SSE data
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        const delay = Math.min(
          RECONNECT_BASE_MS * 2 ** retriesRef.current,
          RECONNECT_MAX_MS,
        );
        retriesRef.current++;
        timerRef.current = setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (esRef.current) esRef.current.close();
      // Cancel all pending auto-complete timeouts
      for (const handle of pendingTimeouts.current) {
        clearTimeout(handle);
      }
      pendingTimeouts.current.clear();
    };
  }, []);
}
