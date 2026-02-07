import { Code } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { YamlViewer } from "@/components/ui/data-viewer";
import { useAutomationConfig } from "@/api/hooks";

export function AutomationYamlCard({
  entityId,
  domain,
}: {
  entityId: string;
  domain: string;
}) {
  // Extract the HA ID from entity_id (e.g., "automation.morning_lights" -> "morning_lights")
  const haId = entityId.replace(`${domain}.`, "");
  const { data, isLoading, error } = useAutomationConfig(haId);

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Code className="h-4 w-4" />
          {domain === "automation" ? "Automation" : "Script"} Configuration
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-32" />
        ) : error ? (
          <p className="text-xs text-muted-foreground">
            Configuration not available from Home Assistant
          </p>
        ) : data?.yaml ? (
          <YamlViewer content={data.yaml} collapsible maxHeight={500} />
        ) : (
          <p className="text-xs text-muted-foreground">No configuration data</p>
        )}
      </CardContent>
    </Card>
  );
}
