import { useState, useRef, useEffect } from "react";
import { Sparkles, Send, Loader2, Sun, Home, Lightbulb } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { streamChat } from "@/api/client";
import type { ChatMessage } from "@/lib/types";

const PROMPT_SUGGESTIONS = [
  {
    icon: Sun,
    label: "Automate lights at sunset",
    message: "Create an automation that turns on the living room lights at sunset",
  },
  {
    icon: Home,
    label: "Create a motion-activated scene",
    message: "Create a scene that activates lights when motion is detected in the hallway",
  },
  {
    icon: Lightbulb,
    label: "Optimize heating schedule",
    message: "Create an automation to optimize my heating schedule based on time of day",
  },
];

interface ArchitectPromptProps {
  onResponse?: (response: string) => void;
}

export function ArchitectPrompt({ onResponse }: ArchitectPromptProps) {
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [response, setResponse] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async (message: string) => {
    if (!message.trim() || isStreaming) return;

    setInput("");
    setIsStreaming(true);
    setResponse(null);

    const chatHistory: ChatMessage[] = [
      {
        role: "system",
        content:
          "The user is on the Proposals page and wants you to create a proposal. " +
          "Use the seek_approval tool to submit your proposal. " +
          "Be concise and action-oriented.",
      },
      { role: "user", content: message.trim() },
    ];

    try {
      let fullContent = "";
      for await (const chunk of streamChat("gpt-4o-mini", chatHistory)) {
        if (typeof chunk === "object" && "type" in chunk && chunk.type === "metadata") {
          continue;
        }
        const text = typeof chunk === "string" ? chunk : "";
        fullContent += text;
        setResponse(fullContent);
      }
      if (onResponse) {
        onResponse(fullContent);
      }
    } catch {
      setResponse("Sorry, I encountered an error. Please try again.");
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(input);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height =
        Math.min(inputRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  return (
    <div className="mb-6">
      <Card>
        <CardContent className="p-4">
          {/* Input area */}
          <div className="flex items-end gap-2">
            <div className="flex min-w-0 flex-1 items-end gap-2 rounded-lg border border-border bg-background p-2 transition-colors focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20">
              <Sparkles className="mb-1 h-4 w-4 shrink-0 text-primary/60" />
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask the Architect to design an automation..."
                rows={1}
                className="flex-1 resize-none border-0 bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none"
                disabled={isStreaming}
              />
              <Button
                size="icon"
                variant="ghost"
                onClick={() => handleSubmit(input)}
                disabled={!input.trim() || isStreaming}
                className="shrink-0"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Suggestion chips */}
          {!response && !isStreaming && (
            <div className="mt-3 flex flex-wrap gap-2">
              {PROMPT_SUGGESTIONS.map((s) => (
                <button
                  key={s.label}
                  onClick={() => handleSubmit(s.message)}
                  className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/30 hover:bg-accent hover:text-foreground"
                >
                  <s.icon className="h-3 w-3" />
                  {s.label}
                </button>
              ))}
            </div>
          )}

          {/* Response area */}
          {(response || isStreaming) && (
            <div className="mt-3 rounded-lg bg-muted/50 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
                <Sparkles className="h-3 w-3" />
                Architect
                {isStreaming && <Loader2 className="h-2.5 w-2.5 animate-spin" />}
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                {response || "Thinking..."}
              </p>
              {!isStreaming && response && (
                <button
                  onClick={() => setResponse(null)}
                  className="mt-2 text-xs text-muted-foreground/50 transition-colors hover:text-foreground"
                >
                  Dismiss
                </button>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
