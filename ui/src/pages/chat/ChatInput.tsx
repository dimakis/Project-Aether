import { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  isStreaming: boolean;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  isStreaming,
  disabled = false,
}: ChatInputProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      // Allow typing while streaming, but don't send
      if (!isStreaming) {
        onSend();
      }
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height =
        Math.min(inputRef.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  // Autofocus on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="border-t border-border p-4">
      <div className="mx-auto max-w-3xl">
        <motion.div
          className="flex items-end gap-2 rounded-xl border border-border bg-card px-3 py-2 transition-colors focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20"
        >
          <textarea
            ref={inputRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message Aether..."
            rows={1}
            className="flex-1 resize-none border-0 bg-transparent py-1 text-sm placeholder:text-muted-foreground focus:outline-none"
            disabled={disabled}
          />
          <Button
            size="icon"
            onClick={onSend}
            disabled={!value.trim() || isStreaming || disabled}
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
          Aether can make mistakes. Always review automation proposals
          before deploying.
        </p>
      </div>
    </div>
  );
}
