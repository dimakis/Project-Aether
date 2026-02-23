import { useState, useRef, useEffect } from "react";
import { Bot, ChevronDown, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAvailableAgents } from "@/api/hooks";
import type { AvailableAgent } from "@/api/client/agents";

const STORAGE_KEY = "aether_selected_agent";
const AUTO_OPTION = "auto";

export interface AgentPickerProps {
  selectedAgent: string;
  onAgentChange: (agent: string) => void;
}

export function AgentPicker({
  selectedAgent,
  onAgentChange,
}: AgentPickerProps) {
  const { data, isLoading } = useAvailableAgents();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const agents: AvailableAgent[] = data?.agents ?? [];

  const selectedLabel =
    selectedAgent === AUTO_OPTION
      ? "Auto (Jarvis)"
      : agents.find((a) => a.name === selectedAgent)?.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) ?? selectedAgent;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-1.5 rounded-md border border-border/50 px-2.5 py-1.5 text-xs transition-colors",
          "hover:bg-accent/50 hover:border-border",
          open && "bg-accent/50 border-border",
        )}
      >
        <Bot className="h-3 w-3 text-muted-foreground" />
        <span className="max-w-[120px] truncate">{selectedLabel}</span>
        {isLoading ? (
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
        ) : (
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        )}
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-56 rounded-lg border border-border bg-popover p-1 shadow-lg">
          <AgentOption
            label="Auto (Jarvis)"
            description="Automatic routing based on intent"
            selected={selectedAgent === AUTO_OPTION}
            onClick={() => {
              onAgentChange(AUTO_OPTION);
              localStorage.setItem(STORAGE_KEY, AUTO_OPTION);
              setOpen(false);
            }}
          />
          {agents.map((agent) => (
            <AgentOption
              key={agent.name}
              label={agent.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              description={agent.domain ?? "general"}
              selected={selectedAgent === agent.name}
              onClick={() => {
                onAgentChange(agent.name);
                localStorage.setItem(STORAGE_KEY, agent.name);
                setOpen(false);
              }}
            />
          ))}
          {agents.length === 0 && !isLoading && (
            <div className="px-3 py-2 text-xs text-muted-foreground">
              No routable agents available
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AgentOption({
  label,
  description,
  selected,
  onClick,
}: {
  label: string;
  description: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs transition-colors",
        "hover:bg-accent/50",
        selected && "bg-accent/80",
      )}
    >
      <div className="flex-1">
        <div className="font-medium">{label}</div>
        <div className="text-[10px] text-muted-foreground">{description}</div>
      </div>
      {selected && <Check className="h-3 w-3 text-primary" />}
    </button>
  );
}

export function getPersistedAgent(): string {
  return localStorage.getItem(STORAGE_KEY) ?? AUTO_OPTION;
}
