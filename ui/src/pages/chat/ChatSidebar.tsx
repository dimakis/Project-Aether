import { useMemo } from "react";
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ChatSession } from "@/lib/storage";
import type { Conversation } from "@/lib/types";

interface ChatSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  recentConversations: Conversation[];
  onNewChat: () => void;
  onSwitchSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
}

export function ChatSidebar({
  sessions,
  activeSessionId,
  recentConversations,
  onNewChat,
  onSwitchSession,
  onDeleteSession,
}: ChatSidebarProps) {
  const sortedSessions = useMemo(
    () => [...sessions].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    [sessions],
  );

  return (
    <div className="hidden w-64 flex-col border-r border-border bg-card/50 lg:flex">
      <div className="flex h-14 items-center justify-between border-b border-border px-4">
        <span className="text-sm font-medium text-muted-foreground">
          History
        </span>
        <Button variant="ghost" size="icon" onClick={onNewChat}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex-1 overflow-auto p-2">
        {/* Local sessions */}
        {sortedSessions.length > 0 && (
          <div className="mb-3">
            {sortedSessions.map((session) => (
              <button
                key={session.id}
                onClick={() => onSwitchSession(session.id)}
                className={cn(
                  "group/item flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
                  session.id === activeSessionId &&
                    "bg-primary/5 border border-primary/20 text-primary",
                )}
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-50" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm">
                    {session.title}
                  </p>
                  <p className="truncate text-[10px] text-muted-foreground/60">
                    {session.messages.filter((m) => m.role === "user").length} message{session.messages.filter((m) => m.role === "user").length !== 1 ? "s" : ""} &middot;{" "}
                    {new Date(session.updatedAt).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  className="ml-1 shrink-0 rounded p-1 text-muted-foreground/30 opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover/item:opacity-100"
                  title="Delete chat"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </button>
            ))}
          </div>
        )}

        {/* Server-side conversations (if any) */}
        {recentConversations.length > 0 && (
          <>
            <div className="mb-2 mt-1 px-3">
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                Server History
              </p>
            </div>
            {recentConversations.map((conv) => (
              <button
                key={conv.id}
                className="w-full rounded-lg px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                <div className="truncate">
                  {conv.title || "Untitled conversation"}
                </div>
                <div className="mt-0.5 text-xs opacity-60">
                  {new Date(conv.updated_at).toLocaleDateString()}
                </div>
              </button>
            ))}
          </>
        )}

        {sortedSessions.length === 0 && recentConversations.length === 0 && (
          <p className="px-3 py-8 text-center text-xs text-muted-foreground">
            No conversations yet
          </p>
        )}
      </div>
    </div>
  );
}
