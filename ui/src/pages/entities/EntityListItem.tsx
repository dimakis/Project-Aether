import { memo } from "react";
import { motion } from "framer-motion";
import { MapPin, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Entity } from "@/lib/types";
import { DomainIcon } from "./DomainIcon";
import { StateIndicator } from "./StateIndicator";

interface EntityListItemProps {
  entity: Entity;
  isSelected: boolean;
  areaName: string;
  onSelect: () => void;
}

export const EntityListItem = memo(function EntityListItem({
  entity,
  isSelected,
  areaName,
  onSelect,
}: EntityListItemProps) {
  return (
    <motion.button
      layout
      onClick={onSelect}
      whileHover={{ x: 2 }}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors",
        isSelected
          ? "bg-primary/5 border border-primary/30"
          : "hover:bg-accent border border-transparent",
      )}
    >
      <DomainIcon domain={entity.domain} state={entity.state} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{entity.name}</p>
        <div className="flex items-center gap-1.5 truncate text-xs text-muted-foreground">
          <span className="truncate">{entity.entity_id}</span>
          {areaName && (
            <>
              <span className="text-muted-foreground/30">&middot;</span>
              <span className="flex items-center gap-0.5 truncate text-muted-foreground/70">
                <MapPin className="h-2.5 w-2.5 shrink-0" />
                {areaName}
              </span>
            </>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <StateIndicator state={entity.state} />
        <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
      </div>
    </motion.button>
  );
});
