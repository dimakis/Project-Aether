import { Circle } from "lucide-react";
import { cn } from "@/lib/utils";

export function StateIndicator({
  state,
  size = "sm",
}: {
  state: string | null;
  size?: "sm" | "lg";
}) {
  const isOn =
    state === "on" ||
    state === "home" ||
    state === "playing" ||
    state === "open";
  const isOff =
    state === "off" ||
    state === "not_home" ||
    state === "idle" ||
    state === "closed";
  const isUnavailable = state === "unavailable" || state === "unknown";

  const s = size === "lg" ? "h-3 w-3" : "h-2 w-2";

  return (
    <Circle
      className={cn(
        s,
        "shrink-0 fill-current",
        isOn && "text-success",
        isOff && "text-muted-foreground/40",
        isUnavailable && "text-destructive",
        !isOn && !isOff && !isUnavailable && "text-info",
      )}
    />
  );
}
