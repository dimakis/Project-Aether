import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  Loader2,
  Check,
  ArrowUpCircle,
  RotateCcw,
  Trash2,
  Cpu,
  Thermometer,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  useAgentConfigVersions,
  useModels,
  useCreateConfigVersion,
  usePromoteConfigVersion,
  useRollbackConfig,
  useDeleteConfigVersion,
} from "@/api/hooks";
import { ModelPicker } from "@/pages/chat/ModelPicker";
import type { ConfigVersion, VersionStatusValue } from "@/lib/types";
import { VERSION_STATUS_COLORS } from "./constants";

// ─── Config Tab ──────────────────────────────────────────────────────────────

export function ConfigTab({ agentName }: { agentName: string }) {
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

// ─── Version Row ─────────────────────────────────────────────────────────────

function VersionRow({
  version,
  onPromote,
  onDelete,
  promotePending,
  deletePending,
}: {
  version: ConfigVersion;
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
