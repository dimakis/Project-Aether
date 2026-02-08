/**
 * Global SSE subscription for system-wide LLM activity events.
 *
 * Connects to /api/v1/activity/stream and updates the agent activity
 * store so the neural panel reacts to ALL LLM calls — not just chat.
 */

import { useEffect, useRef } from "react";
import {
  setAgentActivity,
  clearAgentActivity,
  getActivitySnapshot,
} from "@/lib/agent-activity-store";

const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;

export function useGlobalActivityStream() {
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const esRef = useRef<EventSource | null>(null);

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

          const role: string = data.agent_role ?? "system";
          const snap = getActivitySnapshot();

          if (data.event === "start") {
            // Mark this agent as firing; set system as active
            const nextStates = { ...snap.agentStates };
            nextStates[role] = "firing";
            // Also light up aether hub
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
            // Keep aether firing if anything else is still firing
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

            // If nothing is firing, auto-clear after a short delay
            if (!anyOtherFiring) {
              setTimeout(() => {
                const latest = getActivitySnapshot();
                const stillFiring = Object.values(latest.agentStates).some(
                  (v) => v === "firing",
                );
                if (!stillFiring && !latest.isActive) {
                  // Don't clear — let the "done" state persist until next
                  // conversation. Just mark inactive.
                  setAgentActivity({ isActive: false });
                }
              }, 2000);
            }
          }
        } catch {
          // Ignore parse errors
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        // Exponential backoff reconnect
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
    };
  }, []);
}
