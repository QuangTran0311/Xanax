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

export type NotificationSeverity = "info" | "warning" | "error";
export type NotificationStatus = "unread" | "read" | "resolved";

export interface NotificationRecord {
  id: number;
  kind: string;
  severity: NotificationSeverity;
  title: string;
  body: string;
  payload: Record<string, unknown>;
  link: string;
  source_type: string;
  source_id: string;
  status: NotificationStatus;
  created_at: string;
  read_at?: string | null;
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

export type ProjectSubtab = "overview" | "runs" | "review" | "kanban" | "work" | "knowledge" | "history";

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
  base_url?: string;
  cli_config_dir?: string;
  cli_configured?: boolean;
  category?: string;
  max_requests_per_day?: number;
  max_tokens_per_day?: number;
  price_input_per_1m?: number;
  price_cache_per_1m?: number;
  price_output_per_1m?: number;
  currency?: string;
  usage_today?: {
    request_count?: number;
    tokens_input?: number;
    tokens_cache?: number;
    tokens_output?: number;
  };
}

export type ToastKind = "success" | "error" | "info";

export interface AssetFile {
  name: string;
  size_bytes?: number;
  mime_type?: string;
  note?: string;
  download_url: string;
  preview_url?: string;
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
