import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Model } from "@/lib/types";

interface ModelPickerProps {
  selectedModel: string;
  availableModels: Model[];
  onModelChange: (modelId: string) => void;
}

export function ModelPicker({
  selectedModel,
  availableModels,
  onModelChange,
}: ModelPickerProps) {
  const [showModelPicker, setShowModelPicker] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setShowModelPicker(!showModelPicker)}
        className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent"
      >
        <Sparkles className="h-3.5 w-3.5 text-primary" />
        {selectedModel}
        <ChevronDown className="h-3 w-3 opacity-60" />
      </button>
      <AnimatePresence>
        {showModelPicker && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 top-full z-50 mt-1 w-72 rounded-lg border border-border bg-popover p-1 shadow-lg"
          >
            {availableModels.map((model) => (
              <button
                key={model.id}
                onClick={() => {
                  onModelChange(model.id);
                  setShowModelPicker(false);
                }}
                className={cn(
                  "w-full rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-accent",
                  model.id === selectedModel && "bg-accent",
                )}
              >
                <div className="font-medium">{model.id}</div>
                <div className="text-xs text-muted-foreground">
                  {model.owned_by}
                </div>
              </button>
            ))}
            {availableModels.length === 0 && (
              <p className="px-3 py-2 text-sm text-muted-foreground">
                Loading models...
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
