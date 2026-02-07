import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Plus,
  Loader2,
  Bot,
  User,
  ChevronDown,
  Copy,
  Check,
  RotateCw,
  Sparkles,
  Zap,
  Lightbulb,
  BarChart3,
  Home,
  Settings,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { ThinkingIndicator } from "@/components/ui/thinking-indicator";
import { cn } from "@/lib/utils";
import { useModels, useConversations } from "@/api/hooks";
import { streamChat } from "@/api/client";
import type { ChatMessage } from "@/lib/types";

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  timestamp?: Date;
}

const SUGGESTIONS = [
  {
    icon: Lightbulb,
    title: "Turn on the",
    highlight: "living room lights",
    message: "Turn on the living room lights",
    color: "text-yellow-400",
  },
  {
    icon: BarChart3,
    title: "Analyze my",
    highlight: "energy usage this week",
    message:
      "Analyze my energy consumption over the past week and suggest optimizations",
    color: "text-emerald-400",
  },
  {
    icon: Settings,
    title: "Create an automation for",
    highlight: "morning routine",
    message:
      "Help me create an automation for my morning routine that turns on lights and adjusts the thermostat",
    color: "text-blue-400",
  },
  {
    icon: Zap,
    title: "Which devices",
    highlight: "use the most power?",
    message:
      "Which devices in my home use the most power? Show me the top energy consumers",
    color: "text-orange-400",
  },
  {
    icon: Home,
    title: "Show me all",
    highlight: "devices that are on",
    message: "List all devices and lights that are currently on",
    color: "text-purple-400",
  },
  {
    icon: Sparkles,
    title: "Run diagnostics on",
    highlight: "my automations",
    message:
      "Check the health of my automations and identify any that aren't working correctly",
    color: "text-pink-400",
  },
];

// Message animation variants
const messageVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] },
  },
};

const suggestionVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.4,
      delay: i * 0.08,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  }),
};

export function ChatPage() {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [streamStartTime, setStreamStartTime] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const { data: modelsData } = useModels();
  const { data: conversationsData } = useConversations();

  const availableModels = modelsData?.data ?? [];
  const recentConversations = conversationsData?.items?.slice(0, 10) ?? [];

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height =
        Math.min(inputRef.current.scrollHeight, 200) + "px";
    }
  }, [input]);

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

  const sendMessage = async (content: string) => {
    if (!content.trim() || isStreaming) return;

    const userMsg: DisplayMessage = {
      role: "user",
      content: content.trim(),
      timestamp: new Date(),
    };
    const assistantMsg: DisplayMessage = {
      role: "assistant",
      content: "",
      isStreaming: true,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setIsStreaming(true);
    setStreamStartTime(Date.now());

    // Build OpenAI message history
    const chatHistory: ChatMessage[] = [
      ...messages.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      })),
      { role: "user" as const, content: content.trim() },
    ];

    try {
      let fullContent = "";
      for await (const chunk of streamChat(selectedModel, chatHistory)) {
        fullContent += chunk;
        setMessages((prev) => {
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
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: fullContent,
          isStreaming: false,
          timestamp: assistantMsg.timestamp,
        };
        return updated;
      });
    } catch {
      setMessages((prev) => {
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
      inputRef.current?.focus();
    }
  };

  const handleCopyMessage = async (content: string, idx: number) => {
    await navigator.clipboard.writeText(content);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setInput("");
    inputRef.current?.focus();
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex h-full">
      {/* Conversation Sidebar */}
      <div className="hidden w-64 flex-col border-r border-border bg-card/50 lg:flex">
        <div className="flex h-14 items-center justify-between border-b border-border px-4">
          <span className="text-sm font-medium text-muted-foreground">
            History
          </span>
          <Button variant="ghost" size="icon" onClick={startNewChat}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-auto p-2">
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
          {recentConversations.length === 0 && (
            <p className="px-3 py-8 text-center text-xs text-muted-foreground">
              No conversations yet
            </p>
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex flex-1 flex-col">
        {/* Model selector header */}
        <div className="flex h-14 items-center justify-between border-b border-border px-4">
          <div className="relative">
            <button
              onClick={() => setShowModelPicker(!showModelPicker)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent"
            >
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              {selectedModel}
              <ChevronDown className="h-3 w-3 opacity-60" />
            </button>
            <AnimatePresence>
              {showModelPicker && (
                <motion.div
                  initial={{ opacity: 0, y: -4, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4, scale: 0.97 }}
                  transition={{ duration: 0.15 }}
                  className="absolute left-0 top-full z-50 mt-1 w-72 rounded-lg border border-border bg-popover p-1 shadow-lg"
                >
                  {availableModels.map((model) => (
                    <button
                      key={model.id}
                      onClick={() => {
                        setSelectedModel(model.id);
                        setShowModelPicker(false);
                      }}
                      className={cn(
                        "w-full rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-accent",
                        model.id === selectedModel && "bg-accent",
                      )}
                    >
                      <div className="font-medium">{model.id}</div>
                      <div className="text-xs text-muted-foreground">
                        {model.owned_by}
                      </div>
                    </button>
                  ))}
                  {availableModels.length === 0 && (
                    <p className="px-3 py-2 text-sm text-muted-foreground">
                      Loading models...
                    </p>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

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
            <Button variant="ghost" size="sm" onClick={startNewChat}>
              <Plus className="mr-1 h-3 w-3" />
              New Chat
            </Button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto">
          {isEmpty ? (
            /* Empty state with suggestions */
            <div className="flex h-full flex-col items-center justify-center px-4">
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="mb-8 text-center"
              >
                <motion.div
                  className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10"
                  animate={{ rotate: [0, 5, -5, 0] }}
                  transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                >
                  <Zap className="h-8 w-8 text-primary" />
                </motion.div>
                <h1 className="mb-2 text-2xl font-semibold">
                  What can I help you with?
                </h1>
                <p className="text-muted-foreground">
                  Ask me anything about your Home Assistant setup
                </p>
              </motion.div>
              <div className="grid max-w-2xl gap-3 sm:grid-cols-2">
                {SUGGESTIONS.map((s, i) => (
                  <motion.button
                    key={i}
                    custom={i}
                    initial="hidden"
                    animate="visible"
                    variants={suggestionVariants}
                    whileHover={{ scale: 1.02, y: -2 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => sendMessage(s.message)}
                    className="group rounded-xl border border-border bg-card p-4 text-left transition-colors hover:border-primary/30 hover:bg-accent"
                  >
                    <s.icon className={cn("mb-2 h-4 w-4", s.color)} />
                    <span className="text-sm text-muted-foreground">
                      {s.title}{" "}
                    </span>
                    <span className="text-sm font-medium">{s.highlight}</span>
                  </motion.button>
                ))}
              </div>
            </div>
          ) : (
            /* Message list */
            <div className="mx-auto max-w-3xl space-y-1 px-4 py-6">
              <AnimatePresence initial={false}>
                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    layout
                    initial="hidden"
                    animate="visible"
                    variants={messageVariants}
                    className={cn(
                      "group relative flex gap-3 rounded-xl px-4 py-4",
                      msg.role === "user"
                        ? "bg-accent/30"
                        : "bg-transparent",
                    )}
                  >
                    {/* Avatar */}
                    <div
                      className={cn(
                        "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-gradient-to-br from-primary/20 to-purple-500/20 text-primary",
                      )}
                    >
                      {msg.role === "user" ? (
                        <User className="h-4 w-4" />
                      ) : (
                        <Bot className="h-4 w-4" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="min-w-0 flex-1">
                      {/* Role label + timestamp */}
                      <div className="mb-1 flex items-center gap-2">
                        <span className="text-xs font-semibold">
                          {msg.role === "user" ? "You" : "Aether"}
                        </span>
                        {msg.timestamp && (
                          <span className="text-[10px] text-muted-foreground/50">
                            {msg.timestamp.toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        )}
                      </div>

                      {/* Message body */}
                      {msg.role === "assistant" ? (
                        <div className="text-sm">
                          {msg.content ? (
                            <>
                              <MarkdownRenderer content={msg.content} />
                              {msg.isStreaming && (
                                <ThinkingIndicator hasContent />
                              )}
                            </>
                          ) : msg.isStreaming ? (
                            <ThinkingIndicator />
                          ) : null}
                        </div>
                      ) : (
                        <MarkdownRenderer
                          content={msg.content}
                          className="text-sm"
                        />
                      )}
                    </div>

                    {/* Action buttons (visible on hover) */}
                    {!msg.isStreaming && msg.content && (
                      <div className="absolute right-2 top-2 flex gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                        <button
                          onClick={() => handleCopyMessage(msg.content, i)}
                          className="rounded-md p-1.5 text-muted-foreground/50 transition-colors hover:bg-accent hover:text-foreground"
                          title="Copy message"
                        >
                          {copiedIdx === i ? (
                            <Check className="h-3.5 w-3.5 text-success" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                        </button>
                        {msg.role === "assistant" &&
                          i === messages.length - 1 && (
                            <button
                              onClick={handleRetry}
                              className="rounded-md p-1.5 text-muted-foreground/50 transition-colors hover:bg-accent hover:text-foreground"
                              title="Retry"
                            >
                              <RotateCw className="h-3.5 w-3.5" />
                            </button>
                          )}
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="border-t border-border p-4">
          <div className="mx-auto max-w-3xl">
            <motion.div
              layout
              className="flex items-end gap-2 rounded-xl border border-border bg-card p-2 transition-colors focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20"
            >
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message Aether..."
                rows={1}
                className="flex-1 resize-none border-0 bg-transparent px-2 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none"
                disabled={isStreaming}
              />
              <Button
                size="icon"
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isStreaming}
                className="shrink-0 transition-transform active:scale-95"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </motion.div>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              Aether can make mistakes. Always review automation proposals before
              deploying.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
