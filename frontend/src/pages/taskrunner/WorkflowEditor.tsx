import { useCallback, useEffect, useRef, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeProps,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { ImageLightbox, type LightboxImage } from "../../components/Markdown";
import { Tooltip } from "../../components/Tooltip";
import { useTaskrunnerText, type TaskrunnerMessageKey, type TaskrunnerTranslator } from "../../i18n/taskrunner";
import { useTooltipText } from "../../i18n/tooltips";
import { useWebSocket } from "../../ws/useWebSocket";
import type { ProjectSubtab } from "../hub/types";
import { Modal } from "./Modal";
import { SchedulePicker } from "./SchedulePicker";
import {
  createEmptyGraph,
  editorToGraph,
  graphToEditor,
  inferNodeType,
  parseWorkflowGraph,
  refreshNodePresentation,
  serializeWorkflowGraph,
  type EditorEdge,
  type EditorNode,
  type GraphNodeType,
  type WorkflowGraph,
} from "./graphAdapter";
import { reduceWorkflowEvent, type NodeRunStatus } from "./protocol";
import type {
  AgentOption,
  ProjectOption,
  SkillOption,
  ToolOption,
  WorkflowSocketMessage,
  WorkflowTask,
} from "./types";
import { workflowApi } from "./workflowApi";
import styles from "./TaskrunnerPage.module.css";

const c = (name: string) => styles[name] ?? name;

const NODE_META: Record<GraphNodeType, { titleKey: TaskrunnerMessageKey; descriptionKey: TaskrunnerMessageKey; color: string; icon: keyof typeof ICON_FOR_TYPE }> = {
  trigger: { titleKey: "node.trigger.title", descriptionKey: "node.trigger.description", color: "#22c55e", icon: "trigger" },
  agent: { titleKey: "node.agent.title", descriptionKey: "node.agent.description", color: "#3b82f6", icon: "agent" },
  condition: { titleKey: "node.condition.title", descriptionKey: "node.condition.description", color: "#8b5cf6", icon: "condition" },
  workflow_call: { titleKey: "node.workflow_call.title", descriptionKey: "node.workflow_call.description", color: "#3b82f6", icon: "workflow_call" },
  tool_call: { titleKey: "node.tool_call.title", descriptionKey: "node.tool_call.description", color: "#8892a4", icon: "tool_call" },
  set_data: { titleKey: "node.set_data.title", descriptionKey: "node.set_data.description", color: "#f59e0b", icon: "set_data" },
  delay: { titleKey: "node.delay.title", descriptionKey: "node.delay.description", color: "#f59e0b", icon: "delay" },
  stop_error: { titleKey: "node.stop_error.title", descriptionKey: "node.stop_error.description", color: "#ef4444", icon: "stop_error" },
  approval_gate: { titleKey: "node.approval_gate.title", descriptionKey: "node.approval_gate.description", color: "#f59e0b", icon: "approval_gate" },
  noop: { titleKey: "node.noop.title", descriptionKey: "node.noop.description", color: "#8892a4", icon: "noop" },
  end: { titleKey: "node.end.title", descriptionKey: "node.end.description", color: "#ef4444", icon: "end" },
};

// Giữ nguyên mô tả đầu vào/đầu ra từ bản Xanax vanilla v1.
const NODE_IO: Record<GraphNodeType, { inKey: TaskrunnerMessageKey; outKey: TaskrunnerMessageKey }> = {
  trigger: { inKey: "node.trigger.input", outKey: "node.trigger.output" },
  agent: { inKey: "node.agent.input", outKey: "node.agent.output" },
  tool_call: { inKey: "node.tool_call.input", outKey: "node.tool_call.output" },
  condition: { inKey: "node.condition.input", outKey: "node.condition.output" },
  set_data: { inKey: "node.set_data.input", outKey: "node.set_data.output" },
  delay: { inKey: "node.delay.input", outKey: "node.delay.output" },
  workflow_call: { inKey: "node.workflow_call.input", outKey: "node.workflow_call.output" },
  approval_gate: { inKey: "node.approval_gate.input", outKey: "node.approval_gate.output" },
  stop_error: { inKey: "node.stop_error.input", outKey: "node.stop_error.output" },
  noop: { inKey: "node.noop.input", outKey: "node.noop.output" },
  end: { inKey: "node.end.input", outKey: "node.end.output" },
};

const ICON_FOR_TYPE = {
  trigger: "play", agent: "robot", condition: "branch", workflow_call: "box", tool_call: "api",
  set_data: "db", delay: "clock", stop_error: "octagon", approval_gate: "person", noop: "x", end: "stop",
} as const;

interface FlowData extends Record<string, unknown> {
  editor: EditorNode;
  run?: NodeRunStatus;
}
type FlowNode = Node<FlowData, "workflow">;
interface FlowEdgeData extends Record<string, unknown> { editor: EditorEdge }
type FlowEdge = Edge<FlowEdgeData>;

function WorkflowNode({ data, selected }: NodeProps<FlowNode>) {
  const text = useTaskrunnerText();
  const node = data.editor;
  const type = inferNodeType(node);
  const meta = NODE_META[type];
  const runClass = data.run ? c(`node-${data.run.state}`) : "";
  return <div className={`${c("react-flow-node")} ${selected ? c("selected") : ""} ${runClass}`} style={{ borderTopColor: String(node.color || meta.color) }} title={data.run?.detail}>
    {type !== "trigger" ? <Handle type="target" position={Position.Left} /> : null}
    <div className={c("react-node-icon")} style={{ color: String(node.color || meta.color) }}><Icon name={ICON_FOR_TYPE[type]} /></div>
    <div className={c("react-node-copy")}><strong>{node.title || text(meta.titleKey)}</strong><small>{node.sub || text(meta.descriptionKey)}</small>{data.run ? <em>{data.run.detail}</em> : null}</div>
    {type === "condition" ? <><Handle id="true" type="source" position={Position.Right} style={{ top: "36%", background: "#22c55e" }} /><Handle id="false" type="source" position={Position.Right} style={{ top: "72%", background: "#ef4444" }} /></> : type !== "end" && type !== "stop_error" ? <Handle type="source" position={Position.Right} /> : null}
  </div>;
}

const nodeTypes = { workflow: WorkflowNode };

function toFlowNodes(graph: WorkflowGraph): FlowNode[] {
  return graphToEditor(graph).nodes.map((editor) => ({ id: editor.id, type: "workflow", position: { x: editor.x, y: editor.y }, data: { editor } }));
}

function normalizedBranchLabel(label: string): "true" | "false" | null {
  const normalized = label.toLocaleLowerCase("en");
  if (["true", "đúng"].includes(normalized)) return "true";
  if (["false", "sai"].includes(normalized)) return "false";
  return null;
}

function displayedEdgeLabel(editor: EditorEdge, text: TaskrunnerTranslator): string {
  const branch = normalizedBranchLabel(editor[2]);
  return branch ? text(branch === "true" ? "node.branch.true" : "node.branch.false") : editor[2];
}

function toFlowEdges(graph: WorkflowGraph, text: TaskrunnerTranslator): FlowEdge[] {
  return graphToEditor(graph).edges.map((editor, index) => ({
    id: `edge-${index}-${editor[0]}-${editor[1]}`, source: editor[0], target: editor[1],
    sourceHandle: normalizedBranchLabel(editor[2]) || undefined,
    label: displayedEdgeLabel(editor, text) || undefined, animated: false, data: { editor }, style: editor[3] ? { stroke: editor[3] } : undefined,
  }));
}

function taskRunKey(taskId: number): string { return `xanax_active_run_${taskId}`; }

type TriggerKey = "manual" | "schedule" | "webhook" | "workflow_complete" | "meeting_decision";
type TriggerMap = Record<TriggerKey, Record<string, unknown>>;

function normalizedTriggers(task: WorkflowTask, nodeData?: Record<string, unknown>): TriggerMap {
  let config: Record<string, unknown> = {};
  try { config = JSON.parse(task.trigger_config_json || "{}"); } catch { /* dùng giá trị mặc định bên dưới */ }
  const configTriggers = config.triggers && typeof config.triggers === "object" ? config.triggers as Partial<TriggerMap> : {};
  const nodeTriggers = nodeData?.triggers && typeof nodeData.triggers === "object" ? nodeData.triggers as Partial<TriggerMap> : {};
  const primary = task.trigger_type || (task.schedule_enabled ? "schedule" : "manual");
  return {
    manual: { enabled: primary === "manual", ...(configTriggers.manual || {}), ...(nodeTriggers.manual || {}) },
    schedule: { enabled: Boolean(task.schedule_enabled) || primary === "schedule", cron: task.schedule_cron || "", ...(configTriggers.schedule || {}), ...(nodeTriggers.schedule || {}) },
    webhook: { enabled: primary === "webhook", webhook_token: config.webhook_token || "", ...(configTriggers.webhook || {}), ...(nodeTriggers.webhook || {}) },
    workflow_complete: { enabled: primary === "workflow_complete", source_task_id: config.source_task_id ?? null, ...(configTriggers.workflow_complete || {}), ...(nodeTriggers.workflow_complete || {}) },
    meeting_decision: { enabled: primary === "meeting_decision", project_id: config.project_id ?? null, ...(configTriggers.meeting_decision || {}), ...(nodeTriggers.meeting_decision || {}) },
  };
}

function derivedTriggers(triggers: TriggerMap): TriggerMap {
  return {
    ...triggers,
    manual: { ...triggers.manual, enabled: true },
    webhook: { ...triggers.webhook, enabled: true },
    schedule: { ...triggers.schedule, enabled: Boolean(String(triggers.schedule.cron || "").trim()) },
    workflow_complete: { ...triggers.workflow_complete, enabled: Boolean(triggers.workflow_complete.source_task_id) },
    meeting_decision: { ...triggers.meeting_decision, enabled: Boolean(triggers.meeting_decision.project_id) },
  };
}

function triggerConfig(triggers: TriggerMap): Record<string, unknown> {
  return {
    triggers,
    webhook_token: triggers.webhook.webhook_token || "",
    project_id: triggers.meeting_decision.project_id || null,
    source_task_id: triggers.workflow_complete.source_task_id || null,
  };
}

export function WorkflowEditor(props: {
  taskId: number;
  runOnOpen: boolean;
  onBack: () => void;
  onSaved: () => Promise<void>;
  onOpenProject?: (projectId: number, subtab: ProjectSubtab) => void;
  toast: (text: string, kind?: "success" | "error" | "info") => void;
}) {
  return <ReactFlowProvider><WorkflowEditorInner {...props} /></ReactFlowProvider>;
}

function WorkflowEditorInner({ taskId, runOnOpen, onBack, onSaved, onOpenProject, toast }: {
  taskId: number;
  runOnOpen: boolean;
  onBack: () => void;
  onSaved: () => Promise<void>;
  onOpenProject?: (projectId: number, subtab: ProjectSubtab) => void;
  toast: (text: string, kind?: "success" | "error" | "info") => void;
}) {
  const tt = useTooltipText();
  const text = useTaskrunnerText();
  const textRef = useRef(text);
  textRef.current = text;
  const [task, setTask] = useState<WorkflowTask | null>(null);
  const [sourceGraph, setSourceGraph] = useState<WorkflowGraph | null>(null);
  const [originalRaw, setOriginalRaw] = useState("");
  const [nodes, setNodes] = useState<FlowNode[]>([]);
  const [edges, setEdges] = useState<FlowEdge[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [skills, setSkills] = useState<SkillOption[]>([]);
  const [tools, setTools] = useState<ToolOption[]>([]);
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [allTasks, setAllTasks] = useState<WorkflowTask[]>([]);
  const [paletteSearch, setPaletteSearch] = useState("");
  const [inputModal, setInputModal] = useState<null | { test: boolean }>(null);
  const [runInput, setRunInput] = useState("");
  const [running, setRunning] = useState(false);
  const [runCompleted, setRunCompleted] = useState(false);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [approvalQueue, setApprovalQueue] = useState<WorkflowSocketMessage[]>([]);
  const [imageSource, setImageSource] = useState<WorkflowSocketMessage | null>(null);
  const [approvalContent, setApprovalContent] = useState("");
  const [approvalReason, setApprovalReason] = useState("");
  const [imageLightbox, setImageLightbox] = useState<{ images: LightboxImage[]; index: number } | null>(null);
  const activeRunRef = useRef<number | null>(null);
  const activeNodeRef = useRef<string | undefined>(undefined);
  const sendRef = useRef<(message: unknown) => boolean>(() => false);
  const runOnOpenRef = useRef(runOnOpen);
  const { screenToFlowPosition } = useReactFlow<FlowNode, FlowEdge>();

  const setRunId = useCallback((runId: number | null) => {
    activeRunRef.current = runId;
    setActiveRunId(runId);
    if (runId) localStorage.setItem(taskRunKey(taskId), String(runId));
    else localStorage.removeItem(taskRunKey(taskId));
  }, [taskId]);

  const updateRunState = useCallback((nodeId: string | undefined, status: NodeRunStatus | undefined) => {
    if (!nodeId || !status) return;
    setNodes((current) => current.map((node) => node.id === nodeId ? { ...node, data: { ...node.data, run: status } } : node));
  }, []);

  const onSocketMessage = useCallback((message: WorkflowSocketMessage) => {
    if ((message.type === "node_start" || message.type === "agent_start" || message.type === "tool_call_start" || message.type === "delay_start") && message.node_id) {
      activeNodeRef.current = message.node_id;
    }
    const result = reduceWorkflowEvent(message, activeNodeRef.current, text);
    if (result.reset) {
      setRunCompleted(false);
      activeNodeRef.current = undefined;
      setNodes((current) => current.map((node) => ({ ...node, data: { ...node.data, run: undefined } })));
      setApprovalQueue([]);
      setImageSource(null);
    }
    if (result.rememberRun) { setRunId(result.rememberRun); setRunning(true); }
    updateRunState(result.nodeId, result.nodeStatus);
    if (result.clearApproval) setApprovalQueue((current) => current.slice(1));
    if (result.clearImageSource) setImageSource(null);
    if (result.approval) setApprovalQueue((current) => [...current, result.approval!]);
    if (result.imageSource) setImageSource(result.imageSource);
    if (result.terminal) {
      activeNodeRef.current = undefined;
      setApprovalQueue([]);
      setImageSource(null);
      setNodes((current) => current.map((node) => node.data.run && ["running", "paused"].includes(node.data.run.state) ? { ...node, data: { ...node.data, run: result.terminal === "done" ? { state: "done", detail: text("protocol.done") } : result.terminal === "error" ? { state: "error", detail: text("protocol.failed") } : undefined } } : node));
      setRunning(false);
      setRunCompleted(result.terminal === "done");
    }
    if (result.forgetRun) setRunId(null);
    if (result.toast) toast(result.toast.text, result.toast.kind);
    if (message.type === "node_done") activeNodeRef.current = undefined;
  }, [setRunId, text, toast, updateRunState]);

  const socket = useWebSocket<WorkflowSocketMessage>({
    path: "/ws/workflow", enabled: Boolean(task), connectionKey: taskId, onMessage: onSocketMessage,
    onOpen: () => {
      const runId = activeRunRef.current;
      if (runId) sendRef.current({ action: "attach", run_id: runId });
    },
  });
  sendRef.current = socket.send;

  useEffect(() => {
    let disposed = false;
    void Promise.all([
      workflowApi.task(taskId), workflowApi.agents(), workflowApi.skills(), workflowApi.tools(), workflowApi.projects(), workflowApi.tasks(),
    ]).then(([record, agentData, skillData, toolData, projectData, taskData]) => {
      if (disposed) return;
      const raw = record.graph_json?.trim() ? record.graph_json : JSON.stringify(createEmptyGraph(record.trigger_type));
      const graph = parseWorkflowGraph(raw);
      setTask(record); setSourceGraph(graph); setOriginalRaw(raw);
      setNodes(toFlowNodes(graph)); setEdges(toFlowEdges(graph, textRef.current));
      setAgents(agentData.agents || []); setSkills(skillData.skills || []); setTools(toolData.tools || []); setProjects(projectData.projects || []); setAllTasks(taskData.tasks || []);
      const stored = Number(localStorage.getItem(taskRunKey(taskId)) || 0);
      if (stored) { setRunId(stored); setRunning(true); }
      if (runOnOpenRef.current) { runOnOpenRef.current = false; setInputModal({ test: false }); }
    }).catch((error: unknown) => toast(error instanceof Error ? error.message : textRef.current("editor.load_error"), "error"));
    return () => { disposed = true; };
  }, [setRunId, taskId, toast]);

  const onNodesChange = useCallback((changes: NodeChange<FlowNode>[]) => setNodes((current) => applyNodeChanges(changes, current)), []);
  const onEdgesChange = useCallback((changes: EdgeChange<FlowEdge>[]) => setEdges((current) => applyEdgeChanges(changes, current)), []);
  const onConnect = useCallback((connection: Connection) => {
    const branch = connection.sourceHandle === "true" ? "true" : connection.sourceHandle === "false" ? "false" : "";
    const editor = [connection.source, connection.target, branch, ""] as EditorEdge;
    setEdges((current) => addEdge({ ...connection, id: `edge-${Date.now()}`, label: displayedEdgeLabel(editor, text) || undefined, data: { editor } }, current));
  }, [text]);

  useEffect(() => {
    setEdges((current) => current.map((edge) => edge.data?.editor
      ? { ...edge, label: displayedEdgeLabel(edge.data.editor, text) || undefined }
      : edge));
  }, [text]);

  const selected = nodes.find((node) => node.id === selectedId) || null;
  const updateEditor = (modify: (editor: EditorNode) => EditorNode) => setNodes((current) => current.map((node) => node.id === selectedId ? { ...node, data: { ...node.data, editor: modify(node.data.editor) } } : node));

  /* Bấm node đích ở khối "Đưa sang" phải kéo theo cả vệt chọn trên sơ đồ. Vệt đó
     do React Flow vẽ từ cờ `selected` của từng node, còn `selectedId` chỉ quyết
     định bảng thông tin — đặt mỗi `selectedId` là bảng đổi mà sơ đồ vẫn sáng node cũ. */
  const selectNode = (nodeId: string) => {
    setSelectedId(nodeId);
    setNodes((current) => current.map((node) => {
      const shouldSelect = node.id === nodeId;
      return node.selected === shouldSelect ? node : { ...node, selected: shouldSelect };
    }));
  };
  const updateData = (patch: Record<string, unknown>) => updateEditor((editor) => {
    const data = { ...editor.data, ...patch };
    return refreshNodePresentation({ ...editor, data }, { agents, skills, workflows: allTasks, text });
  });

  /* Dòng mô tả phụ thuộc dữ liệu ngoài sơ đồ nên được tính lại khi danh sách hoặc
     ngôn ngữ đổi. `refreshNodePresentation` tự giữ `title` cũ từ `_source`; các
     nhãn mặc định chỉ được component vẽ node tra theo loại. */
  useEffect(() => {
    setNodes((current) => {
      let changed = false;
      const next = current.map((node) => {
        const presentation = refreshNodePresentation(node.data.editor, { agents, skills, workflows: allTasks, text });
        if (presentation.title === node.data.editor.title && presentation.sub === node.data.editor.sub) return node;
        changed = true;
        return { ...node, data: { ...node.data, editor: presentation } };
      });
      return changed ? next : current;
    });
  }, [agents, skills, allTasks, text]);

  const editorGraph = useCallback(() => {
    if (!sourceGraph) return null;
    const editorNodes = nodes.map((node) => ({ ...node.data.editor, x: node.position.x, y: node.position.y }));
    const editorEdges = edges.map((edge) => {
      const base = edge.data?.editor || [edge.source, edge.target, String(edge.label || ""), ""] as EditorEdge;
      base[0] = edge.source; base[1] = edge.target;
      return base;
    });
    return editorToGraph(editorNodes, editorEdges, sourceGraph);
  }, [edges, nodes, sourceGraph]);

  const save = useCallback(async (silent = false): Promise<boolean> => {
    if (!task) return false;
    const graph = editorGraph();
    if (!graph) return false;
    const trigger = graph.nodes.find((node) => inferNodeType(node) === "trigger");
    const sourceTrigger = sourceGraph?.nodes.find((node) => inferNodeType(node) === "trigger");
    const triggerChanged = JSON.stringify(trigger?.data?.triggers) !== JSON.stringify(sourceTrigger?.data?.triggers);
    const body: Partial<WorkflowTask> = { name: task.name };
    if (triggerChanged && trigger) {
      const triggers = derivedTriggers(normalizedTriggers(task, trigger.data));
      trigger.data = { ...(trigger.data || {}), triggers };
      body.trigger_type = (["meeting_decision", "workflow_complete", "schedule"] as TriggerKey[]).find((key) => Boolean(triggers[key].enabled)) || "manual";
      body.trigger_config_json = JSON.stringify(triggerConfig(triggers));
      body.schedule_enabled = Boolean(triggers.schedule.enabled);
      body.schedule_cron = String(triggers.schedule.cron || "");
    }
    const graph_json = serializeWorkflowGraph(originalRaw, graph);
    body.graph_json = graph_json;
    const updated = await workflowApi.updateTask(task.id, body);
    if (updated.graph_json !== graph_json) throw new Error(text("editor.server_graph_error"));
    if (triggerChanged) {
      const savedTriggers = normalizedTriggers(updated);
      setNodes((current) => current.map((flowNode) => inferNodeType(flowNode.data.editor) === "trigger"
        ? { ...flowNode, data: { ...flowNode.data, editor: { ...flowNode.data.editor, data: { ...flowNode.data.editor.data, triggers: savedTriggers } } } }
        : flowNode));
    }
    setTask(updated); setSourceGraph(parseWorkflowGraph(updated.graph_json)); setOriginalRaw(updated.graph_json);
    await onSaved();
    if (!silent) toast(text(graph_json === originalRaw ? "editor.saved_unchanged" : "editor.saved_graph"), "success");
    return true;
  }, [editorGraph, onSaved, originalRaw, sourceGraph, task, text, toast]);

  const addNode = (type: GraphNodeType, position?: { x: number; y: number }) => {
    if (type === "trigger" && nodes.some((node) => inferNodeType(node.data.editor) === "trigger")) { toast(text("editor.one_trigger"), "error"); return; }
    const meta = NODE_META[type];
    const defaults: Partial<Record<GraphNodeType, Record<string, unknown>>> = {
      trigger: { trigger_type: "manual" }, tool_call: { args: {} }, condition: { field: "last_output", mode: "contains", value: "" },
      workflow_call: { wait: true }, set_data: { assignments: {} }, delay: { seconds: 0 },
      stop_error: { message: "Quy trình đã dừng" }, approval_gate: { approver: "CEO", max_retries: 3, timeout_minutes: 0, on_timeout: "fail" },
      noop: { parallel_out: false },
    };
    const editor: EditorNode = { id: `node_${Date.now()}`, type, x: position?.x ?? 180 + nodes.length * 35, y: position?.y ?? 100 + nodes.length * 55, data: { ...(defaults[type] || {}) }, title: "", sub: "", color: meta.color, kind: type };
    setNodes((current) => [...current, { id: editor.id, type: "workflow", position: { x: editor.x, y: editor.y }, data: { editor } }]);
    setSelectedId(editor.id);
  };

  const deleteSelected = () => {
    if (!selected) return;
    if (inferNodeType(selected.data.editor) === "trigger") { toast(text("editor.no_delete_trigger"), "error"); return; }
    setNodes((current) => current.filter((node) => node.id !== selected.id));
    setEdges((current) => current.filter((edge) => edge.source !== selected.id && edge.target !== selected.id));
    setSelectedId(null);
  };

  const startRun = async () => {
    if (!task || !(await save(true))) return;
    setNodes((current) => current.map((node) => ({ ...node, data: { ...node.data, run: undefined } })));
    setRunId(null); setRunning(true); setRunCompleted(false);
    const input = inputModal?.test ? `${text("editor.test_marker")}\n${runInput}` : runInput;
    socket.send({ action: "run", task_id: task.id, input, project_id: task.project_id || null });
    setInputModal(null); setRunInput("");
  };

  const cancel = () => { if (activeRunId) socket.send({ action: "cancel", run_id: activeRunId }); };
  const approval = approvalQueue[0] || null;
  useEffect(() => { if (approval) { setApprovalContent(String(approval.content || "")); setApprovalReason(""); } }, [approval]);
  const answerApproval = async (approved: boolean) => {
    if (!approval?.output_id) return;
    await workflowApi.updateOutput(approval.output_id, approved
      ? { review_status: "approved", edited_content: approvalContent }
      : { review_status: "rejected", notes: approvalReason });
    setApprovalQueue((current) => current.slice(1));
  };
  const answerImageSource = async (mode: "generate" | "asset", assetId?: number) => {
    if (!imageSource?.run_id || !imageSource.node_id) return;
    await workflowApi.chooseImageSource(imageSource.run_id, { node_id: imageSource.node_id, mode, ...(assetId ? { asset_id: assetId } : {}) });
    setImageSource(null);
  };
  const uploadImage = async (file?: File) => {
    if (!file) return;
    const form = new FormData(); form.append("file", file); form.append("note", text("editor.upload_note"));
    const asset = await apiClient.postForm<{ id: number }>("/assets/upload", form);
    await answerImageSource("asset", asset.id);
  };

  const palette = (Object.keys(NODE_META) as GraphNodeType[]).filter((type) => text(NODE_META[type].titleKey).toLocaleLowerCase().includes(paletteSearch.toLocaleLowerCase()));
  if (!task) return <div className={c("editor-loading")}>{text("common.loading_workflow")}</div>;

  // Hai tab runner cùng được mount trong Hub nên các ID của trình sửa có thể bị
  // trùng. Không truy vấn chúng bằng ID; việc đổi selector cần một đợt riêng.
  return <div id="view-editor" data-testid="taskrunner-editor">
    <div id="editor-topbar">
      <Tooltip label={tt("tooltip.workflow.editor.back")}><button className={c("editor-icon-btn")} onClick={onBack} aria-label={tt("tooltip.workflow.editor.back")}><Icon name="arrowLeft" /></button></Tooltip>
      <div className={c("editor-logo")}><Icon name="workflow" /></div>
      <input className={c("editor-title-input")} value={task.name} onChange={(event) => setTask({ ...task, name: event.target.value })} />
      <div className={c("editor-topbar-spacer")} />
      <span className={c("connection-state")}>{socket.isOpen ? text("editor.connected") : socket.state === "auth-error" ? text("editor.session_expired") : text("editor.connecting", socket.reconnectAttempt)}</span>
      {runCompleted && task.project_id && onOpenProject ? (
        <Tooltip label={tt("tooltip.workflow.editor.open_project")}><button
          data-testid="open-completed-run-project"
          className={c("editor-btn")}
          onClick={() => onOpenProject(task.project_id!, "runs")}
        >
          <Icon name="folder" /> {text("editor.project_results")}
        </button></Tooltip>
      ) : null}
      <Tooltip label={tt("tooltip.workflow.editor.save")}><button className={c("editor-btn")} data-testid="save-graph" onClick={() => void save()}><Icon name="save" /> {text("common.save")}</button></Tooltip>
      <Tooltip label={tt("tooltip.workflow.editor.test")}><button className={c("editor-btn")} onClick={() => setInputModal({ test: true })}><Icon name="flask" /> {text("editor.test")}</button></Tooltip>
      {!running ? <Tooltip label={tt("tooltip.workflow.editor.run")}><button className={`${c("editor-btn")} ${c("primary")}`} onClick={() => setInputModal({ test: false })}><Icon name="play" /> {text("common.run")}</button></Tooltip> : <Tooltip label={tt("tooltip.workflow.editor.cancel")}><button className={c("editor-btn")} onClick={cancel}><Icon name="stop" /> {text("common.cancel")}</button></Tooltip>}
    </div>
    <div id="editor-body">
      <aside id="node-palette"><div className={c("palette-header")}>{text("editor.palette_header")}</div><div className={c("palette-search")}><input value={paletteSearch} onChange={(event) => setPaletteSearch(event.target.value)} placeholder={text("editor.palette_search")} /><Icon name="search" /></div><div id="palette-categories">{palette.map((type) => { const meta = NODE_META[type]; return <Tooltip key={type} label={tt("tooltip.workflow.editor.add_node")}><button className={c("palette-node-item")} draggable onDragStart={(event) => { event.dataTransfer.setData("application/x-workflow-node", type); event.dataTransfer.effectAllowed = "move"; }} onClick={() => addNode(type)}><span style={{ color: meta.color }}><Icon name={ICON_FOR_TYPE[type]} /></span><span><strong>{text(meta.titleKey)}</strong><small>{text(meta.descriptionKey)}</small></span></button></Tooltip>; })}</div></aside>
      <div id="canvas-wrap" onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "move"; }} onDrop={(event) => { event.preventDefault(); const type = event.dataTransfer.getData("application/x-workflow-node") as GraphNodeType; if (type in NODE_META) addNode(type, screenToFlowPosition({ x: event.clientX, y: event.clientY })); }}>
        <ReactFlow<FlowNode, FlowEdge> nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeClick={(_, node) => setSelectedId(node.id)} onPaneClick={() => setSelectedId(null)} fitView minZoom={0.2} maxZoom={2}>
          <Background /><MiniMap nodeColor={(node) => String((node.data as FlowData).editor.color || NODE_META[inferNodeType((node.data as FlowData).editor)].color)} /><Controls />
        </ReactFlow>
      </div>
      <aside id="node-inspector" className={selected ? c("open") : ""}>{selected ? <NodeInspector node={selected.data.editor} nodes={nodes} edges={edges} task={task} agents={agents} skills={skills} tools={tools} projects={projects} tasks={allTasks} updateData={updateData} updateTitle={(title) => updateEditor((editor) => ({ ...editor, title, data: { ...editor.data, label: title } }))} onSelectNode={selectNode} onDelete={deleteSelected} /> : null}</aside>
    </div>

    <Modal open={Boolean(inputModal)} title={text(inputModal?.test ? "editor.input_test_title" : "editor.input_title")} onClose={() => setInputModal(null)}><div className={c("modal-desc")}>{text("editor.input_desc")}</div><textarea className={c("modal-input")} rows={5} value={runInput} onChange={(event) => setRunInput(event.target.value)} /><div className={c("modal-actions")}><Tooltip label={tt("tooltip.workflow.editor.input_cancel")}><button className={c("modal-btn")} onClick={() => setInputModal(null)}>{text("common.cancel")}</button></Tooltip><Tooltip label={tt("tooltip.workflow.editor.input_run")}><button className={`${c("modal-btn")} ${c("primary")}`} onClick={() => void startRun()}>{text("common.run")}</button></Tooltip></div></Modal>

    <Modal open={Boolean(approval)} title={text("editor.approval_title", String(approval?.approver || "CEO"))} onClose={() => undefined} wide>
      {approval?.note ? <div className={c("modal-desc")}>{String(approval.note)}</div> : null}
      {approval?.images?.length ? <div className={c("approval-images")}>{approval.images.map((url, index) => <Tooltip key={url} label={tt("tooltip.workflow.editor.preview_image")}><button
        type="button"
        className={c("approval-image-button")}
        aria-label={tt("tooltip.workflow.editor.preview_image")}
        onClick={() => setImageLightbox({ images: approval.images!.map((src, imageIndex) => ({ src, caption: text("editor.post_image", imageIndex + 1) })), index })}
      ><img src={url} alt={text("editor.post_image", index + 1)} /></button></Tooltip>)}</div> : null}
      <label className={c("se-field-label")}>{text("editor.approval_content")}</label><textarea className={c("modal-input")} rows={8} value={approvalContent} onChange={(event) => setApprovalContent(event.target.value)} />
      <label className={c("se-field-label")}>{text("editor.approval_reason")}</label><textarea className={c("modal-input")} rows={2} value={approvalReason} onChange={(event) => setApprovalReason(event.target.value)} />
      <div className={c("modal-actions")}><Tooltip label={tt("tooltip.workflow.editor.reject")}><button className={`${c("modal-btn")} ${c("danger")}`} onClick={() => void answerApproval(false)}>{text("editor.reject")}</button></Tooltip><Tooltip label={tt("tooltip.workflow.editor.approve")}><button className={`${c("modal-btn")} ${c("primary")}`} onClick={() => void answerApproval(true)}>{text("editor.approve")}</button></Tooltip></div>
    </Modal>

    <Modal open={Boolean(imageSource)} title={text("editor.image_source_title")} onClose={() => undefined} wide>
      <div className={c("modal-actions")}><Tooltip label={tt("tooltip.workflow.editor.generate_image")}><button className={`${c("modal-btn")} ${c("primary")}`} onClick={() => void answerImageSource("generate")}>{text("editor.generate_image")}</button></Tooltip><label className={c("modal-btn")}>{text("editor.upload_image")}<input type="file" accept="image/*" hidden onChange={(event) => void uploadImage(event.target.files?.[0])} /></label></div>
      <div className={c("imgsrc-grid")}>{imageSource?.assets?.map((asset) => <Tooltip key={asset.id} label={tt("tooltip.workflow.editor.use_asset")}><button className={c("imgsrc-thumb")} onClick={() => void answerImageSource("asset", asset.id)}><img src={asset.url} alt={asset.filename} /><span>{asset.filename}</span></button></Tooltip>)}</div>
      <div className={c("modal-desc")}>{text("editor.image_timeout", Number(imageSource?.timeout_minutes || 10))}</div>
    </Modal>
    {imageLightbox ? <ImageLightbox
      images={imageLightbox.images}
      index={imageLightbox.index}
      onIndexChange={(index) => setImageLightbox((current) => current ? { ...current, index } : null)}
      onClose={() => setImageLightbox(null)}
    /> : null}
  </div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className={c("inspector-field")}><span>{label}</span>{children}</label>; }

function JsonField({ value, onValidChange, rows = 7 }: { value: unknown; onValidChange: (value: unknown) => void; rows?: number }) {
  const text = useTaskrunnerText();
  const formatted = JSON.stringify(value ?? {}, null, 2);
  const [draft, setDraft] = useState(formatted);
  const [invalid, setInvalid] = useState(false);
  useEffect(() => { setDraft(formatted); setInvalid(false); }, [formatted]);
  const commit = () => {
    try { onValidChange(JSON.parse(draft)); setInvalid(false); }
    catch { setInvalid(true); }
  };
  return <><textarea className={c("se-input")} rows={rows} value={draft} onChange={(event) => setDraft(event.target.value)} onBlur={commit} /><small className={invalid ? c("json-error") : c("json-hint")}>{text(invalid ? "editor.json_invalid" : "editor.json_valid")}</small></>;
}

function NodeInputBlock({ type }: { type: GraphNodeType }) {
  const text = useTaskrunnerText();
  return <div className={`${c("io-block")} ${c("io-in")}`}><div className={c("io-label")}>{text("editor.input")}</div>{text(NODE_IO[type].inKey)}</div>;
}

function NodeOutputBlock({ node, nodes, edges, type, onSelectNode }: {
  node: EditorNode;
  nodes: FlowNode[];
  edges: FlowEdge[];
  type: GraphNodeType;
  onSelectNode: (nodeId: string) => void;
}) {
  const tt = useTooltipText();
  const text = useTaskrunnerText();
  const terminal = type === "end" || type === "stop_error";
  const targets = edges
    .filter((edge) => edge.source === node.id)
    .map((edge) => ({ edge, node: nodes.find((target) => target.id === edge.target) }))
    .filter((item): item is { edge: FlowEdge; node: FlowNode } => Boolean(item.node));

  return <div className={`${c("io-block")} ${c("io-out")}`}>
    <div className={c("io-label")}>{text("editor.output")}</div>
    <div><strong>{text("editor.produces")}</strong> {text(NODE_IO[type].outKey)}</div>
    {!terminal ? <div><strong>{text("editor.sends_to")}</strong> {targets.length ? targets.map((target, index) => <span key={target.edge.id}>{index ? ", " : ""}<Tooltip label={tt("tooltip.workflow.editor.select_target")}><button type="button" className={c("io-link")} onClick={() => onSelectNode(target.node.id)}>{target.node.data.editor.title || text(NODE_META[inferNodeType(target.node.data.editor)].titleKey)}</button></Tooltip></span>) : <span className={c("io-muted")}>{text("editor.no_target")}</span>}</div> : null}
  </div>;
}

function NodeInspector({ node, nodes, edges, task, agents, skills, tools, projects, tasks, updateData, updateTitle, onSelectNode, onDelete }: {
  node: EditorNode;
  nodes: FlowNode[];
  edges: FlowEdge[];
  task: WorkflowTask;
  agents: AgentOption[];
  skills: SkillOption[];
  tools: ToolOption[];
  projects: ProjectOption[];
  tasks: WorkflowTask[];
  updateData: (patch: Record<string, unknown>) => void;
  updateTitle: (title: string) => void;
  onSelectNode: (nodeId: string) => void;
  onDelete: () => void;
}) {
  const tt = useTooltipText();
  const text = useTaskrunnerText();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const type = inferNodeType(node);
  const data = node.data || {};
  const triggers = normalizedTriggers(task, data);
  const updateTrigger = (key: TriggerKey, patch: Record<string, unknown>) => updateData({ triggers: { ...triggers, [key]: { ...triggers[key], ...patch } } });
  return <><div className={c("inspector-head")}><strong>{text(NODE_META[type].titleKey)}</strong></div>
    <NodeInputBlock type={type} />
    <div className={c("insp-group-label")}>{text("editor.configuration")}</div>
    {/* Node "Tác vụ" lấy luôn tên của tác vụ đích làm tên hiển thị nên không cần
        ô đặt tên riêng — hai chỗ đặt tên chỉ khiến chúng lệch nhau. */}
    {type !== "workflow_call" ? <Field label={text("editor.display_name")}><input className={c("se-input")} value={node.title} placeholder={text(NODE_META[type].titleKey)} onChange={(event) => updateTitle(event.target.value)} /></Field> : null}
    {type === "trigger" ? <><div className={c("json-hint")}>{text("editor.trigger_hint")}</div><div className={c("inspector-field")}><span>{text("editor.schedule")}</span><SchedulePicker value={String(triggers.schedule.cron || "")} onChange={(cron) => updateTrigger("schedule", { cron })} /></div><Field label="Webhook"><input className={c("se-input")} readOnly value={triggers.webhook.webhook_token ? `${window.location.origin}/api/workflow/hooks/${String(triggers.webhook.webhook_token)}` : text("editor.webhook_saved_hint")} /></Field><Field label={text("editor.workflow_complete")}><select className={c("se-input")} value={String(triggers.workflow_complete.source_task_id || "")} onChange={(event) => updateTrigger("workflow_complete", { source_task_id: Number(event.target.value) || null })}><option value="">{text("common.none")}</option>{tasks.filter((item) => item.id !== task.id).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field><Field label={text("editor.meeting_decision")}><select className={c("se-input")} value={String(triggers.meeting_decision.project_id || "")} onChange={(event) => updateTrigger("meeting_decision", { project_id: Number(event.target.value) || null })}><option value="">{text("common.none")}</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></Field></> : null}
    {type === "agent" ? <><Field label={text("editor.agent")}><select className={c("se-input")} value={String(data.agent_id || "")} onChange={(event) => { const agent = agents.find((item) => item.id === Number(event.target.value)); updateData({ agent_id: agent?.id || null, agent_name: agent?.name || "", model_pool_id: agent?.model_pool_id || null }); }}><option value="">{text("editor.select_agent")}</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}{agent.role ? ` — ${agent.role}` : ""}</option>)}</select></Field><Field label={text("editor.instructions")}><textarea className={c("se-input")} rows={6} value={String(data.instructions || "")} onChange={(event) => updateData({ instructions: event.target.value })} /></Field><Field label={text("editor.skills")}><select multiple className={c("se-input")} value={(data.skill_ids as number[] || []).map(String)} onChange={(event) => updateData({ skill_ids: Array.from(event.target.selectedOptions).map((option) => Number(option.value)) })}>{skills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select></Field><label className={c("check-field")}><input type="checkbox" checked={Boolean(data.use_rag)} onChange={(event) => updateData({ use_rag: event.target.checked })} /> {text("editor.use_rag")}</label><label className={c("check-field")}><input type="checkbox" checked={Boolean(data.ask_image_source)} onChange={(event) => updateData({ ask_image_source: event.target.checked })} /> {text("editor.ask_image_source")}</label></> : null}
    {type === "tool_call" ? <><Field label={text("editor.tool")}><select className={c("se-input")} value={String(data.tool_name || "")} onChange={(event) => updateData({ tool_name: event.target.value })}><option value="">{text("editor.select_tool")}</option>{tools.map((tool) => <option key={tool.name} value={tool.name}>{tool.name}{tool.description ? ` — ${tool.description}` : ""}</option>)}</select></Field><Field label={text("editor.json_args")}><JsonField value={data.args || {}} onValidChange={(args) => updateData({ args })} /></Field><div className={c("json-hint")}>{text("editor.template_hint")} <code>{"{{product_image}}"}</code>, <code>{"{{product_cut_target}}"}</code>, <code>{"{{last_text}}"}</code>.</div><label className={c("check-field")}><input type="checkbox" checked={Boolean(data.keep_text)} onChange={(event) => updateData({ keep_text: event.target.checked })} /> {text("editor.keep_text")}</label><Field label={text("editor.output_path")}><input className={c("se-input")} value={String(data.output_state_key || "")} onChange={(event) => updateData({ output_state_key: event.target.value })} /></Field></> : null}
    {type === "condition" ? <><Field label={text("editor.data_source")}><select className={c("se-input")} value={String(data.field || "last_output")} onChange={(event) => updateData({ field: event.target.value })}><option value="last_output">{text("editor.previous_result")}</option><option value="input">{text("editor.initial_request")}</option><option value="product_image">{text("editor.product_image")}</option></select></Field><Field label={text("editor.comparison")}><select className={c("se-input")} value={String(data.mode || "contains")} onChange={(event) => updateData({ mode: event.target.value })}><option value="contains">{text("editor.contains")}</option><option value="equals">{text("editor.equals")}</option><option value="not_contains">{text("editor.not_contains")}</option><option value="regex">{text("editor.regex")}</option><option value="co_du_lieu">{text("editor.has_data")}</option><option value="khong_co_du_lieu">{text("editor.no_data")}</option></select></Field>{!["co_du_lieu", "khong_co_du_lieu"].includes(String(data.mode)) ? <Field label={text("editor.value")}><input className={c("se-input")} value={String(data.value || "")} onChange={(event) => updateData({ value: event.target.value })} /></Field> : <div className={c("json-hint")}>{text("editor.empty_check_hint")}</div>}</> : null}
    {type === "workflow_call" ? <><Field label={text("editor.target_workflow")}><select className={c("se-input")} value={String(data.target_task_id || "")} onChange={(event) => updateData({ target_task_id: Number(event.target.value) || null })}><option value="">{text("editor.select_workflow")}</option>{tasks.filter((item) => item.id !== task.id).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field><label className={c("check-field")}><input type="checkbox" checked={data.wait !== false} onChange={(event) => updateData({ wait: event.target.checked })} /> {text("editor.wait_workflow")}</label></> : null}
    {type === "set_data" ? <Field label={text("editor.assignments")}><JsonField value={data.assignments || {}} rows={8} onValidChange={(assignments) => updateData({ assignments })} /></Field> : null}
    {type === "delay" ? <Field label={text("editor.seconds")}><input type="number" min={0} className={c("se-input")} value={Number(data.seconds || 0)} onChange={(event) => updateData({ seconds: Number(event.target.value) })} /></Field> : null}
    {type === "stop_error" ? <Field label={text("editor.error_message")}><textarea className={c("se-input")} rows={4} value={String(data.message) === "Quy trình đã dừng" ? text("editor.default_stop_message") : String(data.message || "")} onChange={(event) => updateData({ message: event.target.value })} /></Field> : null}
    {type === "approval_gate" ? <><Field label={text("editor.approver")}><input className={c("se-input")} value={String(data.approver || "CEO")} onChange={(event) => updateData({ approver: event.target.value })} /></Field><Field label={text("editor.approver_note")}><textarea className={c("se-input")} rows={3} value={String(data.note || "")} onChange={(event) => updateData({ note: event.target.value })} /></Field><Field label={text("editor.max_retries")}><input type="number" min={0} className={c("se-input")} value={Number(data.max_retries ?? 3)} onChange={(event) => updateData({ max_retries: Number(event.target.value) })} /></Field><Field label={text("editor.timeout")}><input type="number" min={0} className={c("se-input")} value={Number(data.timeout_minutes ?? 0)} onChange={(event) => updateData({ timeout_minutes: Number(event.target.value) })} /></Field><Field label={text("editor.on_timeout")}><select className={c("se-input")} value={String(data.on_timeout || "fail")} onChange={(event) => updateData({ on_timeout: event.target.value })}><option value="fail">{text("editor.timeout_fail")}</option><option value="approve">{text("editor.timeout_approve")}</option><option value="reject">{text("editor.timeout_reject")}</option></select></Field></> : null}
    {type === "noop" ? <label className={c("check-field")}><input type="checkbox" checked={Boolean(data.parallel_out)} onChange={(event) => updateData({ parallel_out: event.target.checked })} /> {text("editor.parallel")}</label> : null}
    <NodeOutputBlock node={node} nodes={nodes} edges={edges} type={type} onSelectNode={onSelectNode} />
    <Tooltip label={tt("tooltip.workflow.editor.delete_node")}><button type="button" className={c("inspector-delete-action")} onClick={() => setDeleteOpen(true)}><Icon name="trash" /> {text("editor.delete_node")}</button></Tooltip>
    <Modal open={deleteOpen} title={text("editor.delete_node_title")} onClose={() => setDeleteOpen(false)}>
      <div className={c("modal-desc")}>{text("editor.delete_node_desc", node.title || text(NODE_META[type].titleKey))}</div>
      <div className={c("modal-actions")}><Tooltip label={tt("tooltip.common.cancel_dialog")}><button className={c("modal-btn")} onClick={() => setDeleteOpen(false)}>{text("common.cancel")}</button></Tooltip><Tooltip label={tt("tooltip.workflow.editor.delete_node_confirm")}><button className={`${c("modal-btn")} ${c("danger")}`} onClick={() => { setDeleteOpen(false); onDelete(); }}>{text("editor.delete_node")}</button></Tooltip></div>
    </Modal>
  </>;
}
