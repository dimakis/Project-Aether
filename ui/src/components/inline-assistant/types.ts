/**
 * InlineAssistant-specific types.
 */

import type { EntityContext } from "@/lib/types";

export interface InlineMessage {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

export interface DelegationMsg {
  from: string;
  to: string;
  content: string;
  ts: number;
}

export interface InlineAssistantProps {
  /** System context injected as the first message (invisible to user) */
  systemContext: string;
  /** Suggestion chips shown when the chat is empty */
  suggestions: string[];
  /** React Query keys to invalidate when the assistant performs actions */
  invalidateKeys?: readonly (readonly string[])[];
  /** Placeholder text for the input */
  placeholder?: string;
  /** Default collapsed state */
  defaultCollapsed?: boolean;
  /** Model to use (defaults to gpt-4o-mini) */
  model?: string;
  /** Entity context injected alongside the system message */
  entityContext?: EntityContext | null;
  /** Callback to clear the entity context */
  onClearEntityContext?: () => void;
  /** Auto-send this message when set (one-shot, clears previous chat) */
  triggerMessage?: string | null;
  /** Called after triggerMessage has been consumed */
  onTriggerConsumed?: () => void;
  /** External messages state (store-driven) — when provided, internal useState is bypassed */
  externalMessages?: InlineMessage[];
  /** External setter for messages — supports both direct value and functional updater */
  onMessagesChange?: (
    action: InlineMessage[] | ((prev: InlineMessage[]) => InlineMessage[]),
  ) => void;
  /** External delegation messages (store-driven) */
  externalDelegationMsgs?: DelegationMsg[];
  /** External setter for delegation messages */
  onDelegationMsgsChange?: (msgs: DelegationMsg[] | ((prev: DelegationMsg[]) => DelegationMsg[])) => void;
}
