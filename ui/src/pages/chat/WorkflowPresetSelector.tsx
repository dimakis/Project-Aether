import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  BarChart3,
  Zap,
  Stethoscope,
  LayoutDashboard,
  MessageSquare,
  Settings2,
  Check,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { useWorkflowPresets } from "@/api/hooks";
import type { WorkflowPreset } from "@/api/client";

// ─── Icon mapping ─────────────────────────────────────────────────────────────

const PRESET_ICONS: Record<string, typeof BarChart3> = {
  "bar-chart-3": BarChart3,
  zap: Zap,
  stethoscope: Stethoscope,
  "layout-dashboard": LayoutDashboard,
  "message-square": MessageSquare,
};

// ─── Agent Toggle Panel ───────────────────────────────────────────────────────

interface AgentToggleProps {
  agents: string[];
  disabledAgents: Set<string>;
  onToggle: (agentId: string) => void;
}

const AGENT_DISPLAY: Record<string, { label: string; color: string }> = {
  architect: { label: "Architect", color: "text-blue-400" },
  energy_analyst: { label: "Energy Analyst", color: "text-yellow-400" },
  behavioral_analyst: { label: "Behavioral Analyst", color: "text-teal-400" },
  diagnostic_analyst: { label: "Diagnostic Analyst", color: "text-rose-400" },
  dashboard_designer: { label: "Dashboard Designer", color: "text-indigo-400" },
  developer: { label: "Developer", color: "text-amber-400" },
  librarian: { label: "Librarian", color: "text-purple-400" },
};

function AgentTogglePanel({ agents, disabledAgents, onToggle }: AgentToggleProps) {
  return (
    <div className="space-y-1 pt-1">
      <p className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground/50">
        Active Agents
      </p>
      {agents.map((agentId) => {
        const display = AGENT_DISPLAY[agentId] ?? {
          label: agentId,
          color: "text-muted-foreground",
        };
        const isDisabled = disabledAgents.has(agentId);

        return (
          <button
            key={agentId}
            onClick={() => onToggle(agentId)}
            className={cn(
              "flex w-full items-center gap-2 rounded-md px-2 py-1 text-xs transition-colors",
              isDisabled
                ? "opacity-40 hover:opacity-60"
                : "hover:bg-accent/50",
            )}
          >
            <div
              className={cn(
                "flex h-4 w-4 items-center justify-center rounded border transition-colors",
                isDisabled
                  ? "border-muted-foreground/30 bg-transparent"
                  : "border-primary bg-primary",
              )}
            >
              {!isDisabled && <Check className="h-2.5 w-2.5 text-primary-foreground" />}
            </div>
            <span className={cn("font-medium", isDisabled ? "text-muted-foreground" : display.color)}>
              {display.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

// ─── Preset Selector ──────────────────────────────────────────────────────────

export interface WorkflowSelection {
  preset: WorkflowPreset | null;
  disabledAgents: Set<string>;
}

interface WorkflowPresetSelectorProps {
  selection: WorkflowSelection;
  onSelectionChange: (selection: WorkflowSelection) => void;
}

export function WorkflowPresetSelector({
  selection,
  onSelectionChange,
}: WorkflowPresetSelectorProps) {
  const [open, setOpen] = useState(false);
  const [showToggles, setShowToggles] = useState(false);
  const { data } = useWorkflowPresets();

  const presets = data?.presets ?? [];
  const activePreset = selection.preset;

  const handleSelect = (preset: WorkflowPreset) => {
    onSelectionChange({
      preset,
      disabledAgents: new Set(),
    });
    setOpen(false);
    setShowToggles(false);
  };

  const handleToggleAgent = (agentId: string) => {
    const next = new Set(selection.disabledAgents);
    if (next.has(agentId)) {
      next.delete(agentId);
    } else {
      next.add(agentId);
    }
    onSelectionChange({ ...selection, disabledAgents: next });
  };

  const activeIcon = activePreset?.icon
    ? PRESET_ICONS[activePreset.icon] ?? MessageSquare
    : MessageSquare;
  const ActiveIcon = activeIcon;

  return (
    <div className="relative">
      {/* Trigger button */}
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium transition-colors",
          "hover:bg-accent/50",
          open && "bg-accent/50 border-primary/30",
        )}
      >
        <ActiveIcon className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="max-w-[120px] truncate">
          {activePreset?.name ?? "General Chat"}
        </span>
        {selection.disabledAgents.size > 0 && (
          <Badge variant="outline" className="ml-0.5 h-4 px-1 text-[8px]">
            -{selection.disabledAgents.size}
          </Badge>
        )}
        <ChevronDown
          className={cn(
            "h-3 w-3 text-muted-foreground/50 transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 top-full z-50 mt-1 w-72 rounded-xl border border-border bg-card shadow-xl"
          >
            {/* Preset list */}
            <div className="p-1.5">
              <p className="px-2 pb-1 text-[9px] font-semibold uppercase tracking-wider text-muted-foreground/50">
                Workflow Presets
              </p>
              {presets.map((preset) => {
                const PresetIcon = preset.icon
                  ? PRESET_ICONS[preset.icon] ?? MessageSquare
                  : MessageSquare;
                const isActive = activePreset?.id === preset.id;

                return (
                  <button
                    key={preset.id}
                    onClick={() => handleSelect(preset)}
                    className={cn(
                      "flex w-full items-start gap-2.5 rounded-lg px-2 py-2 text-left transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-accent/50",
                    )}
                  >
                    <PresetIcon className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold">
                          {preset.name}
                        </span>
                        {isActive && (
                          <Check className="h-3 w-3 text-primary" />
                        )}
                      </div>
                      <p className="text-[10px] leading-relaxed text-muted-foreground">
                        {preset.description}
                      </p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {preset.agents.map((a) => (
                          <Badge
                            key={a}
                            variant="outline"
                            className="text-[8px]"
                          >
                            {AGENT_DISPLAY[a]?.label ?? a}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Agent toggles section */}
            {activePreset && activePreset.agents.length > 1 && (
              <div className="border-t border-border px-3 pb-2 pt-1.5">
                <button
                  onClick={() => setShowToggles(!showToggles)}
                  className="flex w-full items-center gap-1.5 text-[10px] font-medium text-muted-foreground/60 hover:text-muted-foreground"
                >
                  <Settings2 className="h-3 w-3" />
                  Customize agents
                  <ChevronDown
                    className={cn(
                      "ml-auto h-2.5 w-2.5 transition-transform",
                      showToggles && "rotate-180",
                    )}
                  />
                </button>

                <AnimatePresence>
                  {showToggles && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className="overflow-hidden"
                    >
                      <AgentTogglePanel
                        agents={activePreset.agents}
                        disabledAgents={selection.disabledAgents}
                        onToggle={handleToggleAgent}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
