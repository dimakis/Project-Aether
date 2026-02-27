import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { evaluations } from "@/api/client/evaluations";
import { queryKeys } from "./queryKeys";

export function useEvaluationSummary() {
  return useQuery({
    queryKey: queryKeys.evaluations.summary,
    queryFn: () => evaluations.summary(),
  });
}

export function useScorers() {
  return useQuery({
    queryKey: queryKeys.evaluations.scorers,
    queryFn: () => evaluations.scorers(),
  });
}

export function useRunEvaluation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (maxTraces?: number) => evaluations.run(maxTraces),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.evaluations.all });
    },
  });
}
