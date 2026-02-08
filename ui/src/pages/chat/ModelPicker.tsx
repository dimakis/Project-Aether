import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ModelInfo } from "@/lib/types";

interface ModelPickerProps {
  selectedModel: string;
  availableModels: ModelInfo[];
  onModelChange: (modelId: string) => void;
}

function formatCost(cost: number | null): string {
  if (cost == null) return "–";
  if (cost < 0.1) return `$${cost.toFixed(3)}`;
  if (cost < 1) return `$${cost.toFixed(2)}`;
  return `$${cost.toFixed(2)}`;
}

export function ModelPicker({
  selectedModel,
  availableModels,
  onModelChange,
}: ModelPickerProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0, width: 0 });

  // Compute position when opening
  useEffect(() => {
    if (!open || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    setPos({
      top: rect.bottom + 4,
      left: rect.left,
      width: Math.max(rect.width, 340),
    });
  }, [open]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (
        triggerRef.current?.contains(e.target as Node) ||
        menuRef.current?.contains(e.target as Node)
      )
        return;
      setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open]);

  const dropdown = (
    <AnimatePresence>
      {open && (
        <motion.div
          ref={menuRef}
          initial={{ opacity: 0, y: -4, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -4, scale: 0.97 }}
          transition={{ duration: 0.15 }}
          className="fixed z-[9999] max-h-80 overflow-y-auto rounded-lg border border-border bg-popover p-1 shadow-lg"
          style={{
            top: pos.top,
            left: pos.left,
            width: pos.width,
          }}
        >
          {availableModels.map((model) => {
            const hasPricing =
              model.input_cost_per_1m != null || model.output_cost_per_1m != null;
            return (
              <button
                key={model.id}
                onClick={() => {
                  onModelChange(model.id);
                  setOpen(false);
                }}
                className={cn(
                  "w-full rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-accent",
                  model.id === selectedModel && "bg-accent",
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{model.id}</span>
                  {hasPricing && (
                    <span className="text-[10px] text-muted-foreground/70">
                      {formatCost(model.input_cost_per_1m)} /{" "}
                      {formatCost(model.output_cost_per_1m)} per 1M
                    </span>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  {model.owned_by}
                </div>
              </button>
            );
          })}
          {availableModels.length === 0 && (
            <p className="px-3 py-2 text-sm text-muted-foreground">
              Loading models...
            </p>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent"
      >
        <Sparkles className="h-3.5 w-3.5 text-primary" />
        {selectedModel}
        <ChevronDown className="h-3 w-3 opacity-60" />
      </button>
      {createPortal(dropdown, document.body)}
    </div>
  );
}
