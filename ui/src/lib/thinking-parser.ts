/**
 * Parser for LLM thinking/reasoning tags.
 *
 * Many reasoning models (GPT-5, Claude with extended thinking, DeepSeek-R1,
 * QwQ, etc.) include chain-of-thought in tags like:
 *   <think>...</think>
 *   <reasoning>...</reasoning>
 *   <thought>...</thought>
 *   <reflection>...</reflection>
 *
 * This module strips thinking content from visible output and optionally
 * extracts it for display in a collapsible disclosure.
 */

export interface ParsedContent {
  /** The visible content with thinking blocks removed */
  visible: string;
  /** Extracted thinking blocks, in order they appeared */
  thinking: string[];
  /** Whether the content is still mid-thinking (open tag, no close tag yet) */
  isThinking: boolean;
}

// Tags we recognize as thinking/reasoning containers
const THINKING_TAGS = ["think", "thinking", "reasoning", "thought", "reflection"] as const;

// Build a regex that matches any of the thinking tag pairs (including partial/unclosed)
// Handles: <think>...</think>, <think>... (streaming, no close yet)
const THINKING_REGEX = new RegExp(
  `<(${THINKING_TAGS.join("|")})>([\\s\\S]*?)(?:<\\/\\1>|$)`,
  "gi",
);

// Regex to detect an open thinking tag without a close (streaming in progress)
const OPEN_THINKING_REGEX = new RegExp(
  `<(${THINKING_TAGS.join("|")})>([\\s\\S]*)$`,
  "i",
);

/**
 * Parse content to separate thinking blocks from visible output.
 *
 * Works both for complete content and streaming content where the
 * thinking block may not be closed yet.
 */
export function parseThinkingContent(raw: string): ParsedContent {
  if (!raw) {
    return { visible: "", thinking: [], isThinking: false };
  }

  const thinking: string[] = [];
  let isThinking = false;

  // Check if we're mid-stream inside an open thinking tag
  const openMatch = OPEN_THINKING_REGEX.exec(raw);
  if (openMatch) {
    // Check if this open tag has a corresponding close tag
    const tag = openMatch[1].toLowerCase();
    const closeTag = `</${tag}>`;
    const afterOpen = raw.indexOf(`<${openMatch[1]}>`) + openMatch[0].length;
    // If there's no close tag after the open tag, we're mid-thinking
    if (!raw.slice(raw.indexOf(`<${openMatch[1]}>`)).includes(closeTag)) {
      isThinking = true;
    }
  }

  // Extract and remove all thinking blocks
  const visible = raw
    .replace(THINKING_REGEX, (_match, _tag, content) => {
      const trimmed = content.trim();
      if (trimmed) {
        thinking.push(trimmed);
      }
      return "";
    })
    .trim();

  return { visible, thinking, isThinking };
}

/**
 * Quick check: does this content contain any thinking tags?
 */
export function hasThinkingContent(raw: string): boolean {
  return THINKING_TAGS.some(
    (tag) => raw.includes(`<${tag}>`) || raw.includes(`<${tag.charAt(0).toUpperCase() + tag.slice(1)}>`),
  );
}
