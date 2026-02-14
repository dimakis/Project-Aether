import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  setAgentActivity,
  completeAgentActivity,
  setLastTraceId,
  useActivityPanel,
  getActivitySnapshot,
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
import type { ChatMessage } from "@/lib/types";
import { useChatSessions } from "./useChatSessions";
import type { WorkflowSelection } from "../WorkflowPresetSelector";


export interface UseChatMessagesReturn {
  sessions: ChatSession[];
  activeSessionId: string | null;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
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
  availableModels: { id: string }[];
  recentConversations: { id: string; title: string | null }[];
  activityPanelOpen: boolean;
}

export function useChatMessages(): UseChatMessagesReturn {
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [streamStartTime, setStreamStartTime] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [workflowSelection, setWorkflowSelection] = useState<WorkflowSelection>({
    preset: null,
    disabledAgents: new Set(),
  });

  const abortRef = useRef<AbortController | null>(null);
  const streamContentRef = useRef("");
  const streamThinkingRef = useRef("");
  const streamSessionIdRef = useRef<string | null>(null);

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
    onSessionSwitch: () => {
      setInput("");
      inputRef.current?.focus();
    },
  });

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

  useEffect(() => {
    return () => {
      const controller = abortRef.current;
      if (!controller) return;

      controller.abort();
      abortRef.current = null;

      const content = streamContentRef.current;
      const sessionId = streamSessionIdRef.current;
      if (!sessionId) return;

      const stored = storageGet<ChatSession[]>(STORAGE_KEYS.chatSessions, []);
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

  useEffect(() => {
    if (!streamStartTime) {
      setElapsed(0);
      return;
    }
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - streamStartTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [streamStartTime]);

  const sendMessage = useCallback(
    async (content: string) => {
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

      const now = new Date().toISOString();
      const userMsg: DisplayMessage = {
        role: "user",
        content: content.trim(),
        timestamp: now,
      };
      const assistantMsg: DisplayMessage = {
        role: "assistant",
        content: "",
        isStreaming: true,
        timestamp: now,
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
      setIsStreaming(true);
      setStreamStartTime(Date.now());
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

      const scheduleFlush = () => {
        if (rafPending.current) return;
        rafPending.current = true;
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
              timestamp: assistantMsg.timestamp,
              thinkingContent: thinkingSnapshot || undefined,
            };
            return updated;
          });
        });
      };

      try {
        let traceId: string | undefined;

        for await (const chunk of streamChat(
          selectedModel,
          chatHistory,
          sessionId,
          controller.signal,
        )) {
          if (typeof chunk === "object" && "type" in chunk) {
            if (chunk.type === "metadata") {
              if (chunk.trace_id) {
                traceId = chunk.trace_id;
                setLastTraceId(traceId);
              }
              continue;
            }
            if (chunk.type === "trace") {
              handleTraceEvent(
                chunk as TraceEventChunk,
                setAgentActivity,
                getActivitySnapshot(),
              );
              continue;
            }
            if (chunk.type === "status") {
              setStatusMessage(chunk.content);
              continue;
            }
            if (chunk.type === "thinking") {
              const delta = chunk.content ?? "";
              thinkingRef.current += delta;
              const current = getActivitySnapshot();
              setAgentActivity({
                thinkingStream: (current.thinkingStream ?? "") + delta,
              });
              scheduleFlush();
              continue;
            }
            if (chunk.type === "delegation") {
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
              continue;
            }
          }
          const text = typeof chunk === "string" ? chunk : "";
          fullContentRef.current += text;
          scheduleFlush();
        }

        const finalContent = fullContentRef.current;
        const finalThinking = thinkingRef.current;
        updateSessionMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = {
            role: "assistant",
            content: finalContent || last.content || "",
            isStreaming: false,
            timestamp: assistantMsg.timestamp,
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
        updateSessionMessages((prev) => {
          const updated = [...prev];
          const partial = fullContentRef.current;
          updated[updated.length - 1] = {
            role: "assistant",
            content:
              partial ||
              "Sorry, I encountered an error processing your request. Please try again.",
            isStreaming: false,
            timestamp: assistantMsg.timestamp,
          };
          return updated;
        });
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
        setStreamStartTime(null);
        setStatusMessage("");
        completeAgentActivity();
        inputRef.current?.focus();
      }
    },
    [
      activeSessionId,
      isStreaming,
      selectedModel,
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
      // Send raw YAML to the backend — the server parses, normalizes,
      // validates, and extracts trigger/action/condition/mode/name
      // via the canonical schema pipeline (parse_ha_yaml).
      createProposalMut.mutate(
        { yaml_content: yamlContent },
        {
          onSuccess: () => {
            navigate("/proposals");
          },
          onError: (err) => {
            console.error("[chat] Failed to create proposal from YAML:", err);
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
