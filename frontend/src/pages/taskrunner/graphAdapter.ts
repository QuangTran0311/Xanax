import { taskrunnerText, type TaskrunnerTranslator } from "../../i18n/taskrunner";

export type GraphNodeType =
  | "trigger"
  | "agent"
  | "condition"
  | "workflow_call"
  | "tool_call"
  | "set_data"
  | "delay"
  | "stop_error"
  | "approval_gate"
  | "noop"
  | "end";

export interface GraphNode extends Record<string, unknown> {
  id: string;
  type?: GraphNodeType;
  kind?: string;
  x?: number | string;
  y?: number | string;
  data?: Record<string, unknown>;
}

export interface WorkflowGraph extends Record<string, unknown> {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type GraphEdge = Record<string, unknown> | unknown[];

export interface EditorNode extends Record<string, unknown> {
  id: string;
  type: GraphNodeType;
  data: Record<string, unknown>;
  x: number;
  y: number;
  title: string;
  sub: string;
  kind?: string;
  _source?: GraphNode;
}

export type EditorEdge = [string, string, string, string] & { _source?: GraphEdge };

// Chỉ giữ metadata trung tính với ngôn ngữ tại tầng chuyển đổi dữ liệu.
const NODE_DEFAULTS: Record<GraphNodeType, { color: string; kind?: string }> = {
  trigger: { color: "#22c55e", kind: "start" },
  agent: { color: "#3b82f6" },
  condition: { color: "#8b5cf6", kind: "branch" },
  workflow_call: { color: "#3b82f6" },
  tool_call: { color: "#8892a4" },
  set_data: { color: "#f59e0b" },
  delay: { color: "#f59e0b" },
  stop_error: { color: "#ef4444" },
  approval_gate: { color: "#f59e0b" },
  noop: { color: "#8892a4" },
  end: { color: "#ef4444", kind: "end" },
};

function clone<T>(value: T): T {
  return structuredClone(value);
}

function hasOwn(value: object, key: PropertyKey): boolean {
  return Object.prototype.hasOwnProperty.call(value, key);
}

export function inferNodeType(node: GraphNode | EditorNode): GraphNodeType {
  if (node.type && node.type in NODE_DEFAULTS) return node.type as GraphNodeType;
  if (node.kind === "start") return "trigger";
  if (node.kind === "end") return "end";
  if (node.kind === "branch") return "condition";
  return "agent";
}

/** Chiếu dữ liệu sang UI và giữ bản sao không mất mát của mọi trường nguồn. */
export function graphNodeToEditor(node: GraphNode, index = 0): EditorNode {
  const source = clone(node);
  const type = inferNodeType(node);
  const data = node.data && typeof node.data === "object" && !Array.isArray(node.data)
    ? clone(node.data)
    : {};
  const meta = NODE_DEFAULTS[type];
  return {
    ...clone(node),
    id: String(node.id),
    type,
    data,
    x: Number.isFinite(Number(node.x)) ? Number(node.x) : 60 + index * 230,
    y: Number.isFinite(Number(node.y)) ? Number(node.y) : 80,
    title: String(node.title || data.label || data.agent_name || ""),
    sub: String(node.sub || data.instructions || data.tool_name || ""),
    color: node.color || meta.color,
    kind: String(node.kind || meta.kind || type),
    _source: source,
  };
}

export interface EditorPresentationContext {
  agents?: Array<{ id: number; name: string; skills?: number[] }>;
  skills?: Array<{ id: number; name: string }>;
  workflows?: Array<{ id: number; name: string }>;
  text?: TaskrunnerTranslator;
}

/** Chỉ tính lại chữ trên canvas; dữ liệu graph vẫn là nguồn chính thức. */
export function refreshNodePresentation(node: EditorNode, context: EditorPresentationContext = {}): EditorNode {
  const type = inferNodeType(node);
  const data = node.data || {};
  const meta = NODE_DEFAULTS[type] || NODE_DEFAULTS.noop;
  const text = context.text ?? ((key, ...args) => taskrunnerText("vi", key, ...args));
  const sourceTitle = node._source?.title ? String(node._source.title) : "";
  const sourceSub = node._source?.sub ? String(node._source.sub) : "";
  let sub = String(data.instructions || data.message || sourceSub || "");
  if (type === "agent") {
    const agent = context.agents?.find((item) => String(item.id) === String(data.agent_id));
    const effectiveIds = (data.skill_ids as number[] | undefined)?.length ? data.skill_ids as number[] : agent?.skills || [];
    const names = effectiveIds.map((id) => context.skills?.find((skill) => String(skill.id) === String(id))?.name).filter(Boolean);
    sub = `${agent?.name || text("node.presentation.no_agent")}${names.length ? ` · ${names.join(", ")}` : ` · ${text("node.presentation.no_skills")}`}`;
  } else if (type === "tool_call") sub = String(data.tool_name || text("node.presentation.no_tool"));
  else if (type === "workflow_call") sub = context.workflows?.find((item) => String(item.id) === String(data.target_task_id))?.name || text("node.presentation.no_workflow");
  else if (type === "delay") sub = text("node.presentation.seconds", Number(data.seconds || 0));
  else if (type === "approval_gate") sub = text("node.presentation.approval", String(data.approver || "CEO"));
  else if (type === "condition") sub = `${String(data.field || "last_output")} ${String(data.mode || "contains")} ${String(data.value || "")}`.trim();
  return {
    ...node,
    type,
    data,
    kind: meta.kind || type,
    color: node.color || meta.color,
    // `sourceTitle` bảo toàn graph_json v1; nhãn mặc định được tra ở component vẽ node.
    title: String(data.label || sourceTitle || node.title || data.agent_name || ""),
    sub,
  };
}

/**
 * Phép đảo không mất mát cho node đã tải. Trường chỉ dùng để trình bày không lọt
 * vào graph_json; các trường frontend chưa biết vẫn được giữ qua `_source`.
 */
export function editorNodeToGraph(node: EditorNode): GraphNode {
  const source = node._source ? clone(node._source) : null;
  if (!source) {
    return {
      id: node.id,
      type: inferNodeType(node),
      x: Math.round(node.x || 0),
      y: Math.round(node.y || 0),
      data: clone(node.data || {}),
    };
  }

  const result = source;
  result.id = node.id;
  const originalType = inferNodeType(source);
  const nextType = inferNodeType(node);
  if (hasOwn(source, "type") || originalType !== nextType) result.type = nextType;

  const originalX = Number.isFinite(Number(source.x)) ? Number(source.x) : node.x;
  const originalY = Number.isFinite(Number(source.y)) ? Number(source.y) : node.y;
  if (node.x !== originalX || hasOwn(source, "x")) {
    result.x = node.x === originalX ? source.x : Math.round(node.x || 0);
  }
  if (node.y !== originalY || hasOwn(source, "y")) {
    result.y = node.y === originalY ? source.y : Math.round(node.y || 0);
  }
  if (hasOwn(source, "data") || Object.keys(node.data || {}).length) result.data = clone(node.data || {});
  return result;
}

export function graphEdgeToEditor(edge: GraphEdge): EditorEdge {
  let editor: EditorEdge;
  if (Array.isArray(edge)) {
    editor = [String(edge[0] ?? ""), String(edge[1] ?? ""), String(edge[2] ?? ""), String(edge[3] ?? "")] as EditorEdge;
  } else {
    const label = edge.branch === "true" ? "true" : edge.branch === "false" ? "false" : String(edge.label || "");
    editor = [String(edge.from || ""), String(edge.to || ""), label, String(edge.color || "")] as EditorEdge;
  }
  Object.defineProperty(editor, "_source", { value: clone(edge), writable: true });
  return editor;
}

export function editorEdgeToGraph(edge: EditorEdge): GraphEdge {
  const source = edge._source ? clone(edge._source) : null;
  if (Array.isArray(source)) {
    const result = source;
    result[0] = edge[0];
    result[1] = edge[1];
    if (result.length > 2 || edge[2]) result[2] = edge[2];
    if (result.length > 3 || edge[3]) result[3] = edge[3];
    return result;
  }

  const normalizedLabel = edge[2].toLocaleLowerCase("en");
  const branch = ["true", "đúng"].includes(normalizedLabel) ? "true" : ["false", "sai"].includes(normalizedLabel) ? "false" : null;
  if (source) {
    source.from = edge[0];
    source.to = edge[1];
    if (hasOwn(source, "branch") || branch !== null) source.branch = branch;
    if (hasOwn(source, "label") && branch === null) source.label = edge[2];
    if (hasOwn(source, "color") || edge[3]) source.color = edge[3];
    return source;
  }
  return { from: edge[0], to: edge[1], branch, ...(edge[3] ? { color: edge[3] } : {}) };
}

export function graphToEditor(graph: WorkflowGraph): { nodes: EditorNode[]; edges: EditorEdge[] } {
  return {
    nodes: (graph.nodes || []).map(graphNodeToEditor),
    edges: (graph.edges || []).map(graphEdgeToEditor),
  };
}

export function editorToGraph(nodes: EditorNode[], edges: EditorEdge[], source?: WorkflowGraph): WorkflowGraph {
  return {
    ...(source ? clone(source) : {}),
    nodes: nodes.map(editorNodeToGraph),
    edges: edges.map(editorEdgeToGraph),
  };
}

export function parseWorkflowGraph(raw: string): WorkflowGraph {
  const parsed = JSON.parse(raw) as WorkflowGraph;
  return { ...parsed, nodes: parsed.nodes || [], edges: parsed.edges || [] };
}

function structurallyEqual(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

/** Giữ nguyên từng byte trong DB khi trình sửa không tạo thay đổi cấu trúc. */
export function serializeWorkflowGraph(originalRaw: string, graph: WorkflowGraph): string {
  if (originalRaw.trim()) {
    const original = parseWorkflowGraph(originalRaw);
    if (structurallyEqual(original, graph)) return originalRaw;
  }
  return JSON.stringify(graph);
}

export function createEmptyGraph(triggerType = "manual"): WorkflowGraph {
  return {
    nodes: [{ id: "n1", type: "trigger", x: 60, y: 40, data: { trigger_type: triggerType } }],
    edges: [],
  };
}
