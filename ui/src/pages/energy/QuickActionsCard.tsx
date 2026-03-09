import { useNavigate } from "react-router-dom";
import { MessageSquare, Play, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useRunAnalysis } from "@/api/hooks";

export function QuickActionsCard() {
  const navigate = useNavigate();
  const costAnalysis = useRunAnalysis();

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start"
          onClick={() =>
            costAnalysis.mutate({
              analysis_type: "cost_optimization",
              time_range_hours: 168,
            })
          }
          disabled={costAnalysis.isPending}
        >
          <Play className="mr-2 h-3.5 w-3.5" />
          {costAnalysis.isPending ? "Running..." : "Run Cost Analysis (7d)"}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start"
          onClick={() =>
            costAnalysis.mutate({
              analysis_type: "energy_optimization",
              time_range_hours: 168,
            })
          }
          disabled={costAnalysis.isPending}
        >
          <RefreshCw className="mr-2 h-3.5 w-3.5" />
          Run Energy Analysis (7d)
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start"
          onClick={() => navigate("/chat")}
        >
          <MessageSquare className="mr-2 h-3.5 w-3.5" />
          Update Tariffs via Chat
        </Button>
      </CardContent>
    </Card>
  );
}
