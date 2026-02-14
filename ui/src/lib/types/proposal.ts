// ─── Proposals ───────────────────────────────────────────────────────────────

export type ProposalStatus =
  | "draft"
  | "proposed"
  | "approved"
  | "rejected"
  | "deployed"
  | "rolled_back"
  | "archived"
  | "failed";

export type ProposalTypeValue = "automation" | "entity_command" | "script" | "scene" | "dashboard";

export interface Proposal {
  id: string;
  proposal_type?: ProposalTypeValue;
  name: string;
  description?: string;
  status: ProposalStatus;
  conversation_id?: string;
  service_call?: {
    domain?: string;
    service?: string;
    entity_id?: string;
    data?: Record<string, unknown>;
    url_path?: string | null;
  };
  dashboard_config?: Record<string, unknown>;
  proposed_at?: string;
  approved_at?: string;
  approved_by?: string;
  deployed_at?: string;
  rolled_back_at?: string;
  rejection_reason?: string;
  ha_automation_id?: string;
  ha_disabled?: boolean;
  ha_error?: string;
  created_at: string;
  updated_at: string;
}

export interface ReviewNote {
  change: string;
  rationale: string;
  category: string;
}

export interface ProposalWithYAML extends Proposal {
  yaml_content?: string;
  // Review fields (Feature 28)
  original_yaml?: string;
  review_notes?: ReviewNote[];
  review_session_id?: string;
  parent_proposal_id?: string;
}

export interface ProposalList {
  items: Proposal[];
  total: number;
  limit: number;
  offset: number;
}

export interface DeploymentResponse {
  success: boolean;
  proposal_id: string;
  ha_automation_id?: string;
  method?: string;
  yaml_content?: string;
  instructions?: string;
  deployed_at?: string;
  error?: string;
}
