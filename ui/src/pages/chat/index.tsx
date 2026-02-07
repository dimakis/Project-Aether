import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Loader2, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { usePersistedState } from "@/hooks/use-persisted-state";
import {
  STORAGE_KEYS,
  generateSessionId,
  autoTitle,
  type DisplayMessage,
  type ChatSession,
} from "@/lib/storage";
import {
  setAgentActivity,
  clearAgentActivity,
  setLastTraceId,
  useActivityPanel,
  toggleActivityPanel,
} from "@/lib/agent-activity-store";
import { useModels, useConversations, useCreateProposal } from "@/api/hooks";
import { streamChat, submitFeedback } from "@/api/client";
import type { ChatMessage } from "@/lib/types";
import { ChatSidebar } from "./ChatSidebar";
import { ChatMessageList } from "./ChatMessageList";
import { ChatInput } from "./ChatInput";
import { ModelPicker } from "./ModelPicker";
import yaml from "js-yaml";

export function ChatPage() {
  const navigate = useNavigate();

  // ─── Multi-session persisted state ──────────────────────────────────
  const [sessions, setSessions] = usePersistedState<ChatSession[]>(
    STORAGE_KEYS.chatSessions,
    [],
  );
  const [activeSessionId, setActiveSessionId] = usePersistedState<
    string | null
  >(STORAGE_KEYS.activeSessionId, null);
  const [selectedModel, setSelectedModel] = usePersistedState<string>(
    STORAGE_KEYS.selectedModel,
    "gpt-4o-mini",
  );

  // ─── Derive active session ─────────────────────────────────────────
  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );
  const messages = activeSession?.messages ?? [];

  // ─── Ephemeral state ───────────────────────────────────────────────
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [streamStartTime, setStreamStartTime] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const { panelOpen: activityPanelOpen } = useActivityPanel();

  const { data: modelsData } = useModels();
  const { data: conversationsData } = useConversations();
  const createProposalMut = useCreateProposal();

  const availableModels = modelsData?.data ?? [];
  const recentConversations = conversationsData?.items?.slice(0, 10) ?? [];

  // ─── Session helpers ───────────────────────────────────────────────

  /** Update messages in the active session */
  const setMessages = useCallback(
    (
      updater:
        | DisplayMessage[]
        | ((prev: DisplayMessage[]) => DisplayMessage[]),
    ) => {
      setSessions((prev) => {
        const idx = prev.findIndex((s) => s.id === activeSessionId);
        if (idx === -1) return prev;
        const session = prev[idx];
        const newMessages =
          typeof updater === "function"
            ? updater(session.messages)
            : updater;
        const updated = { ...session, messages: newMessages, updatedAt: new Date().toISOString() };
        // Auto-title from first user message if still default
        if (updated.title === "New Chat") {
          updated.title = autoTitle(newMessages);
        }
        const next = [...prev];
        next[idx] = updated;
        return next;
      });
    },
    [activeSessionId, setSessions],
  );

  /** Create a new session and make it active */
  const startNewChat = useCallback(() => {
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
    setInput("");
    inputRef.current?.focus();
  }, [selectedModel, setSessions, setActiveSessionId]);

  /** Switch to a session */
  const switchSession = useCallback(
    (sessionId: string) => {
      setActiveSessionId(sessionId);
      setInput("");
    },
    [setActiveSessionId],
  );

  /** Delete a session */
  const deleteSession = useCallback(
    (sessionId: string) => {
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
    },
    [activeSessionId, setSessions, setActiveSessionId],
  );

  // ─── Scrolling & resize ────────────────────────────────────────────

  // Elapsed time counter during streaming
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

  // ─── Send message ──────────────────────────────────────────────────

  const sendMessage = async (content: string) => {
    if (!content.trim() || isStreaming) return;

    // If no active session, create one
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

    // Use direct session update since setMessages uses activeSessionId which may have just been set
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
    setAgentActivity({ isActive: true, activeAgent: "architect" });

    // Build OpenAI message history
    // Get current messages for this session (we need to read from state at this point)
    const currentMessages = sessions.find((s) => s.id === sessionId)?.messages ?? [];
    const chatHistory: ChatMessage[] = [
      ...currentMessages.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      })),
      { role: "user" as const, content: content.trim() },
    ];

    try {
      let fullContent = "";
      let traceId: string | undefined;

      for await (const chunk of streamChat(selectedModel, chatHistory)) {
        if (typeof chunk === "object" && "type" in chunk && chunk.type === "metadata") {
          traceId = chunk.trace_id;
          continue;
        }
        const text = typeof chunk === "string" ? chunk : "";
        fullContent += text;
        updateSessionMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: fullContent,
            isStreaming: true,
            timestamp: assistantMsg.timestamp,
          };
          return updated;
        });
      }

      // Mark streaming as done
      updateSessionMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: fullContent,
          isStreaming: false,
          timestamp: assistantMsg.timestamp,
          traceId,
        };
        return updated;
      });

      // Update trace ID in the global store for the activity panel
      if (traceId) {
        setLastTraceId(traceId);  // persisted to localStorage via global store
      }
    } catch {
      updateSessionMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content:
            "Sorry, I encountered an error processing your request. Please try again.",
          isStreaming: false,
          timestamp: assistantMsg.timestamp,
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
      setStreamStartTime(null);
      clearAgentActivity();
      inputRef.current?.focus();
    }
  };

  const handleCopyMessage = async (content: string, idx: number) => {
    await navigator.clipboard.writeText(content);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const handleCreateProposal = (yamlContent: string) => {
    try {
      const parsed = yaml.load(yamlContent) as Record<string, unknown>;
      const name =
        (parsed.alias as string) ||
        (parsed.name as string) ||
        "Automation from chat";
      const trigger = parsed.trigger || parsed.triggers || [];
      const actions = parsed.action || parsed.actions || [];
      const conditions = parsed.condition || parsed.conditions || undefined;
      const mode = (parsed.mode as string) || "single";
      const description = (parsed.description as string) || undefined;

      createProposalMut.mutate(
        { name, trigger, actions, conditions, mode, description },
        {
          onSuccess: () => {
            navigate("/proposals");
          },
        },
      );
    } catch {
      // If YAML parsing fails, create with raw content as description
      createProposalMut.mutate(
        {
          name: "Automation from chat",
          trigger: {},
          actions: {},
          description: `YAML content:\n${yamlContent}`,
        },
        {
          onSuccess: () => {
            navigate("/proposals");
          },
        },
      );
    }
  };

  const handleRetry = () => {
    if (messages.length < 2) return;
    const lastUserMsg = [...messages]
      .reverse()
      .find((m) => m.role === "user");
    if (!lastUserMsg) return;
    // Remove last user + assistant pair
    setMessages((prev) => prev.slice(0, -2));
    setTimeout(() => sendMessage(lastUserMsg.content), 100);
  };

  const handleFeedback = useCallback(
    async (index: number, sentiment: "positive" | "negative") => {
      // Update local state immediately
      setMessages((prev) => {
        const updated = [...prev];
        updated[index] = { ...updated[index], feedback: sentiment };
        return updated;
      });

      // Send to backend if we have a trace ID
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

  return (
    <div className="flex h-full">
      {/* Conversation Sidebar */}
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        recentConversations={recentConversations}
        onNewChat={startNewChat}
        onSwitchSession={switchSession}
        onDeleteSession={deleteSession}
      />

      {/* Chat Area */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {/* Model selector header */}
          <div className="flex h-14 items-center justify-between border-b border-border px-4">
            <ModelPicker
              selectedModel={selectedModel}
              availableModels={availableModels}
              onModelChange={setSelectedModel}
            />

            <div className="flex items-center gap-2">
              {/* Streaming elapsed timer */}
              <AnimatePresence>
                {isStreaming && (
                  <motion.div
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground"
                  >
                    <Loader2 className="h-3 w-3 animate-spin text-primary" />
                    <span>{selectedModel}</span>
                    <span className="text-muted-foreground/50">|</span>
                    <span className="tabular-nums">{elapsed}s</span>
                  </motion.div>
                )}
              </AnimatePresence>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleActivityPanel}
                className={cn(
                  activityPanelOpen && "bg-primary/10 text-primary",
                )}
                title="Toggle agent activity panel"
              >
                <Activity className="mr-1 h-3 w-3" />
                Activity
              </Button>
              <Button variant="ghost" size="sm" onClick={startNewChat}>
                <Plus className="mr-1 h-3 w-3" />
                New Chat
              </Button>
            </div>
          </div>

          {/* Messages */}
          <ChatMessageList
            messages={messages}
            activeSessionId={activeSessionId}
            copiedIdx={copiedIdx}
            onCopy={handleCopyMessage}
            onRetry={handleRetry}
            onFeedback={handleFeedback}
            onCreateProposal={handleCreateProposal}
            onSuggestionClick={sendMessage}
          />

          {/* Input area */}
          <ChatInput
            value={input}
            onChange={setInput}
            onSend={() => sendMessage(input)}
            isStreaming={isStreaming}
          />
        </div>
      </div>
    </div>
  );
}

export default ChatPage;
