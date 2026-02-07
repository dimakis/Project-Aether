import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  ChevronRight,
  ChevronDown,
  Power,
  PowerOff,
  Star,
  Plus,
  Loader2,
  Check,
  ArrowUpCircle,
  RotateCcw,
  Trash2,
  Pencil,
  Cpu,
  Thermometer,
  FileText,
  History,
  Settings2,
  Sparkles,
  Workflow,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  useAgents,
  useAgent,
  useAgentConfigVersions,
  useAgentPromptVersions,
  useUpdateAgentStatus,
  useSeedAgents,
  useCreateConfigVersion,
  usePromoteConfigVersion,
  useRollbackConfig,
  useCreatePromptVersion,
  usePromotePromptVersion,
  useRollbackPrompt,
  useDeleteConfigVersion,
  useDeletePromptVersion,
  useModels,
} from "@/api/hooks";
import { ModelPicker } from "@/pages/chat/ModelPicker";
import type {
  AgentDetail,
  AgentStatusValue,
  ConfigVersion,
  PromptVersion,
  VersionStatusValue,
} from "@/lib/types";

// ─── Constants ───────────────────────────────────────────────────────────────

const AGENT_LABELS: Record<string, string> = {
  architect: "Architect",
  data_scientist: "Data Scientist",
  librarian: "Librarian",
  developer: "Developer",
  orchestrator: "Orchestrator",
  categorizer: "Categorizer",
};

const STATUS_COLORS: Record<AgentStatusValue, string> = {
  disabled: "bg-red-500/15 text-red-400 ring-red-500/30",
  enabled: "bg-emerald-500/15 text-emerald-400 ring-emerald-500/30",
  primary: "bg-amber-500/15 text-amber-400 ring-amber-500/30",
};

const VERSION_STATUS_COLORS: Record<VersionStatusValue, string> = {
  draft: "bg-blue-500/15 text-blue-400 ring-blue-500/30",
  active: "bg-emerald-500/15 text-emerald-400 ring-emerald-500/30",
  archived: "bg-zinc-500/15 text-zinc-400 ring-zinc-500/30",
};

type Tab = "overview" | "config" | "prompt" | "history";

// ─── Page ────────────────────────────────────────────────────────────────────

export function AgentsPage() {
  const { data, isLoading, error } = useAgents();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const seedMutation = useSeedAgents();

  const agentsList = data?.agents ?? [];

  // Split into LLM-backed agents (have a model configured) and programmatic agents
  const llmAgents = agentsList.filter(
    (a) => a.active_config?.model_name,
  );
  const programmaticAgents = agentsList.filter(
    (a) => !a.active_config?.model_name,
  );

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Agent Configuration
          </h1>
          <p className="text-sm text-muted-foreground">
            Configure LLM models, prompts, and lifecycle for each agent.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => seedMutation.mutate()}
          disabled={seedMutation.isPending}
        >
          {seedMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="mr-2 h-4 w-4" />
          )}
          Seed Defaults
        </Button>
      </div>

      {/* Loading / Error / Empty states */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {error && (
        <Card className="border-destructive/50">
          <CardContent className="pt-6 text-center text-destructive">
            Failed to load agents. {error instanceof Error ? error.message : ""}
          </CardContent>
        </Card>
      )}

      {!isLoading && agentsList.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Bot className="mx-auto mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="text-muted-foreground">
              No agents configured yet.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => seedMutation.mutate()}
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Seed Default Agents
            </Button>
          </CardContent>
        </Card>
      )}

      {/* LLM Agents */}
      {llmAgents.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            <h2 className="text-lg font-semibold">LLM Agents</h2>
            <span className="text-xs text-muted-foreground">
              Backed by language models
            </span>
          </div>
          {llmAgents.map((agent) => (
            <AgentCard
              key={agent.name}
              agent={agent}
              isSelected={selectedAgent === agent.name}
              onToggle={() =>
                setSelectedAgent(
                  selectedAgent === agent.name ? null : agent.name,
                )
              }
            />
          ))}
        </div>
      )}

      {/* Programmatic Agents */}
      {programmaticAgents.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Workflow className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-lg font-semibold">Programmatic Agents</h2>
            <span className="text-xs text-muted-foreground">
              Rule-based, no LLM required
            </span>
          </div>
          {programmaticAgents.map((agent) => (
            <AgentCard
              key={agent.name}
              agent={agent}
              isSelected={selectedAgent === agent.name}
              isProgrammatic
              onToggle={() =>
                setSelectedAgent(
                  selectedAgent === agent.name ? null : agent.name,
                )
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Agent Card ──────────────────────────────────────────────────────────────

function AgentCard({
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
  const statusMutation = useUpdateAgentStatus();

  const handleStatusChange = (status: AgentStatusValue) => {
    statusMutation.mutate({ name: agent.name, status });
  };

  return (
    <Card className="overflow-hidden">
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
        <Bot className="h-5 w-5 text-primary" />
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold">
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
          {agent.active_config?.model_name && (
            <span className="flex items-center gap-1">
              <Cpu className="h-3 w-3" />
              {agent.active_config.model_name}
            </span>
          )}
          {agent.active_config?.temperature != null && (
            <span className="flex items-center gap-1">
              <Thermometer className="h-3 w-3" />
              {agent.active_config.temperature}
            </span>
          )}
        </div>
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

// ─── Overview Tab ────────────────────────────────────────────────────────────

function OverviewTab({
  agent,
  onStatusChange,
  statusPending,
}: {
  agent: AgentDetail;
  onStatusChange: (status: AgentStatusValue) => void;
  statusPending: boolean;
}) {
  return (
    <div className="space-y-4">
      {/* Status controls */}
      <div>
        <h3 className="mb-2 text-sm font-medium">Status</h3>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={agent.status === "enabled" ? "default" : "outline"}
            onClick={() => onStatusChange("enabled")}
            disabled={statusPending || agent.status === "enabled"}
          >
            <Power className="mr-1.5 h-3.5 w-3.5" />
            Enabled
          </Button>
          <Button
            size="sm"
            variant={agent.status === "disabled" ? "destructive" : "outline"}
            onClick={() => onStatusChange("disabled")}
            disabled={statusPending || agent.status === "disabled"}
          >
            <PowerOff className="mr-1.5 h-3.5 w-3.5" />
            Disabled
          </Button>
          <Button
            size="sm"
            variant={agent.status === "primary" ? "default" : "outline"}
            onClick={() => onStatusChange("primary")}
            disabled={statusPending || agent.status === "primary"}
          >
            <Star className="mr-1.5 h-3.5 w-3.5" />
            Primary
          </Button>
        </div>
      </div>

      {/* Current config summary */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              Active Config
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {agent.active_config ? (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Model</span>
                  <span className="font-mono text-xs">
                    {agent.active_config.model_name ?? "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Temperature</span>
                  <span>{agent.active_config.temperature ?? "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Fallback</span>
                  <span className="font-mono text-xs">
                    {agent.active_config.fallback_model ?? "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Version</span>
                  <span>v{agent.active_config.version_number}</span>
                </div>
              </>
            ) : (
              <p className="text-muted-foreground">No active config</p>
            )}
          </CardContent>
        </Card>

        <Card className="bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              Active Prompt
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {agent.active_prompt ? (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Version</span>
                  <span>v{agent.active_prompt.version_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Length</span>
                  <span>
                    {agent.active_prompt.prompt_template.length} chars
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                  {agent.active_prompt.prompt_template.slice(0, 150)}...
                </p>
              </>
            ) : (
              <p className="text-muted-foreground">No active prompt</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ─── Config Tab ──────────────────────────────────────────────────────────────

function ConfigTab({ agentName }: { agentName: string }) {
  const { data: versions, isLoading } = useAgentConfigVersions(agentName);
  const { data: modelsData } = useModels();
  const [showCreate, setShowCreate] = useState(false);
  const [modelName, setModelName] = useState("");
  const [temperature, setTemperature] = useState("");
  const [fallbackModel, setFallbackModel] = useState("");
  const [changeSummary, setChangeSummary] = useState("");

  const createMutation = useCreateConfigVersion();
  const promoteMutation = usePromoteConfigVersion();
  const rollbackMutation = useRollbackConfig();
  const deleteMutation = useDeleteConfigVersion();

  const handleCreate = () => {
    createMutation.mutate(
      {
        name: agentName,
        data: {
          model_name: modelName || undefined,
          temperature: temperature ? parseFloat(temperature) : undefined,
          fallback_model: fallbackModel || undefined,
          change_summary: changeSummary || undefined,
        },
      },
      {
        onSuccess: () => {
          setShowCreate(false);
          setModelName("");
          setTemperature("");
          setFallbackModel("");
          setChangeSummary("");
        },
      },
    );
  };

  const hasDraft = versions?.some((v) => v.status === "draft");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Config Versions</h3>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => rollbackMutation.mutate(agentName)}
            disabled={rollbackMutation.isPending || hasDraft}
          >
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
            Rollback
          </Button>
          <Button
            size="sm"
            onClick={() => setShowCreate(true)}
            disabled={showCreate || hasDraft}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            New Version
          </Button>
        </div>
      </div>

      {/* Create form */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <Card className="border-blue-500/30 bg-blue-500/5">
              <CardContent className="space-y-3 pt-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="flex items-center rounded-md border border-input px-1">
                    <ModelPicker
                      selectedModel={modelName || "Select model..."}
                      availableModels={modelsData?.data ?? []}
                      onModelChange={(id) => setModelName(id)}
                    />
                  </div>
                  <Input
                    placeholder="Temperature (0.0-2.0)"
                    type="number"
                    min="0"
                    max="2"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => setTemperature(e.target.value)}
                  />
                </div>
                <Input
                  placeholder="Fallback model (optional)"
                  value={fallbackModel}
                  onChange={(e) => setFallbackModel(e.target.value)}
                />
                <Input
                  placeholder="Change summary"
                  value={changeSummary}
                  onChange={(e) => setChangeSummary(e.target.value)}
                />
                <div className="flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowCreate(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleCreate}
                    disabled={createMutation.isPending}
                  >
                    {createMutation.isPending && (
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    )}
                    Create Draft
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Version list */}
      {isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-2">
          {versions?.map((v) => (
            <VersionRow
              key={v.id}
              version={v}
              type="config"
              onPromote={() =>
                promoteMutation.mutate({ name: agentName, versionId: v.id })
              }
              onDelete={() =>
                deleteMutation.mutate({ name: agentName, versionId: v.id })
              }
              promotePending={promoteMutation.isPending}
              deletePending={deleteMutation.isPending}
            />
          ))}
          {versions?.length === 0 && (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No config versions yet. Create one or seed defaults.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Prompt Tab ──────────────────────────────────────────────────────────────

function PromptTab({ agentName }: { agentName: string }) {
  const { data: versions, isLoading } = useAgentPromptVersions(agentName);
  const [showCreate, setShowCreate] = useState(false);
  const [promptTemplate, setPromptTemplate] = useState("");
  const [changeSummary, setChangeSummary] = useState("");

  const createMutation = useCreatePromptVersion();
  const promoteMutation = usePromotePromptVersion();
  const rollbackMutation = useRollbackPrompt();
  const deleteMutation = useDeletePromptVersion();

  const handleCreate = () => {
    if (!promptTemplate.trim()) return;
    createMutation.mutate(
      {
        name: agentName,
        data: {
          prompt_template: promptTemplate,
          change_summary: changeSummary || undefined,
        },
      },
      {
        onSuccess: () => {
          setShowCreate(false);
          setPromptTemplate("");
          setChangeSummary("");
        },
      },
    );
  };

  const hasDraft = versions?.some((v) => v.status === "draft");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Prompt Versions</h3>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => rollbackMutation.mutate(agentName)}
            disabled={rollbackMutation.isPending || hasDraft}
          >
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
            Rollback
          </Button>
          <Button
            size="sm"
            onClick={() => setShowCreate(true)}
            disabled={showCreate || hasDraft}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            New Version
          </Button>
        </div>
      </div>

      {/* Create form */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <Card className="border-blue-500/30 bg-blue-500/5">
              <CardContent className="space-y-3 pt-4">
                <textarea
                  className="min-h-[200px] w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="Enter system prompt template..."
                  value={promptTemplate}
                  onChange={(e) => setPromptTemplate(e.target.value)}
                />
                <Input
                  placeholder="Change summary"
                  value={changeSummary}
                  onChange={(e) => setChangeSummary(e.target.value)}
                />
                <div className="flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowCreate(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleCreate}
                    disabled={createMutation.isPending || !promptTemplate.trim()}
                  >
                    {createMutation.isPending && (
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    )}
                    Create Draft
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Version list */}
      {isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-2">
          {versions?.map((v) => (
            <PromptVersionRow
              key={v.id}
              version={v}
              onPromote={() =>
                promoteMutation.mutate({ name: agentName, versionId: v.id })
              }
              onDelete={() =>
                deleteMutation.mutate({ name: agentName, versionId: v.id })
              }
              promotePending={promoteMutation.isPending}
              deletePending={deleteMutation.isPending}
            />
          ))}
          {versions?.length === 0 && (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No prompt versions yet. Create one or seed defaults.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── History Tab ─────────────────────────────────────────────────────────────

function HistoryTab({ agentName }: { agentName: string }) {
  const { data: configVersions } = useAgentConfigVersions(agentName);
  const { data: promptVersions } = useAgentPromptVersions(agentName);

  // Merge and sort by created_at descending
  const events: Array<{
    type: "config" | "prompt";
    version_number: number;
    status: string;
    summary: string | null;
    created_at: string;
    promoted_at: string | null;
    detail: string;
  }> = [];

  configVersions?.forEach((v) => {
    events.push({
      type: "config",
      version_number: v.version_number,
      status: v.status,
      summary: v.change_summary,
      created_at: v.created_at,
      promoted_at: v.promoted_at,
      detail: `${v.model_name ?? "—"} / temp ${v.temperature ?? "—"}`,
    });
  });

  promptVersions?.forEach((v) => {
    events.push({
      type: "prompt",
      version_number: v.version_number,
      status: v.status,
      summary: v.change_summary,
      created_at: v.created_at,
      promoted_at: v.promoted_at,
      detail: `${v.prompt_template.length} chars`,
    });
  });

  events.sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <div className="space-y-2">
      <h3 className="mb-3 text-sm font-medium">Combined History</h3>
      {events.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted-foreground">
          No version history yet.
        </p>
      ) : (
        <div className="relative space-y-0 pl-4">
          {/* Timeline line */}
          <div className="absolute bottom-0 left-[7px] top-0 w-px bg-border" />

          {events.map((event, idx) => (
            <div key={`${event.type}-${event.version_number}`} className="relative flex gap-3 pb-4">
              {/* Timeline dot */}
              <div
                className={cn(
                  "relative z-10 mt-1.5 h-2.5 w-2.5 rounded-full ring-2 ring-background",
                  event.type === "config"
                    ? "bg-blue-400"
                    : "bg-purple-400",
                )}
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium">
                    {event.type === "config" ? "Config" : "Prompt"} v
                    {event.version_number}
                  </span>
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-[9px] ring-1",
                      VERSION_STATUS_COLORS[event.status as VersionStatusValue],
                    )}
                  >
                    {event.status}
                  </Badge>
                  <span className="text-[10px] text-muted-foreground">
                    {new Date(event.created_at).toLocaleDateString()}{" "}
                    {new Date(event.created_at).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {event.detail}
                </p>
                {event.summary && (
                  <p className="mt-0.5 text-xs text-muted-foreground/70">
                    {event.summary}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Shared Version Row ──────────────────────────────────────────────────────

function VersionRow({
  version,
  type,
  onPromote,
  onDelete,
  promotePending,
  deletePending,
}: {
  version: ConfigVersion;
  type: "config";
  onPromote: () => void;
  onDelete: () => void;
  promotePending: boolean;
  deletePending: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border px-4 py-3",
        version.status === "draft" && "border-blue-500/30 bg-blue-500/5",
        version.status === "active" && "border-emerald-500/30 bg-emerald-500/5",
        version.status === "archived" && "border-border",
      )}
    >
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">v{version.version_number}</span>
          <Badge
            variant="outline"
            className={cn(
              "text-[10px] ring-1",
              VERSION_STATUS_COLORS[version.status as VersionStatusValue],
            )}
          >
            {version.status}
          </Badge>
        </div>
        <div className="mt-0.5 flex gap-3 text-xs text-muted-foreground">
          <span>
            <Cpu className="mr-1 inline h-3 w-3" />
            {version.model_name ?? "—"}
          </span>
          <span>
            <Thermometer className="mr-1 inline h-3 w-3" />
            {version.temperature ?? "—"}
          </span>
          {version.change_summary && (
            <span className="truncate">{version.change_summary}</span>
          )}
        </div>
      </div>
      <div className="flex gap-1">
        {version.status === "draft" && (
          <>
            <Button
              size="sm"
              variant="ghost"
              onClick={onPromote}
              disabled={promotePending}
              title="Promote to active"
            >
              <ArrowUpCircle className="h-4 w-4 text-emerald-400" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={onDelete}
              disabled={deletePending}
              title="Delete draft"
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </>
        )}
        {version.status === "active" && (
          <Check className="h-4 w-4 text-emerald-400" />
        )}
      </div>
    </div>
  );
}

function PromptVersionRow({
  version,
  onPromote,
  onDelete,
  promotePending,
  deletePending,
}: {
  version: PromptVersion;
  onPromote: () => void;
  onDelete: () => void;
  promotePending: boolean;
  deletePending: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-3",
        version.status === "draft" && "border-blue-500/30 bg-blue-500/5",
        version.status === "active" && "border-emerald-500/30 bg-emerald-500/5",
        version.status === "archived" && "border-border",
      )}
    >
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">
              v{version.version_number}
            </span>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] ring-1",
                VERSION_STATUS_COLORS[version.status as VersionStatusValue],
              )}
            >
              {version.status}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {version.prompt_template.length} chars
            </span>
          </div>
          {version.change_summary && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {version.change_summary}
            </p>
          )}
        </div>
        <div className="flex gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setExpanded(!expanded)}
            title="Toggle prompt text"
          >
            <FileText className="h-4 w-4" />
          </Button>
          {version.status === "draft" && (
            <>
              <Button
                size="sm"
                variant="ghost"
                onClick={onPromote}
                disabled={promotePending}
                title="Promote to active"
              >
                <ArrowUpCircle className="h-4 w-4 text-emerald-400" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={onDelete}
                disabled={deletePending}
                title="Delete draft"
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </>
          )}
          {version.status === "active" && (
            <Check className="h-4 w-4 text-emerald-400" />
          )}
        </div>
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <pre className="mt-3 max-h-[300px] overflow-auto rounded-md bg-background/50 p-3 font-mono text-xs leading-relaxed text-muted-foreground">
              {version.prompt_template}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
