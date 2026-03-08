import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  setAgentActivity,
  completeAgentActivity,
  setLastTraceId,
  useActivityPanel,
  getActivitySnapshot,
  setActivitySession,
  getActivitySessionId,
} from "@/lib/agent-activity-store";
import { handleTraceEvent } from "@/lib/trace-event-handler";
import type { TraceEventChunk } from "@/lib/trace-event-handler";
import {
  STORAGE_KEYS,
  generateSessionId,
  autoTitle,
  storageGet,
  storageSet,
  type DisplayMessage,
  type ChatSession,
} from "@/lib/storage";
import { useModels, useConversations, useCreateProposal } from "@/api/hooks";
import { streamChat, submitFeedback } from "@/api/client";
import type { ChatMessage, ModelInfo, Conversation } from "@/lib/types";
import { useChatSessions } from "./useChatSessions";
import type { WorkflowSelection } from "../WorkflowPresetSelector";
import { getPersistedAgent } from "../AgentPicker";


export interface UseChatMessagesReturn {
  sessions: ChatSession[];
  activeSessionId: string | null;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  selectedAgent: string;
  setSelectedAgent: (agent: string) => void;
  messages: DisplayMessage[];
  startNewChat: () => void;
  switchSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  input: string;
  setInput: (value: string) => void;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  isStreaming: boolean;
  copiedIdx: number | null;
  statusMessage: string;
  elapsed: number;
  workflowSelection: WorkflowSelection;
  setWorkflowSelection: (s: WorkflowSelection) => void;
  sendMessage: (content: string) => Promise<void>;
  handleCopyMessage: (content: string, idx: number) => Promise<void>;
  handleRetry: () => void;
  handleFeedback: (index: number, sentiment: "positive" | "negative") => Promise<void>;
  handleCreateProposal: (yamlContent: string) => void;
  setMessages: (
    updater:
      | DisplayMessage[]
      | ((prev: DisplayMessage[]) => DisplayMessage[]),
  ) => void;
  availableModels: ModelInfo[];
  recentConversations: Conversation[];
  activityPanelOpen: boolean;
}

export function useChatMessages(): UseChatMessagesReturn {
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const [input, setInput] = useState("");
  // Track WHICH session is streaming rather than a boolean.
  // This lets background streams continue when the user switches sessions.
  const [streamingSessionId, setStreamingSessionId] = useState<string | null>(
    null,
  );
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [streamStartTime, setStreamStartTime] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [selectedAgent, setSelectedAgent] = useState<string>(getPersistedAgent());
  const [workflowSelection, setWorkflowSelection] =
    useState<WorkflowSelection>({
      preset: null,
      disabledAgents: new Set(),
    });

  const abortRef = useRef<AbortController | null>(null);
  const streamContentRef = useRef("");
  const streamThinkingRef = useRef("");
  const streamSessionIdRef = useRef<string | null>(null);

  // Per-session draft storage so switching chats preserves unsent input
  const draftsRef = useRef<Map<string, string>>(new Map());
  // Track current values in refs for the switch callback (avoids stale closures)
  const activeSessionIdRef = useRef<string | null>(null);
  const inputRef2 = useRef(input);
  inputRef2.current = input;

  const { panelOpen: activityPanelOpen } = useActivityPanel();

  const {
    sessions,
    setSessions,
    activeSessionId,
    setActiveSessionId,
    selectedModel,
    setSelectedModel,
    messages,
    setMessages,
    startNewChat,
    switchSession,
    deleteSession,
  } = useChatSessions({
    onSessionSwitch: (newSessionId: string) => {
      // Do NOT abort the running stream — it continues in the background.
      // The updateSessionMessages closure captures the correct sessionId,
      // so data keeps flowing to the right session.

      // Save the current draft before switching (read from ref to avoid stale closure)
      const oldId = activeSessionIdRef.current;
      if (oldId) {
        const currentDraft = inputRef2.current.trim();
        if (currentDraft) {
          draftsRef.current.set(oldId, currentDraft);
        } else {
          draftsRef.current.delete(oldId);
        }
      }

      // Restore the new session's draft (or empty)
      setInput(draftsRef.current.get(newSessionId) ?? "");
      setStreamStartTime(null);
      setStatusMessage("");
      inputRef.current?.focus();

      // Rebind the activity panel to the new session so the System
      // Activity panel reflects the correct session's state.
      setActivitySession(newSessionId);

      // Restore the last traceId from the new session's messages
      // so the activity panel can show the last trace timeline.
      const stored = storageGet<ChatSession[]>(STORAGE_KEYS.chatSessions, []);
      const targetSession = stored.find((s) => s.id === newSessionId);
      if (targetSession) {
        const lastAssistant = [...targetSession.messages]
          .reverse()
          .find((m) => m.role === "assistant" && m.traceId);
        setLastTraceId(lastAssistant?.traceId ?? null);
      } else {
        setLastTraceId(null);
      }
    },
  });

  // Keep the ref in sync so the switch callback can read the old session ID
  activeSessionIdRef.current = activeSessionId;

  // Derive isStreaming from whether the ACTIVE session is the one streaming.
  // Other sessions can stream in the background without blocking the UI.
  const isStreaming = streamingSessionId === activeSessionId && activeSessionId !== null;

  const { data: modelsData } = useModels();
  const { data: conversationsData } = useConversations();
  const createProposalMut = useCreateProposal();

  const availableModels = modelsData?.data ?? [];
  const recentConversations = conversationsData?.items?.slice(0, 10) ?? [];

  useEffect(() => {
    const prefill = (location.state as { prefill?: string } | null)?.prefill;
    if (prefill) {
      setInput(prefill);
      navigate(location.pathname, { replace: true, state: {} });
      inputRef.current?.focus();
    }
  }, [location.state, location.pathname, navigate]);

  // Component unmount: abort the stream and persist partial content
  useEffect(() => {
    return () => {
      const controller = abortRef.current;
      if (!controller) return;

      controller.abort();
      abortRef.current = null;

      const content = streamContentRef.current;
      const sessionId = streamSessionIdRef.current;
      if (!sessionId) return;

      const stored = storageGet<ChatSession[]>(
        STORAGE_KEYS.chatSessions,
        [],
      );
      const idx = stored.findIndex((s) => s.id === sessionId);
      if (idx === -1) return;

      const msgs = [...stored[idx].messages];
      const last = msgs.length > 0 ? msgs[msgs.length - 1] : null;
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = {
          ...last,
          content: content || last.content || "",
          isStreaming: false,
          thinkingContent: streamThinkingRef.current || undefined,
        };
        stored[idx] = {
          ...stored[idx],
          messages: msgs,
          updatedAt: new Date().toISOString(),
        };
        storageSet(STORAGE_KEYS.chatSessions, stored);
      }
    };
  }, []);

  // Elapsed timer: only runs when the active session is streaming
  useEffect(() => {
    if (!streamStartTime || !isStreaming) {
      setElapsed(0);
      return;
    }
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - streamStartTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [streamStartTime, isStreaming]);

  // When switching back to a session that is still streaming, restore the timer
  useEffect(() => {
    if (isStreaming && !streamStartTime) {
      setStreamStartTime(Date.now());
    }
  }, [isStreaming, streamStartTime]);

  const sendMessage = useCallback(
    async (content: string) => {
      // Guard: block send if the ACTIVE session is already streaming
      if (!content.trim() || isStreaming) return;

      let sessionId = activeSessionId;
      if (!sessionId) {
        const id = generateSessionId();
        const now = new Date().toISOString();
        const newSession: ChatSession = {
          id,
          title: "New Chat",
          messages: [],
          model: selectedModel,
          createdAt: now,
          updatedAt: now,
        };
        setSessions((prev) => [newSession, ...prev]);
        setActiveSessionId(id);
        sessionId = id;
      }

      const userTimestamp = new Date().toISOString();
      const userMsg: DisplayMessage = {
        role: "user",
        content: content.trim(),
        timestamp: userTimestamp,
      };
      const assistantMsg: DisplayMessage = {
        role: "assistant",
        content: "",
        isStreaming: true,
        // No timestamp yet — set when the first token arrives (Bug 2 fix)
      };

      const updateSessionMessages = (
        updater: (prev: DisplayMessage[]) => DisplayMessage[],
      ) => {
        setSessions((prev) => {
          const idx = prev.findIndex((s) => s.id === sessionId);
          if (idx === -1) return prev;
          const session = prev[idx];
          const newMessages = updater(session.messages);
          const updated = {
            ...session,
            messages: newMessages,
            updatedAt: new Date().toISOString(),
          };
          if (updated.title === "New Chat") {
            updated.title = autoTitle(newMessages);
          }
          const next = [...prev];
          next[idx] = updated;
          return next;
        });
      };

      updateSessionMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setStreamingSessionId(sessionId);
      setStreamStartTime(Date.now());

      // Claim the activity panel for this session
      setActivitySession(sessionId);
      setLastTraceId(null);
      setAgentActivity({
        isActive: true,
        activeAgent: "architect",
        thinkingStream: "",
        agentsSeen: ["aether", "architect"],
        agentStates: { aether: "firing", architect: "firing" },
        activeEdges: [["aether", "architect"]],
      });

      const currentMessages =
        sessions.find((s) => s.id === sessionId)?.messages ?? [];
      const chatHistory: ChatMessage[] = [
        ...currentMessages.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        })),
        { role: "user" as const, content: content.trim() },
      ];

      const controller = new AbortController();
      abortRef.current = controller;
      streamContentRef.current = "";
      streamThinkingRef.current = "";
      streamSessionIdRef.current = sessionId;

      const fullContentRef = streamContentRef;
      const thinkingRef = streamThinkingRef;
      const rafPending = { current: false };
      const routedAgentRef = { current: undefined as string | undefined };
      const routingConfidenceRef = { current: undefined as number | undefined };
      const clarificationRef = { current: undefined as import("@/lib/storage").ClarificationOption[] | undefined };

      // Bug 2 fix: track the assistant timestamp separately.
      // Set it on the first flush (when the first token arrives) so the
      // assistant message shows when the response actually started,
      // not when the user pressed send.
      let assistantTimestamp: string | undefined;

      const scheduleFlush = () => {
        if (rafPending.current) return;
        rafPending.current = true;
        if (!assistantTimestamp) {
          assistantTimestamp = new Date().toISOString();
        }
        const ts = assistantTimestamp;
        requestAnimationFrame(() => {
          rafPending.current = false;
          const snapshot = fullContentRef.current;
          const thinkingSnapshot = thinkingRef.current;
          updateSessionMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: snapshot,
              isStreaming: true,
              timestamp: ts,
              thinkingContent: thinkingSnapshot || undefined,
              routedAgent: routedAgentRef.current,
              routingConfidence: routingConfidenceRef.current,
              clarificationOptions: clarificationRef.current,
            };
            return updated;
          });
        });
      };

      try {
        let traceId: string | undefined;

        // Only update the activity panel if this session owns it.
        // Background sessions still stream data (messages accumulate)
        // but their trace/thinking events are dropped from the panel.
        const ownsPanel = () => getActivitySessionId() === sessionId;

        const agentArg = selectedAgent === "auto" ? undefined : selectedAgent;
        const presetArg = workflowSelection.preset?.id;
        const disabledArg = workflowSelection.disabledAgents.size > 0
          ? [...workflowSelection.disabledAgents]
          : undefined;

        for await (const chunk of streamChat(
          selectedModel,
          chatHistory,
          sessionId,
          controller.signal,
          agentArg,
          presetArg,
          disabledArg,
        )) {
          if (typeof chunk === "object" && "type" in chunk) {
            if (chunk.type === "metadata") {
              if (chunk.trace_id) {
                traceId = chunk.trace_id;
                if (ownsPanel()) setLastTraceId(traceId);
              }
              continue;
            }
            if (chunk.type === "trace") {
              if (ownsPanel()) {
                handleTraceEvent(
                  chunk as TraceEventChunk,
                  setAgentActivity,
                  getActivitySnapshot(),
                );
              }
              continue;
            }
            if (chunk.type === "status") {
              if (ownsPanel()) setStatusMessage(chunk.content);
              continue;
            }
            if (chunk.type === "thinking") {
              const delta = chunk.content ?? "";
              thinkingRef.current += delta;
              if (ownsPanel()) {
                const current = getActivitySnapshot();
                setAgentActivity({
                  thinkingStream: (current.thinkingStream ?? "") + delta,
                });
              }
              scheduleFlush();
              continue;
            }
            if (chunk.type === "delegation") {
              if (ownsPanel()) {
                const current = getActivitySnapshot();
                setAgentActivity({
                  delegationMessages: [
                    ...current.delegationMessages,
                    {
                      from: chunk.from,
                      to: chunk.to,
                      content: chunk.content,
                      ts: chunk.ts ?? Date.now() / 1000,
                    },
                  ],
                });
              }
              continue;
            }
            if (chunk.type === "routing") {
              routedAgentRef.current = chunk.agent;
              routingConfidenceRef.current = chunk.confidence;
              if (ownsPanel()) {
                setAgentActivity({
                  routedAgent: chunk.agent,
                  routingConfidence: chunk.confidence,
                  routingReasoning: chunk.reasoning,
                });
              }
              continue;
            }
            if (chunk.type === "clarification_options") {
              clarificationRef.current = chunk.options;
              scheduleFlush();
              continue;
            }
            if (chunk.type === "error") {
              if (chunk.recoverable) {
                if (ownsPanel())
                  setStatusMessage(`\u26A0 ${chunk.content}`);
              } else {
                const errorMsg =
                  chunk.content || "An unexpected error occurred.";
                fullContentRef.current += `\n\n---\n\n**Error:** ${errorMsg}`;
                scheduleFlush();
              }
              continue;
            }
          }
          const text = typeof chunk === "string" ? chunk : "";
          fullContentRef.current += text;
          scheduleFlush();
        }

        // Use the assistant timestamp captured during streaming,
        // or fall back to now if no tokens arrived at all.
        const finalTs = assistantTimestamp ?? new Date().toISOString();
        const finalContent = fullContentRef.current;
        const finalThinking = thinkingRef.current;
        updateSessionMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = {
            role: "assistant",
            content: finalContent || last.content || "",
            isStreaming: false,
            timestamp: finalTs,
            traceId,
            thinkingContent: finalThinking || undefined,
          };
          return updated;
        });
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        console.warn("[chat] Stream error:", err);

        const errorDetail =
          err instanceof Error ? err.message : String(err);
        const partial = fullContentRef.current;
        const errorSuffix = partial
          ? `\n\n---\n\n**Error:** ${errorDetail}`
          : `Something went wrong: ${errorDetail}. Please try again.`;

        const errorTs = assistantTimestamp ?? new Date().toISOString();
        updateSessionMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: partial ? partial + errorSuffix : errorSuffix,
            isStreaming: false,
            timestamp: errorTs,
          };
          return updated;
        });
      } finally {
        abortRef.current = null;
        streamSessionIdRef.current = null;
        setStreamingSessionId(null);
        setStreamStartTime(null);
        setStatusMessage("");
        completeAgentActivity(sessionId);
        inputRef.current?.focus();
      }
    },
    [
      activeSessionId,
      isStreaming,
      selectedModel,
      selectedAgent,
      sessions,
      setSessions,
      setActiveSessionId,
    ],
  );

  const handleCopyMessage = useCallback(
    async (content: string, idx: number) => {
      await navigator.clipboard.writeText(content);
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(null), 2000);
    },
    [],
  );

  const handleRetry = useCallback(() => {
    if (messages.length < 2) return;
    const lastUserMsg = [...messages]
      .reverse()
      .find((m) => m.role === "user");
    if (!lastUserMsg) return;
    setMessages((prev) => prev.slice(0, -2));
    setTimeout(() => sendMessage(lastUserMsg.content), 100);
  }, [messages, setMessages, sendMessage]);

  const handleFeedback = useCallback(
    async (index: number, sentiment: "positive" | "negative") => {
      setMessages((prev) => {
        const updated = [...prev];
        updated[index] = { ...updated[index], feedback: sentiment };
        return updated;
      });

      const msg = messages[index];
      if (msg?.traceId) {
        try {
          await submitFeedback(msg.traceId, sentiment);
        } catch {
          // Feedback is best-effort; don't disturb the user
        }
      }
    },
    [messages, setMessages],
  );

  const handleCreateProposal = useCallback(
    (yamlContent: string) => {
      createProposalMut.mutate(
        { yaml_content: yamlContent },
        {
          onSuccess: () => {
            navigate("/proposals");
          },
          onError: (err) => {
            console.error(
              "[chat] Failed to create proposal from YAML:",
              err,
            );
          },
        },
      );
    },
    [createProposalMut, navigate],
  );

  return {
    sessions,
    activeSessionId,
    selectedModel,
    setSelectedModel,
    selectedAgent,
    setSelectedAgent,
    messages,
    startNewChat,
    switchSession,
    deleteSession,
    input,
    setInput,
    inputRef,
    isStreaming,
    copiedIdx,
    statusMessage,
    elapsed,
    workflowSelection,
    setWorkflowSelection,
    sendMessage,
    handleCopyMessage,
    handleRetry,
    handleFeedback,
    handleCreateProposal,
    setMessages,
    availableModels,
    recentConversations,
    activityPanelOpen,
  };
}
