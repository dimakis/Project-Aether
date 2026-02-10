/**
 * Unit tests for the streamChat SSE parser.
 *
 * Verifies that the async generator correctly parses OpenAI-compatible
 * Server-Sent Events, handling text deltas, metadata, errors, and
 * edge cases like malformed chunks and split reads.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { streamChat, ApiError } from "@/api/client";
import type { StreamChunk } from "@/api/client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Encode a string to Uint8Array for ReadableStream simulation. */
function encode(str: string): Uint8Array {
  return new TextEncoder().encode(str);
}

/** Build an SSE data line (with trailing double newline). */
function sse(data: string): string {
  return `data: ${data}\n\n`;
}

/** Build an SSE chunk with OpenAI delta format. */
function sseDelta(content: string): string {
  return sse(
    JSON.stringify({
      id: "chatcmpl-test",
      object: "chat.completion.chunk",
      created: 1700000000,
      model: "test-model",
      choices: [{ index: 0, delta: { content }, finish_reason: null }],
    }),
  );
}

/** Build an SSE metadata event. */
function sseMetadata(
  traceId?: string,
  conversationId?: string,
): string {
  return sse(
    JSON.stringify({
      type: "metadata",
      trace_id: traceId,
      conversation_id: conversationId,
    }),
  );
}

/**
 * Create a mock fetch response with a readable stream that
 * emits the given string chunks (each chunk is a separate read).
 */
function mockFetchSSE(
  chunks: string[],
  status = 200,
  statusText = "OK",
): typeof globalThis.fetch {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText,
    body: new ReadableStream({
      start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(encode(chunk));
        }
        controller.close();
      },
    }),
  });
}

/** Collect all chunks from the streamChat async generator. */
async function collectChunks(
  model: string,
  messages: import("@/lib/types").ChatMessage[],
): Promise<StreamChunk[]> {
  const result: StreamChunk[] = [];
  for await (const chunk of streamChat(model, messages)) {
    result.push(chunk);
  }
  return result;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("streamChat", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    // Ensure env.API_URL resolves (jsdom doesn't set window.__ENV__)
    // The default fallback in env.ts is "/api"
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  // --- text delta parsing ---

  it("yields text content from SSE delta chunks", async () => {
    globalThis.fetch = mockFetchSSE([
      sseDelta("Hello"),
      sseDelta(" world"),
      sse("[DONE]"),
    ]);

    const chunks = await collectChunks("test", [
      { role: "user", content: "Hi" },
    ]);

    expect(chunks).toEqual(["Hello", " world"]);
  });

  it("handles multiple deltas in a single read", async () => {
    // Server sends multiple SSE events in one TCP frame
    const combined = sseDelta("A") + sseDelta("B") + sse("[DONE]");
    globalThis.fetch = mockFetchSSE([combined]);

    const chunks = await collectChunks("test", [
      { role: "user", content: "Hi" },
    ]);

    expect(chunks).toEqual(["A", "B"]);
  });

  // --- metadata events ---

  it("yields metadata events with trace_id and conversation_id", async () => {
    globalThis.fetch = mockFetchSSE([
      sseDelta("Hi"),
      sseMetadata("trace-abc", "conv-123"),
      sse("[DONE]"),
    ]);

    const chunks = await collectChunks("test", [
      { role: "user", content: "Hi" },
    ]);

    expect(chunks).toEqual([
      "Hi",
      {
        type: "metadata",
        trace_id: "trace-abc",
        conversation_id: "conv-123",
      },
    ]);
  });

  // --- [DONE] handling ---

  it("stops iteration on [DONE]", async () => {
    globalThis.fetch = mockFetchSSE([
      sseDelta("before"),
      sse("[DONE]"),
      sseDelta("after"), // should never be reached
    ]);

    const chunks = await collectChunks("test", [
      { role: "user", content: "Hi" },
    ]);

    expect(chunks).toEqual(["before"]);
  });

  // --- error handling ---

  it("throws ApiError on non-OK HTTP status", async () => {
    globalThis.fetch = mockFetchSSE([], 429, "Too Many Requests");

    await expect(
      collectChunks("test", [{ role: "user", content: "Hi" }]),
    ).rejects.toThrow(ApiError);
  });

  it("throws ApiError on SSE error event", async () => {
    const errorEvent = sse(
      JSON.stringify({
        error: { message: "Rate limit exceeded", type: "api_error" },
      }),
    );
    globalThis.fetch = mockFetchSSE([errorEvent]);

    await expect(
      collectChunks("test", [{ role: "user", content: "Hi" }]),
    ).rejects.toThrow("Rate limit exceeded");
  });

  // --- malformed chunks ---

  it("skips malformed JSON chunks silently", async () => {
    globalThis.fetch = mockFetchSSE([
      sseDelta("good"),
      sse("{not valid json"),
      sseDelta("also good"),
      sse("[DONE]"),
    ]);

    const chunks = await collectChunks("test", [
      { role: "user", content: "Hi" },
    ]);

    expect(chunks).toEqual(["good", "also good"]);
  });

  it("skips empty lines and non-data lines", async () => {
    globalThis.fetch = mockFetchSSE([
      "\n\n",
      ": comment line\n\n",
      sseDelta("valid"),
      sse("[DONE]"),
    ]);

    const chunks = await collectChunks("test", [
      { role: "user", content: "Hi" },
    ]);

    expect(chunks).toEqual(["valid"]);
  });

  it("skips delta with empty content", async () => {
    const emptyDelta = sse(
      JSON.stringify({
        choices: [{ index: 0, delta: { content: "" }, finish_reason: null }],
      }),
    );

    globalThis.fetch = mockFetchSSE([
      sseDelta("before"),
      emptyDelta,
      sseDelta("after"),
      sse("[DONE]"),
    ]);

    const chunks = await collectChunks("test", [
      { role: "user", content: "Hi" },
    ]);

    // Empty content is falsy, so it's not yielded
    expect(chunks).toEqual(["before", "after"]);
  });

  // --- split reads (buffering) ---

  it("handles SSE data split across multiple reads", async () => {
    // Simulate the TCP stream splitting an SSE event mid-line
    const full = sseDelta("split");
    const mid = Math.floor(full.length / 2);

    globalThis.fetch = mockFetchSSE([
      full.slice(0, mid),
      full.slice(mid),
      sse("[DONE]"),
    ]);

    const chunks = await collectChunks("test", [
      { role: "user", content: "Hi" },
    ]);

    expect(chunks).toEqual(["split"]);
  });

  // --- trace events ---

  it("yields trace events with agent and event info", async () => {
    const traceStart = sse(
      JSON.stringify({
        type: "trace",
        agent: "architect",
        event: "start",
        ts: 1700000000,
      }),
    );
    const traceToolCall = sse(
      JSON.stringify({
        type: "trace",
        agent: "data_scientist",
        event: "tool_call",
        tool: "analyze_energy",
        ts: 1700000001,
      }),
    );
    const traceComplete = sse(
      JSON.stringify({
        type: "trace",
        event: "complete",
        agents: ["architect", "data_scientist"],
        ts: 1700000002,
      }),
    );

    globalThis.fetch = mockFetchSSE([
      traceStart,
      traceToolCall,
      traceComplete,
      sseDelta("Results"),
      sse("[DONE]"),
    ]);

    const chunks = await collectChunks("test", [
      { role: "user", content: "Analyze" },
    ]);

    expect(chunks).toEqual([
      {
        type: "trace",
        agent: "architect",
        event: "start",
        tool: undefined,
        ts: 1700000000,
        agents: undefined,
      },
      {
        type: "trace",
        agent: "data_scientist",
        event: "tool_call",
        tool: "analyze_energy",
        ts: 1700000001,
        agents: undefined,
      },
      {
        type: "trace",
        event: "complete",
        agent: undefined,
        tool: undefined,
        ts: 1700000002,
        agents: ["architect", "data_scientist"],
      },
      "Results",
    ]);
  });

  it("handles interleaved trace and metadata events", async () => {
    const trace = sse(
      JSON.stringify({
        type: "trace",
        agent: "architect",
        event: "start",
        ts: 1700000000,
      }),
    );

    globalThis.fetch = mockFetchSSE([
      trace,
      sseDelta("Hi"),
      sseMetadata("trace-id", "conv-id"),
      sse("[DONE]"),
    ]);

    const chunks = await collectChunks("test", [
      { role: "user", content: "Hi" },
    ]);

    // Trace event, then text, then metadata
    expect(chunks).toHaveLength(3);
    expect(typeof chunks[0]).toBe("object");
    expect((chunks[0] as any).type).toBe("trace");
    expect(typeof chunks[1]).toBe("string");
    expect((chunks[2] as any).type).toBe("metadata");
  });

  // --- request format ---

  it("sends correct request body", async () => {
    const mockFetch = mockFetchSSE([sse("[DONE]")]);
    globalThis.fetch = mockFetch;

    await collectChunks("gpt-4o", [
      { role: "user", content: "Hello" },
    ]);

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/chat/completions"),
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "gpt-4o",
          messages: [{ role: "user", content: "Hello" }],
          stream: true,
        }),
      }),
    );
  });
});
