import { BookOpen } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface EmptyStateProps {
  type: string;
}

export function EmptyState({ type }: EmptyStateProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center py-16">
        <BookOpen className="mb-3 h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">
          No {type} found. Sync the registry first.
        </p>
      </CardContent>
    </Card>
  );
}
