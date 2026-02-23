import { motion, AnimatePresence } from "framer-motion";
import { Plus, Loader2, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toggleActivityPanel } from "@/lib/agent-activity-store";
import { ModelPicker } from "./ModelPicker";
import {
  WorkflowPresetSelector,
  type WorkflowSelection,
} from "./WorkflowPresetSelector";
import type { ModelInfo } from "@/lib/types";

export interface ChatHeaderProps {
  selectedModel: string;
  availableModels: ModelInfo[];
  onModelChange: (model: string) => void;
  workflowSelection: WorkflowSelection;
  onWorkflowSelectionChange: (selection: WorkflowSelection) => void;
  isStreaming: boolean;
  statusMessage: string;
  elapsed: number;
  activityPanelOpen: boolean;
  onNewChat: () => void;
}

export function ChatHeader({
  selectedModel,
  availableModels,
  onModelChange,
  workflowSelection,
  onWorkflowSelectionChange,
  isStreaming,
  statusMessage,
  elapsed,
  activityPanelOpen,
  onNewChat,
}: ChatHeaderProps) {
  return (
    <div className="flex h-14 items-center justify-between border-b border-border px-4">
      <div className="flex items-center gap-2">
        <ModelPicker
          selectedModel={selectedModel}
          availableModels={availableModels}
          onModelChange={onModelChange}
        />
        <WorkflowPresetSelector
          selection={workflowSelection}
          onSelectionChange={onWorkflowSelectionChange}
        />
      </div>

      <div className="flex items-center gap-2">
        <AnimatePresence>
          {isStreaming && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              className="flex items-center gap-1.5 text-xs text-muted-foreground"
            >
              <Loader2 className="h-3 w-3 animate-spin text-primary" />
              {statusMessage ? (
                <span className="text-primary/80">{statusMessage}</span>
              ) : (
                <span>{selectedModel}</span>
              )}
              <span className="text-muted-foreground/50">|</span>
              <span className="tabular-nums">{elapsed}s</span>
            </motion.div>
          )}
        </AnimatePresence>
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleActivityPanel}
          className={cn(activityPanelOpen && "bg-primary/10 text-primary")}
          title="Toggle agent activity panel"
        >
          <Activity className="mr-1 h-3 w-3" />
          Activity
        </Button>
        <Button variant="ghost" size="sm" onClick={onNewChat}>
          <Plus className="mr-1 h-3 w-3" />
          New Chat
        </Button>
      </div>
    </div>
  );
}
