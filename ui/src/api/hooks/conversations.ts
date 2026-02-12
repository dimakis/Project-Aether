import { useQuery } from "@tanstack/react-query";
import { conversations } from "../client";
import { queryKeys } from "./queryKeys";

// ─── Conversations ──────────────────────────────────────────────────────────

export function useConversations() {
  return useQuery({
    queryKey: queryKeys.conversations.all,
    queryFn: () => conversations.list(),
  });
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: queryKeys.conversations.detail(id),
    queryFn: () => conversations.get(id),
    enabled: !!id,
  });
}
