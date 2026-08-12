export interface MeetingMessage {
  id: string;
  sender: string;
  senderType: "user" | "agent" | "system";
  content: string;
  createdAt?: string;
}

export interface AgentStream {
  agentId: number;
  agent: string;
  color?: string;
  content: string;
  thinking: boolean;
}

export interface WorkflowProgress {
  run_id: number;
  task_name?: string;
  status: "running" | "waiting" | "done" | "failed" | "cancelled" | string;
  label?: string;
  step?: number;
  total?: number;
}

export interface ApprovalRequest {
  output_id: number;
  run_id?: number;
  task_name?: string;
  approver?: string;
  note?: string;
  content?: string;
  images?: string[];
  deadline_note?: string;
  restored?: boolean;
  resolved?: "approved" | "rejected";
}

export interface ImageSourceRequest {
  run_id: number;
  node_id: string;
  task_name?: string;
  timeout_minutes?: number;
  assets?: Array<{ id: number; filename: string; url: string; note?: string }>;
  resolved?: "asset" | "generate";
}

export type MeetingServerMessage = Record<string, unknown> & { type: string };

export interface MeetingLiveState {
  messages: MeetingMessage[];
  streams: Record<string, AgentStream>;
  progress: Record<string, WorkflowProgress>;
  approvals: Record<string, ApprovalRequest>;
  imageSources: Record<string, ImageSourceRequest>;
  participantIds: number[] | null;
  endedDraft: string | null;
  error: string | null;
}

export const emptyMeetingLiveState: MeetingLiveState = {
  messages: [], streams: {}, progress: {}, approvals: {}, imageSources: {},
  participantIds: null, endedDraft: null, error: null,
};

function historyMessage(row: Record<string, unknown>, index: number): MeetingMessage {
  const senderType = row.sender_type === "user" ? "user" : row.sender_type === "system" ? "system" : "agent";
  return {
    id: String(row.id ?? `history-${index}`),
    sender: String(row.sender ?? (senderType === "user" ? "user" : "Hệ thống")),
    senderType,
    content: String(row.content ?? ""),
    createdAt: row.created_at ? String(row.created_at) : undefined,
  };
}

/** Pure protocol reducer: reconnect/replay is deterministic and duplicate cards are keyed. */
export function reduceMeetingMessage(state: MeetingLiveState, msg: MeetingServerMessage): MeetingLiveState {
  if (msg.type === "__approval_resolved") return resolveApproval(state, Number(msg.output_id), msg.resolution === "rejected" ? "rejected" : "approved");
  if (msg.type === "__image_source_resolved") return resolveImageSource(state, Number(msg.run_id), String(msg.node_id), msg.mode === "asset" ? "asset" : "generate");
  if (msg.type === "history") {
    const rows = Array.isArray(msg.messages) ? msg.messages as Record<string, unknown>[] : [];
    return { ...state, messages: rows.map(historyMessage), streams: {}, error: null };
  }
  if (msg.type === "user_message" || msg.type === "system_notice") {
    const isUser = msg.type === "user_message";
    const message: MeetingMessage = {
      id: `live-${Date.now()}-${state.messages.length}`,
      sender: isUser ? String(msg.sender ?? "user") : "Hệ thống",
      senderType: isUser ? "user" : "system",
      content: String(msg.content ?? ""),
    };
    return { ...state, messages: [...state.messages, message] };
  }
  if (msg.type === "agent_thinking") {
    const key = String(msg.agent_id ?? msg.agent ?? "agent");
    return { ...state, streams: { ...state.streams, [key]: {
      agentId: Number(msg.agent_id ?? -1), agent: String(msg.agent ?? "Agent"),
      color: msg.color ? String(msg.color) : undefined, content: "", thinking: true,
    } } };
  }
  if (msg.type === "agent_chunk") {
    const key = String(msg.agent_id ?? msg.agent ?? "agent");
    const previous = state.streams[key];
    return { ...state, streams: { ...state.streams, [key]: {
      agentId: Number(msg.agent_id ?? previous?.agentId ?? -1),
      agent: String(msg.agent ?? previous?.agent ?? "Agent"),
      color: msg.color ? String(msg.color) : previous?.color,
      content: `${previous?.content ?? ""}${String(msg.content ?? "")}`,
      thinking: false,
    } } };
  }
  if (msg.type === "agent_done" || msg.type === "agent_cancelled") {
    const key = String(msg.agent_id ?? msg.agent ?? "agent");
    const stream = state.streams[key];
    const streams = { ...state.streams }; delete streams[key];
    if (msg.type === "agent_cancelled" || !stream?.content) return { ...state, streams };
    return { ...state, streams, messages: [...state.messages, {
      id: `agent-${Date.now()}-${key}`, sender: stream.agent, senderType: "agent",
      content: stream.content,
    }] };
  }
  if (msg.type === "workflow_progress") {
    const item = msg as unknown as WorkflowProgress; const key = String(item.run_id);
    const progress = { ...state.progress };
    if (["done", "failed", "cancelled"].includes(item.status)) delete progress[key]; else progress[key] = item;
    return { ...state, progress };
  }
  if (msg.type === "approval_request") {
    const item = msg as unknown as ApprovalRequest;
    return { ...state, approvals: { ...state.approvals, [String(item.output_id)]: { ...state.approvals[String(item.output_id)], ...item } } };
  }
  if (msg.type === "image_source_request") {
    const item = msg as unknown as ImageSourceRequest; const key = `${item.run_id}:${item.node_id}`;
    return { ...state, imageSources: { ...state.imageSources, [key]: { ...state.imageSources[key], ...item } } };
  }
  if (msg.type === "image_source_chosen") {
    const key = `${msg.run_id}:${msg.node_id}`; const previous = state.imageSources[key];
    if (!previous) return state;
    return { ...state, imageSources: { ...state.imageSources, [key]: { ...previous, resolved: msg.mode === "asset" ? "asset" : "generate" } } };
  }
  if (msg.type === "participants_updated") {
    const raw = Array.isArray(msg.participants) ? msg.participants : [];
    return { ...state, participantIds: raw.map((item) => Number(typeof item === "object" && item ? (item as { id?: unknown }).id : item)).filter(Number.isFinite) };
  }
  if (msg.type === "meeting_ended") return { ...state, endedDraft: String(msg.draft_minutes ?? "") };
  if (msg.type === "error") return { ...state, error: String(msg.message ?? "WebSocket error") };
  return state;
}

export function resolveApproval(state: MeetingLiveState, outputId: number, resolution: "approved" | "rejected"): MeetingLiveState {
  const key = String(outputId); const previous = state.approvals[key];
  if (!previous) return state;
  return { ...state, approvals: { ...state.approvals, [key]: { ...previous, resolved: resolution } } };
}

export function resolveImageSource(state: MeetingLiveState, runId: number, nodeId: string, mode: "asset" | "generate"): MeetingLiveState {
  const key = `${runId}:${nodeId}`; const previous = state.imageSources[key];
  if (!previous) return state;
  return { ...state, imageSources: { ...state.imageSources, [key]: { ...previous, resolved: mode } } };
}
