import { BookOpen, RefreshCw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  type: string;
  onSync?: () => void;
  isSyncing?: boolean;
}

export function EmptyState({ type, onSync, isSyncing }: EmptyStateProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center py-16">
        <BookOpen className="mb-3 h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">
          No {type} found. Sync the registry first.
        </p>
        {onSync && (
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={onSync}
            disabled={isSyncing}
          >
            <RefreshCw
              className={`mr-2 h-3.5 w-3.5 ${isSyncing ? "animate-spin" : ""}`}
            />
            {isSyncing ? "Syncing..." : "Sync Now"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
