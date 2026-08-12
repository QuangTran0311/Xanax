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

const NODE_DEFAULTS: Record<GraphNodeType, { title: string; color: string; kind?: string }> = {
  trigger: { title: "Bắt đầu", color: "#22c55e", kind: "start" },
  agent: { title: "Nhân viên AI", color: "#3b82f6" },
  condition: { title: "Điều kiện", color: "#8b5cf6", kind: "branch" },
  workflow_call: { title: "Tác vụ", color: "#3b82f6" },
  tool_call: { title: "Gọi công cụ", color: "#8892a4" },
  set_data: { title: "Đặt / Sửa dữ liệu", color: "#f59e0b" },
  delay: { title: "Chờ", color: "#f59e0b" },
  stop_error: { title: "Dừng & Báo lỗi", color: "#ef4444" },
  approval_gate: { title: "Cổng duyệt", color: "#f59e0b" },
  noop: { title: "Không làm gì", color: "#8892a4" },
  end: { title: "Kết thúc", color: "#ef4444", kind: "end" },
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

/** UI projection that keeps a lossless copy of every source field. */
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
    title: String(node.title || data.label || data.agent_name || meta.title),
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
}

/** Recompute only the labels shown on canvas; graph data remains authoritative. */
export function refreshNodePresentation(node: EditorNode, context: EditorPresentationContext = {}): EditorNode {
  const type = inferNodeType(node);
  const data = node.data || {};
  const meta = NODE_DEFAULTS[type] || NODE_DEFAULTS.noop;
  let sub = String(data.instructions || data.message || "");
  if (type === "agent") {
    const agent = context.agents?.find((item) => String(item.id) === String(data.agent_id));
    const effectiveIds = (data.skill_ids as number[] | undefined)?.length ? data.skill_ids as number[] : agent?.skills || [];
    const names = effectiveIds.map((id) => context.skills?.find((skill) => String(skill.id) === String(id))?.name).filter(Boolean);
    sub = `${agent?.name || "Chưa chọn nhân viên AI"}${names.length ? ` · ${names.join(", ")}` : " · Không có kỹ năng"}`;
  } else if (type === "tool_call") sub = String(data.tool_name || "Chưa chọn công cụ");
  else if (type === "workflow_call") sub = context.workflows?.find((item) => String(item.id) === String(data.target_task_id))?.name || "Chưa chọn tác vụ";
  else if (type === "delay") sub = `${Number(data.seconds || 0)} giây`;
  else if (type === "approval_gate") sub = `Chờ ${String(data.approver || "CEO")} duyệt`;
  else if (type === "condition") sub = `${String(data.field || "last_output")} ${String(data.mode || "contains")} ${String(data.value || "")}`.trim();
  return {
    ...node,
    type,
    data,
    kind: meta.kind || type,
    color: node.color || meta.color,
    title: String(data.label || meta.title),
    sub,
  };
}

/**
 * Lossless inverse for loaded nodes. Presentation-only fields never leak into
 * graph_json; fields unknown to this frontend survive through `_source`.
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
    const label = edge.branch === "true" ? "Đúng" : edge.branch === "false" ? "Sai" : String(edge.label || "");
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

  const branch = edge[2] === "Đúng" ? "true" : edge[2] === "Sai" ? "false" : null;
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

/** Preserve the exact DB bytes when the editor made no structural change. */
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
