import { ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export function StatCard({
  icon: Icon,
  label,
  value,
  loading,
  color,
  bgColor,
  onClick,
  detail,
}: {
  icon: typeof ArrowRight;
  label: string;
  value: number;
  loading: boolean;
  color: string;
  bgColor: string;
  onClick: () => void;
  detail?: string;
}) {
  return (
    <Card
      className="cursor-pointer transition-all hover:border-primary/30 hover:shadow-md"
      onClick={onClick}
    >
      <CardContent className="flex items-center gap-3 p-4">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg",
            bgColor,
          )}
        >
          <Icon className={cn("h-5 w-5", color)} />
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          {loading ? (
            <Skeleton className="mt-1 h-5 w-10" />
          ) : (
            <>
              <p className="text-lg font-bold">{value}</p>
              {detail && (
                <p className="text-[10px] text-muted-foreground">{detail}</p>
              )}
            </>
          )}
        </div>
        <ArrowRight className="ml-auto h-4 w-4 text-muted-foreground/30" />
      </CardContent>
    </Card>
  );
}
