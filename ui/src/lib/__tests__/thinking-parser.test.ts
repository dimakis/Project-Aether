/**
 * Unit tests for the thinking-parser module.
 *
 * Documents and verifies the behavior of parseThinkingContent and
 * hasThinkingContent used to split LLM reasoning from visible output.
 */

import { describe, it, expect } from "vitest";
import {
  parseThinkingContent,
  hasThinkingContent,
} from "@/lib/thinking-parser";

// ---------------------------------------------------------------------------
// parseThinkingContent
// ---------------------------------------------------------------------------

describe("parseThinkingContent", () => {
  // --- empty / no tags ---

  it("returns empty result for empty string", () => {
    const result = parseThinkingContent("");
    expect(result).toEqual({ visible: "", thinking: [], isThinking: false });
  });

  it("returns full content as visible when no tags present", () => {
    const result = parseThinkingContent("Hello, world!");
    expect(result.visible).toBe("Hello, world!");
    expect(result.thinking).toEqual([]);
    expect(result.isThinking).toBe(false);
  });

  // --- closed tag pairs ---

  it("strips a single <think> block and extracts thinking", () => {
    const raw = "<think>reasoning here</think>The answer is 42.";
    const result = parseThinkingContent(raw);

    expect(result.visible).toBe("The answer is 42.");
    expect(result.thinking).toEqual(["reasoning here"]);
    expect(result.isThinking).toBe(false);
  });

  it("strips <thinking> tag variant", () => {
    const result = parseThinkingContent(
      "<thinking>analysis</thinking>Result.",
    );
    expect(result.visible).toBe("Result.");
    expect(result.thinking).toEqual(["analysis"]);
  });

  it("strips <reasoning> tag variant", () => {
    const result = parseThinkingContent(
      "<reasoning>deduction</reasoning>Conclusion.",
    );
    expect(result.visible).toBe("Conclusion.");
    expect(result.thinking).toEqual(["deduction"]);
  });

  it("strips <thought> tag variant", () => {
    const result = parseThinkingContent("<thought>hmm</thought>OK.");
    expect(result.visible).toBe("OK.");
    expect(result.thinking).toEqual(["hmm"]);
  });

  it("strips <reflection> tag variant", () => {
    const result = parseThinkingContent(
      "<reflection>review</reflection>Final.",
    );
    expect(result.visible).toBe("Final.");
    expect(result.thinking).toEqual(["review"]);
  });

  it("handles multiple thinking blocks in sequence", () => {
    const raw =
      "<think>step 1</think>Part A. <think>step 2</think>Part B.";
    const result = parseThinkingContent(raw);

    expect(result.visible).toBe("Part A. Part B.");
    expect(result.thinking).toEqual(["step 1", "step 2"]);
    expect(result.isThinking).toBe(false);
  });

  it("handles multiline thinking content", () => {
    const raw = "<think>\nLine 1\nLine 2\n</think>\nVisible.";
    const result = parseThinkingContent(raw);

    expect(result.visible).toBe("Visible.");
    expect(result.thinking).toHaveLength(1);
    expect(result.thinking[0]).toContain("Line 1");
    expect(result.thinking[0]).toContain("Line 2");
  });

  // --- unclosed tags (streaming / model artefact) ---

  it("matches unclosed <think> tag to end of string", () => {
    const raw = "<think>reasoning in progress";
    const result = parseThinkingContent(raw);

    expect(result.visible).toBe("");
    expect(result.thinking).toEqual(["reasoning in progress"]);
    expect(result.isThinking).toBe(true);
  });

  it("preserves text before an unclosed tag", () => {
    const raw = "Hello. <think>partial reasoning";
    const result = parseThinkingContent(raw);

    expect(result.visible).toBe("Hello.");
    expect(result.thinking).toEqual(["partial reasoning"]);
    expect(result.isThinking).toBe(true);
  });

  it("sets isThinking false when all tags are properly closed", () => {
    const raw = "<think>done</think>Result.";
    const result = parseThinkingContent(raw);

    expect(result.isThinking).toBe(false);
  });

  // --- mixed content ---

  it("handles visible text before, between, and after thinking blocks", () => {
    const raw = "Intro. <think>t1</think>Middle. <think>t2</think>End.";
    const result = parseThinkingContent(raw);

    expect(result.visible).toBe("Intro. Middle. End.");
    expect(result.thinking).toEqual(["t1", "t2"]);
  });

  // --- edge cases ---

  it("preserves non-thinking angle brackets", () => {
    const raw = "Use <div> for containers.";
    const result = parseThinkingContent(raw);

    expect(result.visible).toBe("Use <div> for containers.");
    expect(result.thinking).toEqual([]);
  });

  it("skips empty thinking blocks", () => {
    const raw = "<think></think>Result.";
    const result = parseThinkingContent(raw);

    expect(result.visible).toBe("Result.");
    // Empty content is trimmed → not pushed to thinking array
    expect(result.thinking).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// hasThinkingContent
// ---------------------------------------------------------------------------

describe("hasThinkingContent", () => {
  it("returns true when <think> tag is present", () => {
    expect(hasThinkingContent("<think>test</think>")).toBe(true);
  });

  it("returns true for capitalized tag", () => {
    expect(hasThinkingContent("<Think>test</Think>")).toBe(true);
  });

  it("returns false when no thinking tags present", () => {
    expect(hasThinkingContent("Hello, world!")).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(hasThinkingContent("")).toBe(false);
  });
});
