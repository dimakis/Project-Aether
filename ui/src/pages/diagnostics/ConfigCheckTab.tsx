import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Shield,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useConfigCheck } from "@/api/hooks";

export function ConfigCheckTab() {
  const { data, isLoading, refetch, isFetching } = useConfigCheck();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Configuration Validation</h3>
          <p className="text-xs text-muted-foreground">
            Check your Home Assistant configuration for errors and warnings.
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          {isFetching ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Shield className="mr-1.5 h-3.5 w-3.5" />
          )}
          Run Check
        </Button>
      </div>

      {isLoading || isFetching ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : data ? (
        <div className="space-y-4">
          {/* Result card */}
          <Card>
            <CardContent className="flex items-center gap-4 p-6">
              <div
                className={cn(
                  "flex h-12 w-12 items-center justify-center rounded-xl",
                  data.valid ? "bg-success/10" : "bg-destructive/10",
                )}
              >
                {data.valid ? (
                  <CheckCircle2 className="h-6 w-6 text-success" />
                ) : (
                  <XCircle className="h-6 w-6 text-destructive" />
                )}
              </div>
              <div>
                <h2 className="text-lg font-semibold">
                  {data.valid
                    ? "Configuration Valid"
                    : "Configuration Issues Found"}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {data.errors.length} error{data.errors.length !== 1 ? "s" : ""}
                  , {data.warnings.length} warning
                  {data.warnings.length !== 1 ? "s" : ""}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Errors */}
          {data.errors.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-medium text-destructive">
                Errors
              </h4>
              <div className="space-y-1">
                {data.errors.map((err, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2"
                  >
                    <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" />
                    <span className="text-xs">{err}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {data.warnings.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-medium text-amber-400">
                Warnings
              </h4>
              <div className="space-y-1">
                {data.warnings.map((warn, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2"
                  >
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
                    <span className="text-xs">{warn}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <Shield className="mb-2 h-8 w-8 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              Click "Run Check" to validate your HA configuration.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
