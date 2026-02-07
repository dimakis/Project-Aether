import { useState } from "react";
import { Bot, Loader2, Sparkles, Workflow, Network, Settings2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAgents, useSeedAgents } from "@/api/hooks";
import { AgentCard } from "./AgentCard";
import { TeamArchitectureTab } from "./TeamArchitectureTab";

type PageView = "configuration" | "architecture";

// ─── Agents Page ─────────────────────────────────────────────────────────────

export function AgentsPage() {
  const { data, isLoading, error } = useAgents();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [view, setView] = useState<PageView>("configuration");
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
        <div className="flex items-center gap-2">
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
      </div>

      {/* View toggle */}
      <div className="flex gap-1 border-b border-border">
        {(
          [
            { key: "configuration" as const, label: "Configuration", icon: Settings2 },
            { key: "architecture" as const, label: "Team Architecture", icon: Network },
          ] as const
        ).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setView(key)}
            className={cn(
              "flex items-center gap-1.5 border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              view === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
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

      {/* Architecture View */}
      {view === "architecture" && !isLoading && agentsList.length > 0 && (
        <TeamArchitectureTab agents={agentsList} />
      )}

      {/* Configuration View */}
      {view === "configuration" && (
        <>
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
        </>
      )}
    </div>
  );
}
