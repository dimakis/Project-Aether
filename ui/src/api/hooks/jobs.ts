import { useQuery } from "@tanstack/react-query";
import { jobs } from "@/api/client/jobs";
import { queryKeys } from "./queryKeys";

export function useJobs(limit?: number, jobType?: string) {
  return useQuery({
    queryKey: [...queryKeys.jobs.all, limit, jobType],
    queryFn: () => jobs.list(limit, jobType),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.jobs.some((j) => j.status === "running")) return 5000;
      return 30_000;
    },
  });
}
