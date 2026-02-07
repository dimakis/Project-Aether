import { cn } from "@/lib/utils";

interface ConfidenceRingProps {
  value: number;
  size?: number;
}

export function ConfidenceRing({ value, size = 20 }: ConfidenceRingProps) {
  const radius = (size - 3) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - value);

  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        className="text-muted/50"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className={cn(
          value >= 0.8
            ? "text-green-400"
            : value >= 0.5
              ? "text-blue-400"
              : "text-orange-400",
        )}
      />
    </svg>
  );
}
