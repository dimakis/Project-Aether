/**
 * Custom hook for InlineAssistant state, messages, and streaming.
 */

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/hooks/queryKeys";
import type { ChatMessage, EntityContext } from "@/lib/types";
import { handleTraceEvent } from "@/lib/trace-event-handler";
import type { TraceEventChunk } from "@/lib/trace-event-handler";
import { useStreamChat } from "@/lib/useStreamChat";
import type { InlineMessage, DelegationMsg } from "./types";

const TOOL_INVALIDATION_MAP: Record<string, readonly (readonly string[])[]> = {
  create_insight_schedule: [queryKeys.schedules.all],
  run_custom_analysis: [queryKeys.insights.all, queryKeys.insights.summary],
  analyze_energy: [queryKeys.insights.all, queryKeys.insights.summary],
  diagnose_issue: [queryKeys.insights.all, queryKeys.insights.summary],
  seek_approval: [
    queryKeys.proposals.all,
    queryKeys.registry.automations,
    queryKeys.registry.scripts,
    queryKeys.registry.scenes,
  ],
};

export interface UseInlineAssistantParams {
  systemContext: string;
  invalidateKeys?: readonly (readonly string[])[];
  model?: string;
  defaultCollapsed?: boolean;
  entityContext?: EntityContext | null;
  triggerMessage?: string | null;
  onTriggerConsumed?: () => void;
  externalMessages?: InlineMessage[];
  onMessagesChange?: (
    action: InlineMessage[] | ((prev: InlineMessage[]) => InlineMessage[]),
  ) => void;
  externalDelegationMsgs?: DelegationMsg[];
  onDelegationMsgsChange?: (msgs: DelegationMsg[]) => void;
}

export interface UseInlineAssistantResult {
  messages: InlineMessage[];
  setMessages: (
    action: InlineMessage[] | ((prev: InlineMessage[]) => InlineMessage[]),
  ) => void;
  delegationMsgs: DelegationMsg[];
  setDelegationMsgs: (msgs: DelegationMsg[] | ((prev: DelegationMsg[]) => DelegationMsg[])) => void;
  input: string;
  setInput: (v: string) => void;
  isStreaming: boolean;
  activeAgent: string | null;
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  effectiveSystemContext: string;
  sendMessage: (content: string) => Promise<void>;
  clearChat: () => void;
}

export function useInlineAssistant({
  systemContext,
  invalidateKeys = [],
  model = "gpt-4o-mini",
  entityContext = null,
  triggerMessage = null,
  onTriggerConsumed,
  externalMessages,
  onMessagesChange,
  externalDelegationMsgs,
  onDelegationMsgsChange,
  defaultCollapsed = true,
}: UseInlineAssistantParams): UseInlineAssistantResult {
  const queryClient = useQueryClient();
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [internalMessages, setInternalMessages] = useState<InlineMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [internalDelegationMsgs, setInternalDelegationMsgs] = useState<DelegationMsg[]>([]);

  const messages = externalMessages ?? internalMessages;
  const setMessages = onMessagesChange ?? setInternalMessages;
  const delegationMsgs = externalDelegationMsgs ?? internalDelegationMsgs;
  const setDelegationMsgs = onDelegationMsgsChange ?? setInternalDelegationMsgs;

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const isStreamingRef = useRef(isStreaming);
  isStreamingRef.current = isStreaming;

  const stableInvalidateKeys = useMemo(() => invalidateKeys, [invalidateKeys]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    const isNearBottom = distanceFromBottom < 80;

    if (isNearBottom) {
      const lastMsg = messages[messages.length - 1];
      const behavior = lastMsg?.isStreaming ? "instant" : "smooth";
      messagesEndRef.current?.scrollIntoView({ behavior: behavior as ScrollBehavior });
    }
  }, [messages]);

  useEffect(() => {
    if (!collapsed) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [collapsed]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height =
        Math.min(inputRef.current.scrollHeight, 100) + "px";
    }
  }, [input]);

  const effectiveSystemContext = useMemo(() => {
    if (!entityContext) return systemContext;

    let ctx = `${systemContext}\n\n--- ENTITY CONTEXT ---\nThe user is viewing: ${entityContext.entityId} ("${entityContext.label}")\nType: ${entityContext.entityType}`;

    if (entityContext.configYaml) {
      ctx += `\n\nCurrent configuration:\n\`\`\`yaml\n${entityContext.configYaml}\n\`\`\``;
    }
    if (entityContext.editedYaml) {
      ctx += `\n\nUser's edited YAML:\n\`\`\`yaml\n${entityContext.editedYaml}\n\`\`\``;
    }

    return ctx;
  }, [systemContext, entityContext]);

  // Refs for stream content accumulation (avoids stale closures)
  const fullContentRef = useRef("");
  const toolCallsUsedRef = useRef<string[]>([]);

  const { stream, abort: abortStream } = useStreamChat({
    onToken: (text) => {
      fullContentRef.current += text;
      const snapshot = fullContentRef.current;
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: snapshot,
          isStreaming: true,
        };
        return updated;
      });
    },
    onMetadata: (chunk) => {
      if (chunk.tool_calls) {
        toolCallsUsedRef.current = chunk.tool_calls;
      }
    },
    onTrace: (chunk) => {
      handleTraceEvent(
        chunk as TraceEventChunk,
        (activity) => {
          setActiveAgent(activity.activeAgent ?? null);
        },
        {
          isActive: false,
          activeAgent: null,
          agentsSeen: [],
          agentStates: {},
          liveTimeline: [],
          thinkingStream: "",
          activeEdges: [],
          delegationMessages: [],
          completedAt: null,
        },
      );
    },
    onDelegation: (chunk) => {
      const msg: DelegationMsg = {
        from: chunk.from,
        to: chunk.to,
        content: chunk.content,
        ts: chunk.ts ?? Date.now() / 1000,
      };
      setDelegationMsgs((prev) => [...prev, msg]);
    },
    onDone: () => {
      // Finalize message
      const finalContent = fullContentRef.current;
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: finalContent,
          isStreaming: false,
        };
        return updated;
      });

      // Invalidate relevant queries
      for (const key of stableInvalidateKeys) {
        queryClient.invalidateQueries({ queryKey: [...key] });
      }
      const usedTools = toolCallsUsedRef.current;
      if (usedTools.length > 0) {
        for (const toolName of usedTools) {
          const keys = TOOL_INVALIDATION_MAP[toolName];
          if (keys) {
            for (const key of keys) {
              queryClient.invalidateQueries({ queryKey: [...key] });
            }
          }
        }
      }

      setIsStreaming(false);
      setActiveAgent(null);
      inputRef.current?.focus();
    },
    onError: () => {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again.",
          isStreaming: false,
        };
        return updated;
      });
      setIsStreaming(false);
      setActiveAgent(null);
      inputRef.current?.focus();
    },
  });

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreamingRef.current) return;

      const userMsg: InlineMessage = { role: "user", content: content.trim() };
      const assistantMsg: InlineMessage = {
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setIsStreaming(true);

      // Reset refs for this stream
      fullContentRef.current = "";
      toolCallsUsedRef.current = [];

      const chatHistory: ChatMessage[] = [
        { role: "system", content: effectiveSystemContext },
        ...messagesRef.current.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        })),
        { role: "user", content: content.trim() },
      ];

      await stream(model, chatHistory);
    },
    [effectiveSystemContext, model, stream],
  );

  // Stable ref for sendMessage so triggerMessage effect doesn't depend on the callback
  const sendMessageFn = useCallback(
    (msg: string) => sendMessage(msg),
    [sendMessage],
  );

  const triggerMessageRef = useRef(triggerMessage);
  useEffect(() => {
    if (
      triggerMessage &&
      triggerMessage !== triggerMessageRef.current &&
      !isStreaming
    ) {
      triggerMessageRef.current = triggerMessage;
      setCollapsed(false);
      setMessages([]);
      setDelegationMsgs([]);
      setTimeout(() => {
        sendMessageFn(triggerMessage);
        onTriggerConsumed?.();
      }, 50);
    } else if (!triggerMessage) {
      triggerMessageRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerMessage]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setDelegationMsgs([]);
    setInput("");
  }, [setMessages, setDelegationMsgs]);

  return {
    messages,
    setMessages,
    delegationMsgs,
    setDelegationMsgs,
    input,
    setInput,
    isStreaming,
    activeAgent,
    collapsed,
    setCollapsed,
    messagesEndRef,
    scrollContainerRef,
    inputRef,
    effectiveSystemContext,
    sendMessage,
    clearChat,
  };
}
