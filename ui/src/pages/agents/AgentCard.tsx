import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  ChevronRight,
  ChevronDown,
  Cpu,
  Thermometer,
  Settings2,
  FileText,
  History,
  Ban,
  Copy,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUpdateAgentStatus, useCloneAgent, useQuickModelSwitch, useModels } from "@/api/hooks";
import type { AgentDetail, AgentStatusValue } from "@/lib/types";
import { AGENT_LABELS, STATUS_COLORS, type Tab } from "./constants";
import { OverviewTab } from "./OverviewTab";
import { ConfigTab } from "./ConfigTab";
import { PromptTab } from "./PromptTab";
import { HistoryTab } from "./HistoryTab";

export function AgentCard({
  agent,
  isSelected,
  isProgrammatic,
  onToggle,
}: {
  agent: AgentDetail;
  isSelected: boolean;
  isProgrammatic?: boolean;
  onToggle: () => void;
}) {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [showModelPicker, setShowModelPicker] = useState(false);
  const statusMutation = useUpdateAgentStatus();
  const cloneMutation = useCloneAgent();
  const modelSwitchMutation = useQuickModelSwitch();
  const { data: modelsData } = useModels();
  const isDisabled = agent.status === "disabled";
  const availableModels = modelsData?.data ?? [];

  const handleStatusChange = (status: AgentStatusValue) => {
    statusMutation.mutate({ name: agent.name, status });
  };

  return (
    <Card className={cn("overflow-hidden", isDisabled && "opacity-60")}>
      {/* Card Header - always visible */}
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-4 px-6 py-4 text-left transition-colors hover:bg-accent/30"
      >
        {isSelected ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
        {isDisabled ? (
          <Ban className="h-5 w-5 text-muted-foreground" />
        ) : (
          <Bot className="h-5 w-5 text-primary" />
        )}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={cn("font-semibold", isDisabled && "text-muted-foreground")}>
              {AGENT_LABELS[agent.name] ?? agent.name}
            </span>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] font-medium ring-1",
                STATUS_COLORS[agent.status as AgentStatusValue],
              )}
            >
              {agent.status}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">{agent.description}</p>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {agent.active_config?.model_name && !showModelPicker && (
            <button
              className="flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors hover:bg-accent"
              onClick={(e) => {
                e.stopPropagation();
                setShowModelPicker(true);
              }}
              title="Click to switch model"
            >
              <Cpu className="h-3 w-3" />
              {agent.active_config.model_name}
            </button>
          )}
          {showModelPicker && (
            <select
              className="h-7 rounded border border-border bg-background px-2 text-xs"
              value={agent.active_config?.model_name ?? ""}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => {
                e.stopPropagation();
                const newModel = e.target.value;
                if (newModel && newModel !== agent.active_config?.model_name) {
                  modelSwitchMutation.mutate({ name: agent.name, modelName: newModel });
                }
                setShowModelPicker(false);
              }}
              onBlur={() => setShowModelPicker(false)}
              autoFocus
            >
              {availableModels.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id}
                </option>
              ))}
            </select>
          )}
          {agent.active_config?.temperature != null && (
            <span className="flex items-center gap-1">
              <Thermometer className="h-3 w-3" />
              {agent.active_config.temperature}
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="ml-2 h-7 px-2 text-muted-foreground hover:text-foreground"
          onClick={(e) => {
            e.stopPropagation();
            cloneMutation.mutate(agent.name);
          }}
          disabled={cloneMutation.isPending}
          title="Clone agent"
        >
          <Copy className="h-3.5 w-3.5" />
        </Button>
      </button>

      {/* Expanded Detail */}
      <AnimatePresence>
        {isSelected && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border">
              {/* Tab navigation */}
              <div className="flex gap-1 border-b border-border px-6 pt-2">
                {(
                  isProgrammatic
                    ? [
                        { key: "overview" as const, label: "Overview", icon: Settings2 },
                      ]
                    : [
                        { key: "overview" as const, label: "Overview", icon: Settings2 },
                        { key: "config" as const, label: "Config", icon: Cpu },
                        { key: "prompt" as const, label: "Prompt", icon: FileText },
                        { key: "history" as const, label: "History", icon: History },
                      ]
                ).map(({ key, label, icon: Icon }) => (
                  <button
                    key={key}
                    onClick={() => setActiveTab(key)}
                    className={cn(
                      "flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                      activeTab === key
                        ? "border-primary text-primary"
                        : "border-transparent text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="p-6">
                {activeTab === "overview" && (
                  <OverviewTab
                    agent={agent}
                    onStatusChange={handleStatusChange}
                    statusPending={statusMutation.isPending}
                  />
                )}
                {activeTab === "config" && (
                  <ConfigTab agentName={agent.name} />
                )}
                {activeTab === "prompt" && (
                  <PromptTab agentName={agent.name} />
                )}
                {activeTab === "history" && (
                  <HistoryTab agentName={agent.name} />
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
