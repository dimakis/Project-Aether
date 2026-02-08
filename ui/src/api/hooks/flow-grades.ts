import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { flowGrades } from "../client";
import type { FlowGradePayload } from "../client";

export function useFlowGrades(conversationId: string | null) {
  return useQuery({
    queryKey: ["flow-grades", conversationId],
    queryFn: () => flowGrades.get(conversationId!),
    enabled: !!conversationId,
  });
}

export function useSubmitFlowGrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: FlowGradePayload) => flowGrades.submit(data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: ["flow-grades", vars.conversation_id],
      });
    },
  });
}

export function useDeleteFlowGrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (gradeId: string) => flowGrades.delete(gradeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["flow-grades"] });
    },
  });
}
