// ─── Traces (Feature 11) ─────────────────────────────────────────────────────

export interface SpanNode {
  span_id: string;
  name: string;
  agent: string;
  type: string;
  start_ms: number;
  end_ms: number;
  duration_ms: number;
  status: string;
  attributes: Record<string, unknown>;
  children: SpanNode[];
}

export interface TraceResponse {
  trace_id: string;
  status: string;
  duration_ms: number;
  started_at: string | null;
  root_span: SpanNode | null;
  agents_involved: string[];
  span_count: number;
}
