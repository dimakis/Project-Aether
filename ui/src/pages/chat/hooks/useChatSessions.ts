import { useMemo, useCallback } from "react";
import { usePersistedState } from "@/hooks/use-persisted-state";
import {
  STORAGE_KEYS,
  generateSessionId,
  autoTitle,
  type DisplayMessage,
  type ChatSession,
} from "@/lib/storage";

export interface UseChatSessionsOptions {
  /** Called after startNewChat or switchSession; use to clear input and focus. */
  onSessionSwitch?: () => void;
}

export interface UseChatSessionsReturn {
  sessions: ChatSession[];
  setSessions: React.Dispatch<React.SetStateAction<ChatSession[]>>;
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  activeSession: ChatSession | null;
  messages: DisplayMessage[];
  setMessages: (
    updater:
      | DisplayMessage[]
      | ((prev: DisplayMessage[]) => DisplayMessage[]),
  ) => void;
  startNewChat: () => void;
  switchSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
}

export function useChatSessions(
  options?: UseChatSessionsOptions,
): UseChatSessionsReturn {
  const { onSessionSwitch } = options ?? {};

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

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );
  const messages = activeSession?.messages ?? [];

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
    },
    [activeSessionId, setSessions],
  );

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
    onSessionSwitch?.();
  }, [selectedModel, setSessions, setActiveSessionId, onSessionSwitch]);

  const switchSession = useCallback(
    (sessionId: string) => {
      setActiveSessionId(sessionId);
      onSessionSwitch?.();
    },
    [setActiveSessionId, onSessionSwitch],
  );

  const deleteSession = useCallback(
    (sessionId: string) => {
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
    },
    [activeSessionId, setSessions, setActiveSessionId],
  );

  return {
    sessions,
    setSessions,
    activeSessionId,
    setActiveSessionId,
    selectedModel,
    setSelectedModel,
    activeSession,
    messages,
    setMessages,
    startNewChat,
    switchSession,
    deleteSession,
  };
}
