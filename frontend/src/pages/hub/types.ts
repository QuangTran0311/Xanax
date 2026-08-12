export interface HubRecord {
  id: number;
  name?: string;
  title?: string;
  description?: string;
  status?: string;
  enabled?: boolean | number;
  created_at?: string;
  [key: string]: unknown;
}

export interface AgentRecord extends HubRecord {
  role?: string;
  avatar_color?: string;
  avatar_icon?: string;
  skills?: number[];
  model_pool_ids?: number[];
  skill_tools?: Record<string, string[]>;
  department_id?: number | null;
}

export interface SkillRecord extends HubRecord {
  type?: "builtin" | "api" | "mcp" | string;
  config?: Record<string, unknown>;
}

export interface ProjectRecord extends HubRecord {
  description?: string;
}

export interface MeetingRecord extends HubRecord {
  topic?: string;
  participants?: number[];
  project_id?: number | null;
  proposed_items?: unknown[];
  draft_minutes?: string;
  decision_text?: string;
  decided_at?: string;
  ended_at?: string;
  pending_approvals?: number;
}

export interface ModelRecord extends HubRecord {
  provider?: string;
  api_style?: string;
  model_id?: string;
  category?: string;
  usage_today?: Record<string, number>;
}

export type ToastKind = "success" | "error" | "info";

export interface AssetFile {
  name: string;
  size_bytes?: number;
  mime_type?: string;
  note?: string;
  download_url: string;
}

export interface AssetRecord {
  id: string;
  source: "upload" | "workflow" | "benchmark" | string;
  name: string;
  label?: string;
  created_at?: string;
  deletable?: boolean;
  files: AssetFile[];
}

export interface CostRow {
  bucket: string;
  bucket_from: string;
  bucket_to: string;
  name: string;
  currency: string;
  request_count: number;
  tokens_input: number;
  tokens_cache: number;
  tokens_output: number;
  estimated_cost: number;
}

export interface CostReport {
  period: "day" | "week" | "month";
  date_from: string;
  date_to: string;
  rows: CostRow[];
  totals: Record<string, number>;
}
