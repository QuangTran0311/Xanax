import type { GraphNodeType } from "./graphAdapter";

export interface WorkflowTask {
  id: number;
  name: string;
  description: string;
  kind: "company" | "automation";
  project_id: number | null;
  agents_json: string;
  graph_json: string;
  trigger_type: string;
  trigger_config_json: string;
  schedule_enabled: boolean | number;
  schedule_cron: string;
  status: "active" | "paused" | "draft" | "failed" | string;
  slug?: string;
  created_at?: string;
  updated_at?: string;
}

export interface WorkflowRun {
  id: number;
  task_id: number;
  task_name?: string;
  project_id?: number | null;
  status: string;
  triggered_by?: string;
  created_at?: string;
  started_at?: string;
  finished_at?: string;
  outputs?: WorkflowOutput[];
}

export interface WorkflowOutput {
  id: number;
  run_id: number;
  agent_id?: number | null;
  agent_name?: string;
  step_order?: number;
  output_content?: string;
  edited_content?: string | null;
  status?: string;
  pass_fail?: "pass" | "fail" | null;
  review_status?: string;
  notes?: string;
}

export interface AgentOption {
  id: number;
  name: string;
  role?: string;
  skills?: number[];
  model_pool_id?: number | null;
}

export interface SkillOption { id: number; name: string }
export interface ProjectOption { id: number; name: string }
export interface ToolOption {
  name: string;
  description?: string;
  parameters?: { properties?: Record<string, { type?: string; description?: string; default?: unknown }>; required?: string[] };
  inputSchema?: { properties?: Record<string, { type?: string; description?: string; default?: unknown }> };
  input_schema?: { properties?: Record<string, { type?: string; description?: string; default?: unknown }> };
}

export interface WorkflowAsset { id: number; filename: string; url: string; note?: string }

export type WorkflowMessageType =
  | "active_runs" | "agent_chunk" | "agent_done" | "agent_error" | "agent_image"
  | "agent_start" | "approval_rejected" | "approval_request" | "approval_resumed"
  | "attach_failed" | "attached" | "cancelling" | "condition_result" | "data_set"
  | "delay_done" | "delay_start" | "error" | "function" | "image_source_chosen"
  | "image_source_request" | "node_done" | "node_start" | "run_cancelled" | "run_done"
  | "run_error" | "run_failed" | "run_paused_for_approval"
  | "run_paused_for_image_source" | "run_started" | "tool_call_done"
  | "tool_call_error" | "tool_call_start" | "workflow_progress";

export interface WorkflowSocketMessage extends Record<string, unknown> {
  type: WorkflowMessageType;
  run_id?: number;
  node_id?: string;
  output_id?: number;
  content?: string;
  result?: unknown;
  agent_name?: string;
  tool_name?: string;
  task_name?: string;
  approver?: string;
  attempt?: number;
  mode?: "generate" | "asset";
  finished?: boolean;
  note?: string;
  images?: string[];
  assets?: WorkflowAsset[];
  timeout_minutes?: number;
  runs?: Array<{ run_id: number; task_id: number; task_name: string; finished: boolean }>;
}

export interface NodeMeta {
  type: GraphNodeType;
  title: string;
  description: string;
  color: string;
}
