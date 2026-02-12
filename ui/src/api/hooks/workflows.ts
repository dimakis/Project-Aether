import { useQuery } from "@tanstack/react-query";
import { workflows } from "@/api/client";
import { queryKeys } from "./queryKeys";

// ─── Workflow Preset Hooks ──────────────────────────────────────────────────

export function useWorkflowPresets() {
  return useQuery({
    queryKey: queryKeys.workflows.presets,
    queryFn: () => workflows.listPresets(),
    staleTime: 5 * 60 * 1000, // Presets rarely change, cache 5 min
  });
}
