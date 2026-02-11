import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, FlaskConical, Pencil, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ──────────────────────────────────────────────────────────────────

export type EntityAction = "improve" | "deep_review" | "edit_yaml" | "chat";

/** Callback type used by tab components to report entity actions to the registry page. */
export type OnEntityAction = (
  entityId: string,
  entityType: "automation" | "script" | "scene",
  label: string,
  configYaml: string | undefined,
  action: EntityAction,
  editedYaml?: string,
) => void;

export interface EntityActionMenuProps {
  /** Entity ID, e.g. "automation.kitchen_lights" */
  entityId: string;
  /** Domain type */
  entityType: "automation" | "script" | "scene";
  /** Friendly display name */
  entityLabel: string;
  /** Called when the user picks an action */
  onAction: (action: EntityAction) => void;
}

// ─── Menu item config ───────────────────────────────────────────────────────

interface MenuItem {
  action: EntityAction;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const MENU_ITEMS: MenuItem[] = [
  {
    action: "improve",
    label: "Improve",
    icon: Sparkles,
    description: "Architect suggests improvements",
  },
  {
    action: "deep_review",
    label: "Deep Review",
    icon: FlaskConical,
    description: "Architect + DS team analysis",
  },
  {
    action: "edit_yaml",
    label: "Edit YAML",
    icon: Pencil,
    description: "Edit config and submit for review",
  },
  {
    action: "chat",
    label: "Chat about this",
    icon: MessageSquare,
    description: "Open a conversation with context",
  },
];

// ─── Component ──────────────────────────────────────────────────────────────

export function EntityActionMenu({
  onAction,
}: EntityActionMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  const handleClickOutside = useCallback(
    (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open, handleClickOutside]);

  const handleSelect = (action: EntityAction) => {
    setOpen(false);
    onAction(action);
  };

  return (
    <div ref={menuRef} className="relative inline-block">
      {/* Trigger button */}
      <button
        aria-label="Actions"
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5",
          "text-xs font-medium text-muted-foreground transition-colors",
          "hover:border-primary/30 hover:bg-accent hover:text-foreground",
          open && "border-primary/30 bg-accent text-foreground",
        )}
      >
        <Sparkles className="h-3.5 w-3.5" />
        Actions
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className={cn(
              "absolute right-0 z-50 mt-1.5 w-64",
              "rounded-xl border border-border bg-card shadow-lg",
              "overflow-hidden",
            )}
          >
            <div className="p-1">
              {MENU_ITEMS.map((item) => (
                <button
                  key={item.action}
                  onClick={() => handleSelect(item.action)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2.5",
                    "text-left text-xs transition-colors",
                    "hover:bg-accent",
                  )}
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted">
                    <item.icon className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="font-medium text-foreground">{item.label}</p>
                    <p className="text-[10px] text-muted-foreground">
                      {item.description}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
