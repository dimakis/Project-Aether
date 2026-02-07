import { Cpu } from "lucide-react";
import { cn } from "@/lib/utils";
import { DOMAIN_ICONS } from "./constants";

export function DomainIcon({
  domain,
  state,
  size = "sm",
}: {
  domain: string;
  state: string | null;
  size?: "sm" | "lg";
}) {
  const IconComponent = DOMAIN_ICONS[domain] ?? Cpu;
  const isOn =
    state === "on" ||
    state === "home" ||
    state === "playing" ||
    state === "open";

  const sizeClasses = size === "lg" ? "h-10 w-10" : "h-8 w-8";
  const iconSize = size === "lg" ? "h-5 w-5" : "h-4 w-4";

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-lg",
        sizeClasses,
        isOn
          ? "bg-primary/10 text-primary"
          : "bg-muted text-muted-foreground",
      )}
    >
      <IconComponent className={iconSize} />
    </div>
  );
}
