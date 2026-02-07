import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { proposals, insights } from "../client";
import { queryKeys } from "./queryKeys";

// ─── Proposals ──────────────────────────────────────────────────────────────

export function useProposals(status?: string) {
  return useQuery({
    queryKey: [...queryKeys.proposals, status],
    queryFn: () => proposals.list(status),
  });
}

export function usePendingProposals() {
  return useQuery({
    queryKey: queryKeys.proposalsPending,
    queryFn: () => proposals.pending(),
    refetchInterval: 30_000, // Poll every 30s for pending approvals
  });
}

export function useProposal(id: string) {
  return useQuery({
    queryKey: queryKeys.proposal(id),
    queryFn: () => proposals.get(id),
    enabled: !!id,
  });
}

export function useApproveProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => proposals.approve(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
      qc.invalidateQueries({ queryKey: queryKeys.proposalsPending });
    },
  });
}

export function useRejectProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      proposals.reject(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
      qc.invalidateQueries({ queryKey: queryKeys.proposalsPending });
    },
  });
}

export function useDeployProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => proposals.deploy(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
      qc.invalidateQueries({ queryKey: queryKeys.proposalsPending });
      qc.invalidateQueries({ queryKey: queryKeys.proposal(id) });
    },
  });
}

export function useRollbackProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => proposals.rollback(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
      qc.invalidateQueries({ queryKey: queryKeys.proposalsPending });
      qc.invalidateQueries({ queryKey: queryKeys.proposal(id) });
    },
  });
}

export function useDeleteProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => proposals.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
      qc.invalidateQueries({ queryKey: queryKeys.proposalsPending });
    },
  });
}

export function useCreateProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      name: string;
      trigger?: unknown;
      actions?: unknown;
      description?: string;
      conditions?: unknown;
      mode?: string;
      proposal_type?: string;
      service_call?: Record<string, unknown>;
    }) => proposals.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.proposals });
    },
  });
}

// ─── Insights ───────────────────────────────────────────────────────────────

export function useInsights(type?: string, status?: string) {
  return useQuery({
    queryKey: [...queryKeys.insights, type, status],
    queryFn: () => insights.list(type, status),
  });
}

export function useInsightsSummary() {
  return useQuery({
    queryKey: queryKeys.insightsSummary,
    queryFn: () => insights.summary(),
  });
}

export function useInsight(id: string) {
  return useQuery({
    queryKey: queryKeys.insight(id),
    queryFn: () => insights.get(id),
    enabled: !!id,
  });
}

export function useReviewInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => insights.review(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.insights });
      qc.invalidateQueries({ queryKey: queryKeys.insightsSummary });
    },
  });
}

export function useDismissInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      insights.dismiss(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.insights });
      qc.invalidateQueries({ queryKey: queryKeys.insightsSummary });
    },
  });
}

export function useDeleteInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => insights.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.insights });
      qc.invalidateQueries({ queryKey: queryKeys.insightsSummary });
    },
  });
}

export function useRunAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      type,
      hours,
    }: {
      type?: string;
      hours?: number;
    } = {}) => insights.analyze(type, hours),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.insights });
      qc.invalidateQueries({ queryKey: queryKeys.insightsSummary });
    },
  });
}
