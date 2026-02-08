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
} from "@/lib/agent-activity-store";

const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;

export function useGlobalActivityStream() {
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
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
          if (data.type !== "llm") return;

          const snap = getActivitySnapshot();

          // If the chat stream is driving state, defer to it.
          // The chat stream sets isActive=true with a completedAt=null;
          // the global stream should only update when the panel is idle
          // or showing a completed session.
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
