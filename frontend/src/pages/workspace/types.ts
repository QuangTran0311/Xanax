export interface Message {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
}

export interface TrainingSession {
  id: number;
  title: string;
  task_description: string;
  status: "in_progress" | "pass" | "fail";
  result_notes: string;
  agent_id: number | null;
  agent_name?: string | null;
  project_id: number | null;
  project_name?: string | null;
  closed: boolean | number;
  created_at: string;
  messages?: Message[];
}

export interface AgentOption { id: number; name: string; role?: string }
export interface ProjectOption { id: number; name: string }
export interface ToolOption { name: string; description?: string }

export type TrainingSocketMessage =
  | { type: "status"; status?: string }
  | { type: "chunk"; content: string }
  | { type: "tool_executed"; clean_text: string; results?: ToolResult[] }
  | { type: "done" }
  | { type: "notes_updated"; content: string }
  | { type: "failure_analysed"; content: string }
  | { type: "error"; message: string };

export interface ToolResult {
  action: string;
  ok: boolean;
  message?: string;
  error?: string;
}
