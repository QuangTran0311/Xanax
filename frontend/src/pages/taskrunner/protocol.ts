import type { WorkflowMessageType, WorkflowSocketMessage } from "./types";

/** Exhaustive list extracted from websocket_workflow.py, including compatibility aliases. */
export const WORKFLOW_MESSAGE_TYPES = [
  "active_runs", "agent_chunk", "agent_done", "agent_error", "agent_image",
  "agent_start", "approval_rejected", "approval_request", "approval_resumed",
  "attach_failed", "attached", "cancelling", "condition_result", "data_set",
  "delay_done", "delay_start", "error", "function", "image_source_chosen",
  "image_source_request", "node_done", "node_start", "run_cancelled", "run_done",
  "run_error", "run_failed", "run_paused_for_approval",
  "run_paused_for_image_source", "run_started", "tool_call_done",
  "tool_call_error", "tool_call_start", "workflow_progress",
] as const satisfies readonly WorkflowMessageType[];

export function isWorkflowMessage(value: unknown): value is WorkflowSocketMessage {
  if (!value || typeof value !== "object") return false;
  return WORKFLOW_MESSAGE_TYPES.includes((value as WorkflowSocketMessage).type);
}

export type NodeRunState = "running" | "done" | "error" | "paused";
export interface NodeRunStatus { state: NodeRunState; detail: string }

export interface WorkflowEventResult {
  nodeId?: string;
  nodeStatus?: NodeRunStatus;
  terminal?: "done" | "cancelled" | "error";
  approval?: WorkflowSocketMessage;
  imageSource?: WorkflowSocketMessage;
  clearApproval?: boolean;
  clearImageSource?: boolean;
  reset?: boolean;
  rememberRun?: number;
  forgetRun?: boolean;
  toast?: { text: string; kind: "success" | "error" | "info" };
}

/** One explicit branch for every server message: additions cannot disappear silently. */
export function reduceWorkflowEvent(message: WorkflowSocketMessage, activeNodeId?: string): WorkflowEventResult {
  const nodeId = message.node_id || activeNodeId;
  switch (message.type) {
    case "active_runs": return {};
    case "attached": return { reset: true };
    case "attach_failed": return { terminal: "error", forgetRun: true, toast: { text: "Không còn lần chạy để nối lại.", kind: "error" } };
    case "run_started": return { rememberRun: message.run_id };
    case "node_start":
    case "agent_start":
    case "tool_call_start":
    case "delay_start":
      return { nodeId: message.node_id, nodeStatus: { state: "running", detail: String(message.agent_name || message.tool_name || "Đang chạy") } };
    case "agent_chunk":
    case "workflow_progress":
      return { nodeId, nodeStatus: { state: "running", detail: String(message.content || "Đang chạy") } };
    case "agent_image":
    case "function":
      return { nodeId, nodeStatus: { state: "running", detail: String(message.content || message.result || "Đã nhận kết quả") } };
    case "agent_done":
    case "tool_call_done":
    case "data_set":
    case "delay_done":
    case "condition_result":
    case "node_done":
      return { nodeId, nodeStatus: { state: "done", detail: String(message.result ?? "Đã hoàn thành") } };
    case "approval_resumed":
      return { nodeId, nodeStatus: { state: "done", detail: "Đã duyệt" }, clearApproval: true };
    case "run_paused_for_approval":
    case "approval_request":
      return { nodeId: message.node_id, nodeStatus: { state: "paused", detail: `Đang chờ ${String(message.approver || "CEO")} duyệt` }, approval: message };
    case "run_paused_for_image_source":
    case "image_source_request":
      return { nodeId: message.node_id, nodeStatus: { state: "paused", detail: "Đang hỏi nguồn ảnh" }, imageSource: message };
    case "image_source_chosen":
      return { nodeId: message.node_id, nodeStatus: { state: "running", detail: message.mode === "asset" ? "Dùng ảnh có sẵn" : "Nhân viên tự vẽ ảnh" }, clearImageSource: true };
    case "approval_rejected":
      return { clearApproval: true, toast: { text: `Đã từ chối — đang chạy lại bước trước (lần ${message.attempt || 1}).`, kind: "info" } };
    case "agent_error":
    case "tool_call_error":
      return { nodeId, nodeStatus: { state: "error", detail: String(message.content || "Thất bại") } };
    case "run_done": return { terminal: "done", forgetRun: true, toast: { text: "Quy trình đã hoàn thành.", kind: "success" } };
    case "run_cancelled": return { terminal: "cancelled", forgetRun: true, toast: { text: "Đã huỷ lần chạy.", kind: "info" } };
    case "run_error":
      return { terminal: "error", forgetRun: true, toast: { text: String(message.content || "Quy trình thất bại."), kind: "error" } };
    case "run_failed":
      return { terminal: "error", forgetRun: true, nodeId: message.node_id, nodeStatus: message.node_id ? { state: "error", detail: String(message.content || "Thất bại") } : undefined, toast: { text: String(message.content || "Quy trình thất bại."), kind: "error" } };
    case "cancelling": return { toast: { text: "Đang huỷ lần chạy...", kind: "info" } };
    case "error": return { toast: { text: String(message.content || "Lỗi WebSocket."), kind: "error" } };
  }
}
