import { request } from "./core";

export interface Job {
  job_id: string;
  job_type: "chat" | "optimization" | "analysis" | "discovery" | "schedule" | "webhook" | "evaluation" | "other";
  status: "running" | "completed" | "failed";
  title: string;
  started_at: number;
  duration_ms: number | null;
  conversation_id: string | null;
  run_name: string;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
}

export const jobs = {
  list: (limit?: number, jobType?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set("limit", String(limit));
    if (jobType) params.set("job_type", jobType);
    const qs = params.toString();
    return request<JobListResponse>(`/jobs${qs ? `?${qs}` : ""}`);
  },
};
