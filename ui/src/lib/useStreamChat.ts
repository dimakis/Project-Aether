/**
 * Shared hook for consuming a streamChat async generator.
 *
 * Encapsulates the `for await` loop and dispatches events through callbacks,
 * eliminating the duplicated event dispatch logic between the chat page and
 * InlineAssistant.
 *
 * Feature 31: Streaming Tool Executor Refactor — Phase 2.
 */

import { useCallback, useRef } from "react";
import type { StreamChunk } from "@/api/client/conversations";
import { streamChat } from "@/api/client/conversations";
import type { ChatMessage } from "@/lib/types";

// ─── Extracted StreamChunk subtypes ──────────────────────────────────────────

type MetadataChunk = Extract<StreamChunk, { type: "metadata" }>;
type TraceChunk = Extract<StreamChunk, { type: "trace" }>;
type StatusChunk = Extract<StreamChunk, { type: "status" }>;
type ThinkingChunk = Extract<StreamChunk, { type: "thinking" }>;
type DelegationChunk = Extract<StreamChunk, { type: "delegation" }>;

// ─── Callbacks ───────────────────────────────────────────────────────────────

export interface StreamChatCallbacks {
  /** Called for each text token delta. */
  onToken: (text: string) => void;
  /** Called for metadata events (trace_id, conversation_id, tool_calls). */
  onMetadata?: (chunk: MetadataChunk) => void;
  /** Called for trace events (agent start/end, tool_call, etc.). */
  onTrace?: (chunk: TraceChunk) => void;
  /** Called for status events (e.g. "Running analyze_energy..."). */
  onStatus?: (chunk: StatusChunk) => void;
  /** Called for thinking/reasoning content from the LLM. */
  onThinking?: (chunk: ThinkingChunk) => void;
  /** Called for inter-agent delegation messages. */
  onDelegation?: (chunk: DelegationChunk) => void;
  /** Called when the stream finishes (success or abort). Not called on error. */
  onDone?: () => void;
  /** Called when the stream errors. */
  onError?: (error: unknown) => void;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export interface UseStreamChatReturn {
  /** Start streaming. Returns when the stream ends or is aborted. */
  stream: (
    model: string,
    messages: ChatMessage[],
    conversationId?: string,
  ) => Promise<void>;
  /** Abort the current stream. Safe to call when no stream is active. */
  abort: () => void;
  /** Whether a stream is currently active. */
  isStreaming: boolean;
}

/**
 * Hook that wraps `streamChat` and dispatches events via callbacks.
 *
 * Usage:
 * ```ts
 * const { stream, abort } = useStreamChat({
 *   onToken: (text) => { contentRef.current += text; flush(); },
 *   onTrace: (chunk) => handleTraceEvent(chunk, setActivity, snap()),
 *   onStatus: (chunk) => setStatusMessage(chunk.content),
 * });
 * await stream(model, chatHistory, conversationId);
 * ```
 */
export function useStreamChat(callbacks: StreamChatCallbacks): UseStreamChatReturn {
  const abortRef = useRef<AbortController | null>(null);
  const isStreamingRef = useRef(false);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const stream = useCallback(
    async (
      model: string,
      messages: ChatMessage[],
      conversationId?: string,
    ) => {
      // Abort any existing stream
      abort();

      const controller = new AbortController();
      abortRef.current = controller;
      isStreamingRef.current = true;

      try {
        for await (const chunk of streamChat(
          model,
          messages,
          conversationId,
          controller.signal,
        )) {
          // Structured events
          if (typeof chunk === "object" && "type" in chunk) {
            switch (chunk.type) {
              case "metadata":
                callbacks.onMetadata?.(chunk);
                continue;
              case "trace":
                callbacks.onTrace?.(chunk);
                continue;
              case "status":
                callbacks.onStatus?.(chunk);
                continue;
              case "thinking":
                callbacks.onThinking?.(chunk);
                continue;
              case "delegation":
                callbacks.onDelegation?.(chunk);
                continue;
            }
          }

          // Text token
          const text = typeof chunk === "string" ? chunk : "";
          if (text) {
            callbacks.onToken(text);
          }
        }

        callbacks.onDone?.();
      } catch (error) {
        // AbortError is expected when the user cancels — treat as done
        if (error instanceof DOMException && error.name === "AbortError") {
          callbacks.onDone?.();
          return;
        }
        callbacks.onError?.(error);
      } finally {
        isStreamingRef.current = false;
        abortRef.current = null;
      }
    },
    // callbacks is intentionally not in the dep array — callers should
    // provide stable callbacks (or use refs internally).
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [abort],
  );

  return {
    stream,
    abort,
    get isStreaming() {
      return isStreamingRef.current;
    },
  };
}
