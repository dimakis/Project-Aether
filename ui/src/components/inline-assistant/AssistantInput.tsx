/**
 * Input area sub-component for InlineAssistant.
 */

import { Send, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface AssistantInputProps {
  input: string;
  onInputChange: (value: string) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  placeholder: string;
  isStreaming: boolean;
  hasMessages: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  onSend: () => void;
  onClearChat: () => void;
}

export function AssistantInput({
  input,
  onInputChange,
  onKeyDown,
  placeholder,
  isStreaming,
  hasMessages,
  inputRef,
  onSend,
  onClearChat,
}: AssistantInputProps) {
  return (
    <div className="border-t border-border px-4 py-2">
      <div className="flex items-end gap-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          rows={1}
          className="flex-1 resize-none border-0 bg-transparent px-1 py-1.5 text-xs placeholder:text-muted-foreground focus:outline-none"
          disabled={isStreaming}
        />
        <div className="flex items-center gap-1">
          {hasMessages && !isStreaming && (
            <Button
              size="icon"
              variant="ghost"
              onClick={onClearChat}
              className="h-7 w-7"
              aria-label="Clear chat"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            size="icon"
            onClick={onSend}
            disabled={!input.trim() || isStreaming}
            className="h-7 w-7"
            aria-label={isStreaming ? "Sending message" : "Send message"}
          >
            {isStreaming ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
