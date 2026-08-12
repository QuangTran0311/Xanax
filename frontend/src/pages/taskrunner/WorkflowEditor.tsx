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
import { useWebSocket } from "../../ws/useWebSocket";
import type { ProjectSubtab } from "../hub/types";
import { Modal } from "./Modal";
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

const NODE_META: Record<GraphNodeType, { title: string; description: string; color: string; icon: keyof typeof ICON_FOR_TYPE }> = {
  trigger: { title: "Bắt đầu", description: "Điểm khởi động và cấu hình trigger", color: "#22c55e", icon: "trigger" },
  agent: { title: "Nhân viên AI", description: "Nhân viên AI xử lý nội dung", color: "#3b82f6", icon: "agent" },
  condition: { title: "Điều kiện", description: "Rẽ nhánh Đúng / Sai", color: "#8b5cf6", icon: "condition" },
  workflow_call: { title: "Tác vụ", description: "Gọi quy trình hoặc tác vụ khác", color: "#3b82f6", icon: "workflow_call" },
  tool_call: { title: "Gọi công cụ", description: "Gọi tool với tham số cấu hình", color: "#8892a4", icon: "tool_call" },
  set_data: { title: "Đặt / Sửa dữ liệu", description: "Đặt dữ liệu cho lần chạy", color: "#f59e0b", icon: "set_data" },
  delay: { title: "Chờ", description: "Tạm dừng trước khi đi tiếp", color: "#f59e0b", icon: "delay" },
  stop_error: { title: "Dừng & Báo lỗi", description: "Dừng quy trình với lỗi", color: "#ef4444", icon: "stop_error" },
  approval_gate: { title: "Cổng duyệt", description: "Chờ người phụ trách duyệt", color: "#f59e0b", icon: "approval_gate" },
  noop: { title: "Không làm gì", description: "Cho dữ liệu đi qua", color: "#8892a4", icon: "noop" },
  end: { title: "Kết thúc", description: "Điểm kết thúc quy trình", color: "#ef4444", icon: "end" },
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
  const node = data.editor;
  const type = inferNodeType(node);
  const meta = NODE_META[type];
  const runClass = data.run ? c(`node-${data.run.state}`) : "";
  return <div className={`${c("react-flow-node")} ${selected ? c("selected") : ""} ${runClass}`} style={{ borderTopColor: String(node.color || meta.color) }} title={data.run?.detail}>
    {type !== "trigger" ? <Handle type="target" position={Position.Left} /> : null}
    <div className={c("react-node-icon")} style={{ color: String(node.color || meta.color) }}><Icon name={ICON_FOR_TYPE[type]} /></div>
    <div className={c("react-node-copy")}><strong>{node.title || meta.title}</strong><small>{node.sub || meta.description}</small>{data.run ? <em>{data.run.detail}</em> : null}</div>
    {type === "condition" ? <><Handle id="true" type="source" position={Position.Right} style={{ top: "36%", background: "#22c55e" }} /><Handle id="false" type="source" position={Position.Right} style={{ top: "72%", background: "#ef4444" }} /></> : type !== "end" && type !== "stop_error" ? <Handle type="source" position={Position.Right} /> : null}
  </div>;
}

const nodeTypes = { workflow: WorkflowNode };

function toFlowNodes(graph: WorkflowGraph): FlowNode[] {
  return graphToEditor(graph).nodes.map((editor) => ({ id: editor.id, type: "workflow", position: { x: editor.x, y: editor.y }, data: { editor } }));
}

function toFlowEdges(graph: WorkflowGraph): FlowEdge[] {
  return graphToEditor(graph).edges.map((editor, index) => ({
    id: `edge-${index}-${editor[0]}-${editor[1]}`, source: editor[0], target: editor[1],
    sourceHandle: editor[2] === "Đúng" ? "true" : editor[2] === "Sai" ? "false" : undefined,
    label: editor[2] || undefined, animated: false, data: { editor }, style: editor[3] ? { stroke: editor[3] } : undefined,
  }));
}

function taskRunKey(taskId: number): string { return `xanax_active_run_${taskId}`; }

type TriggerKey = "manual" | "schedule" | "webhook" | "workflow_complete" | "meeting_decision";
type TriggerMap = Record<TriggerKey, Record<string, unknown>>;

function normalizedTriggers(task: WorkflowTask, nodeData?: Record<string, unknown>): TriggerMap {
  let config: Record<string, unknown> = {};
  try { config = JSON.parse(task.trigger_config_json || "{}"); } catch { /* defaults below */ }
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
    const result = reduceWorkflowEvent(message, activeNodeRef.current);
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
      setNodes((current) => current.map((node) => node.data.run && ["running", "paused"].includes(node.data.run.state) ? { ...node, data: { ...node.data, run: result.terminal === "done" ? { state: "done", detail: "Đã hoàn thành" } : result.terminal === "error" ? { state: "error", detail: "Thất bại" } : undefined } } : node));
      setRunning(false);
      setRunCompleted(result.terminal === "done");
    }
    if (result.forgetRun) setRunId(null);
    if (result.toast) toast(result.toast.text, result.toast.kind);
    if (message.type === "node_done") activeNodeRef.current = undefined;
  }, [setRunId, toast, updateRunState]);

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
      setNodes(toFlowNodes(graph)); setEdges(toFlowEdges(graph));
      setAgents(agentData.agents || []); setSkills(skillData.skills || []); setTools(toolData.tools || []); setProjects(projectData.projects || []); setAllTasks(taskData.tasks || []);
      const stored = Number(localStorage.getItem(taskRunKey(taskId)) || 0);
      if (stored) { setRunId(stored); setRunning(true); }
      if (runOnOpenRef.current) { runOnOpenRef.current = false; setInputModal({ test: false }); }
    }).catch((error: unknown) => toast(error instanceof Error ? error.message : "Không tải được quy trình", "error"));
    return () => { disposed = true; };
  }, [setRunId, taskId, toast]);

  const onNodesChange = useCallback((changes: NodeChange<FlowNode>[]) => setNodes((current) => applyNodeChanges(changes, current)), []);
  const onEdgesChange = useCallback((changes: EdgeChange<FlowEdge>[]) => setEdges((current) => applyEdgeChanges(changes, current)), []);
  const onConnect = useCallback((connection: Connection) => {
    const label = connection.sourceHandle === "true" ? "Đúng" : connection.sourceHandle === "false" ? "Sai" : "";
    const editor = [connection.source, connection.target, label, ""] as EditorEdge;
    setEdges((current) => addEdge({ ...connection, id: `edge-${Date.now()}`, label: label || undefined, data: { editor } }, current));
  }, []);

  const selected = nodes.find((node) => node.id === selectedId) || null;
  const updateEditor = (modify: (editor: EditorNode) => EditorNode) => setNodes((current) => current.map((node) => node.id === selectedId ? { ...node, data: { ...node.data, editor: modify(node.data.editor) } } : node));
  const updateData = (patch: Record<string, unknown>) => updateEditor((editor) => {
    const data = { ...editor.data, ...patch };
    return refreshNodePresentation({ ...editor, data }, { agents, skills, workflows: allTasks });
  });

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
    if (updated.graph_json !== graph_json) throw new Error("Server không giữ nguyên graph_json vừa lưu");
    if (triggerChanged) {
      const savedTriggers = normalizedTriggers(updated);
      setNodes((current) => current.map((flowNode) => inferNodeType(flowNode.data.editor) === "trigger"
        ? { ...flowNode, data: { ...flowNode.data, editor: { ...flowNode.data.editor, data: { ...flowNode.data.editor.data, triggers: savedTriggers } } } }
        : flowNode));
    }
    setTask(updated); setSourceGraph(parseWorkflowGraph(updated.graph_json)); setOriginalRaw(updated.graph_json);
    await onSaved();
    if (!silent) toast(graph_json === originalRaw ? "Đã lưu — graph_json không đổi byte." : "Đã lưu đồ thị quy trình.", "success");
    return true;
  }, [editorGraph, onSaved, originalRaw, task, toast]);

  const addNode = (type: GraphNodeType, position?: { x: number; y: number }) => {
    if (type === "trigger" && nodes.some((node) => inferNodeType(node.data.editor) === "trigger")) { toast("Sơ đồ chỉ có một node Bắt đầu.", "error"); return; }
    const meta = NODE_META[type];
    const defaults: Partial<Record<GraphNodeType, Record<string, unknown>>> = {
      trigger: { trigger_type: "manual" }, tool_call: { args: {} }, condition: { field: "last_output", mode: "contains", value: "" },
      workflow_call: { wait: true }, set_data: { assignments: {} }, delay: { seconds: 0 },
      stop_error: { message: "Quy trình đã dừng" }, approval_gate: { approver: "CEO", max_retries: 3, timeout_minutes: 0, on_timeout: "fail" },
      noop: { parallel_out: false },
    };
    const editor: EditorNode = { id: `node_${Date.now()}`, type, x: position?.x ?? 180 + nodes.length * 35, y: position?.y ?? 100 + nodes.length * 55, data: { ...(defaults[type] || {}) }, title: meta.title, sub: "", color: meta.color, kind: type };
    setNodes((current) => [...current, { id: editor.id, type: "workflow", position: { x: editor.x, y: editor.y }, data: { editor } }]);
    setSelectedId(editor.id);
  };

  const deleteSelected = () => {
    if (!selected) return;
    if (inferNodeType(selected.data.editor) === "trigger") { toast("Không thể xoá node Bắt đầu.", "error"); return; }
    setNodes((current) => current.filter((node) => node.id !== selected.id));
    setEdges((current) => current.filter((edge) => edge.source !== selected.id && edge.target !== selected.id));
    setSelectedId(null);
  };

  const startRun = async () => {
    if (!task || !(await save(true))) return;
    setNodes((current) => current.map((node) => ({ ...node, data: { ...node.data, run: undefined } })));
    setRunId(null); setRunning(true); setRunCompleted(false);
    const input = inputModal?.test ? `[CHẠY THỬ]\n${runInput}` : runInput;
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
    const form = new FormData(); form.append("file", file); form.append("note", "Tải lên khi chạy quy trình");
    const asset = await apiClient.postForm<{ id: number }>("/assets/upload", form);
    await answerImageSource("asset", asset.id);
  };

  const palette = (Object.keys(NODE_META) as GraphNodeType[]).filter((type) => NODE_META[type].title.toLocaleLowerCase("vi").includes(paletteSearch.toLocaleLowerCase("vi")));
  if (!task) return <div className={c("editor-loading")}>Đang tải quy trình...</div>;

  return <div id="view-editor" data-testid="taskrunner-editor">
    <div id="editor-topbar">
      <button className={c("editor-icon-btn")} onClick={onBack} title="Quay lại"><Icon name="arrowLeft" /></button>
      <div className={c("editor-logo")}><Icon name="workflow" /></div>
      <input className={c("editor-title-input")} value={task.name} onChange={(event) => setTask({ ...task, name: event.target.value })} />
      <div className={c("editor-topbar-spacer")} />
      <span className={c("connection-state")}>{socket.isOpen ? "Đã kết nối" : socket.state === "auth-error" ? "Hết phiên" : `Đang nối${socket.reconnectAttempt ? ` (${socket.reconnectAttempt}/5)` : ""}`}</span>
      {runCompleted && task.project_id && onOpenProject ? (
        <button
          data-testid="open-completed-run-project"
          className={c("editor-btn")}
          onClick={() => onOpenProject(task.project_id!, "runs")}
        >
          <Icon name="folder" /> Xem kết quả dự án
        </button>
      ) : null}
      <button className={c("editor-btn")} data-testid="save-graph" onClick={() => void save()}><Icon name="save" /> Lưu</button>
      <button className={c("editor-btn")} onClick={() => setInputModal({ test: true })}><Icon name="flask" /> Chạy thử</button>
      {!running ? <button className={`${c("editor-btn")} ${c("primary")}`} onClick={() => setInputModal({ test: false })}><Icon name="play" /> Chạy</button> : <button className={c("editor-btn")} onClick={cancel}><Icon name="stop" /> Huỷ</button>}
    </div>
    <div id="editor-body">
      <aside id="node-palette"><div className={c("palette-header")}>ADD NODE — kéo thả vào sơ đồ</div><div className={c("palette-search")}><input value={paletteSearch} onChange={(event) => setPaletteSearch(event.target.value)} placeholder="Tìm node..." /><Icon name="search" /></div><div id="palette-categories">{palette.map((type) => { const meta = NODE_META[type]; return <button key={type} className={c("palette-node-item")} draggable onDragStart={(event) => { event.dataTransfer.setData("application/x-workflow-node", type); event.dataTransfer.effectAllowed = "move"; }} onClick={() => addNode(type)}><span style={{ color: meta.color }}><Icon name={ICON_FOR_TYPE[type]} /></span><span><strong>{meta.title}</strong><small>{meta.description}</small></span></button>; })}</div></aside>
      <div id="canvas-wrap" onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "move"; }} onDrop={(event) => { event.preventDefault(); const type = event.dataTransfer.getData("application/x-workflow-node") as GraphNodeType; if (type in NODE_META) addNode(type, screenToFlowPosition({ x: event.clientX, y: event.clientY })); }}>
        <ReactFlow<FlowNode, FlowEdge> nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeClick={(_, node) => setSelectedId(node.id)} onPaneClick={() => setSelectedId(null)} fitView minZoom={0.2} maxZoom={2}>
          <Background /><MiniMap nodeColor={(node) => String((node.data as FlowData).editor.color || NODE_META[inferNodeType((node.data as FlowData).editor)].color)} /><Controls />
        </ReactFlow>
      </div>
      <aside id="node-inspector" className={selected ? c("open") : ""}>{selected ? <NodeInspector node={selected.data.editor} task={task} agents={agents} skills={skills} tools={tools} projects={projects} tasks={allTasks} updateData={updateData} updateTitle={(title) => updateEditor((editor) => ({ ...editor, title, data: { ...editor.data, label: title } }))} onDelete={deleteSelected} /> : null}</aside>
    </div>

    <Modal open={Boolean(inputModal)} title={inputModal?.test ? "Dữ liệu đầu vào cho lần chạy thử" : "Yêu cầu đầu vào cho quy trình"} onClose={() => setInputModal(null)}><div className={c("modal-desc")}>Nhập nội dung được chuyển vào node bắt đầu.</div><textarea className={c("modal-input")} rows={5} value={runInput} onChange={(event) => setRunInput(event.target.value)} /><div className={c("modal-actions")}><button className={c("modal-btn")} onClick={() => setInputModal(null)}>Huỷ</button><button className={`${c("modal-btn")} ${c("primary")}`} onClick={() => void startRun()}>Chạy</button></div></Modal>

    <Modal open={Boolean(approval)} title={`Chờ ${String(approval?.approver || "CEO")} duyệt`} onClose={() => undefined} wide>
      {approval?.note ? <div className={c("modal-desc")}>{String(approval.note)}</div> : null}
      {approval?.images?.length ? <div className={c("approval-images")}>{approval.images.map((url) => <img key={url} src={url} alt="Ảnh bài đăng" />)}</div> : null}
      <label className={c("se-field-label")}>Nội dung — có thể sửa trước khi duyệt</label><textarea className={c("modal-input")} rows={8} value={approvalContent} onChange={(event) => setApprovalContent(event.target.value)} />
      <label className={c("se-field-label")}>Không duyệt vì sao?</label><textarea className={c("modal-input")} rows={2} value={approvalReason} onChange={(event) => setApprovalReason(event.target.value)} />
      <div className={c("modal-actions")}><button className={`${c("modal-btn")} ${c("danger")}`} onClick={() => void answerApproval(false)}>Không duyệt — chạy lại</button><button className={`${c("modal-btn")} ${c("primary")}`} onClick={() => void answerApproval(true)}>Duyệt & tiếp tục</button></div>
    </Modal>

    <Modal open={Boolean(imageSource)} title="Ảnh cho bài này lấy từ đâu?" onClose={() => undefined} wide>
      <div className={c("modal-actions")}><button className={`${c("modal-btn")} ${c("primary")}`} onClick={() => void answerImageSource("generate")}>Để nhân viên tự vẽ</button><label className={c("modal-btn")}>Tải ảnh lên<input type="file" accept="image/*" hidden onChange={(event) => void uploadImage(event.target.files?.[0])} /></label></div>
      <div className={c("imgsrc-grid")}>{imageSource?.assets?.map((asset) => <button key={asset.id} className={c("imgsrc-thumb")} onClick={() => void answerImageSource("asset", asset.id)}><img src={asset.url} alt={asset.filename} /><span>{asset.filename}</span></button>)}</div>
      <div className={c("modal-desc")}>Không trả lời trong {imageSource?.timeout_minutes || 10} phút thì nhân viên tự vẽ.</div>
    </Modal>
  </div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className={c("inspector-field")}><span>{label}</span>{children}</label>; }

function JsonField({ value, onValidChange, rows = 7 }: { value: unknown; onValidChange: (value: unknown) => void; rows?: number }) {
  const formatted = JSON.stringify(value ?? {}, null, 2);
  const [draft, setDraft] = useState(formatted);
  const [invalid, setInvalid] = useState(false);
  useEffect(() => { setDraft(formatted); setInvalid(false); }, [formatted]);
  const commit = () => {
    try { onValidChange(JSON.parse(draft)); setInvalid(false); }
    catch { setInvalid(true); }
  };
  return <><textarea className={c("se-input")} rows={rows} value={draft} onChange={(event) => setDraft(event.target.value)} onBlur={commit} /><small className={invalid ? c("json-error") : c("json-hint")}>{invalid ? "JSON chưa hợp lệ — dữ liệu cũ vẫn được giữ." : "JSON hợp lệ sẽ được áp dụng khi rời ô."}</small></>;
}

function NodeInspector({ node, task, agents, skills, tools, projects, tasks, updateData, updateTitle, onDelete }: {
  node: EditorNode;
  task: WorkflowTask;
  agents: AgentOption[];
  skills: SkillOption[];
  tools: ToolOption[];
  projects: ProjectOption[];
  tasks: WorkflowTask[];
  updateData: (patch: Record<string, unknown>) => void;
  updateTitle: (title: string) => void;
  onDelete: () => void;
}) {
  const type = inferNodeType(node);
  const data = node.data || {};
  const triggers = normalizedTriggers(task, data);
  const updateTrigger = (key: TriggerKey, patch: Record<string, unknown>) => updateData({ triggers: { ...triggers, [key]: { ...triggers[key], ...patch } } });
  return <><div className={c("inspector-head")}><strong>{NODE_META[type].title}</strong><button onClick={onDelete}><Icon name="trash" /></button></div>
    <Field label="Tên hiển thị"><input className={c("se-input")} value={node.title} onChange={(event) => updateTitle(event.target.value)} /></Field>
    {type === "trigger" ? <><div className={c("json-hint")}>Chạy tay và webhook luôn sẵn sàng; điền cấu hình nào thì kích hoạt đó tự bật.</div><Field label="Cron hẹn giờ"><input className={c("se-input")} value={String(triggers.schedule.cron || "")} placeholder="0 8 * * *" onChange={(event) => updateTrigger("schedule", { cron: event.target.value })} /></Field><Field label="Webhook"><input className={c("se-input")} readOnly value={triggers.webhook.webhook_token ? `${window.location.origin}/api/workflow/hooks/${String(triggers.webhook.webhook_token)}` : "Lưu quy trình để sinh URL webhook"} /></Field><Field label="Khi quy trình khác hoàn tất"><select className={c("se-input")} value={String(triggers.workflow_complete.source_task_id || "")} onChange={(event) => updateTrigger("workflow_complete", { source_task_id: Number(event.target.value) || null })}><option value="">— Không dùng —</option>{tasks.filter((item) => item.id !== task.id).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field><Field label="Khi cuộc họp dự án chốt biên bản"><select className={c("se-input")} value={String(triggers.meeting_decision.project_id || "")} onChange={(event) => updateTrigger("meeting_decision", { project_id: Number(event.target.value) || null })}><option value="">— Không dùng —</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></Field></> : null}
    {type === "agent" ? <><Field label="Nhân viên AI"><select className={c("se-input")} value={String(data.agent_id || "")} onChange={(event) => { const agent = agents.find((item) => item.id === Number(event.target.value)); updateData({ agent_id: agent?.id || null, agent_name: agent?.name || "", model_pool_id: agent?.model_pool_id || null }); }}><option value="">— Chọn nhân viên —</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}{agent.role ? ` — ${agent.role}` : ""}</option>)}</select></Field><Field label="Hướng dẫn"><textarea className={c("se-input")} rows={6} value={String(data.instructions || "")} onChange={(event) => updateData({ instructions: event.target.value })} /></Field><Field label="Kỹ năng"><select multiple className={c("se-input")} value={(data.skill_ids as number[] || []).map(String)} onChange={(event) => updateData({ skill_ids: Array.from(event.target.selectedOptions).map((option) => Number(option.value)) })}>{skills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select></Field><label className={c("check-field")}><input type="checkbox" checked={Boolean(data.use_rag)} onChange={(event) => updateData({ use_rag: event.target.checked })} /> Dùng tri thức RAG</label><label className={c("check-field")}><input type="checkbox" checked={Boolean(data.ask_image_source)} onChange={(event) => updateData({ ask_image_source: event.target.checked })} /> Hỏi nguồn ảnh trước khi chạy</label></> : null}
    {type === "tool_call" ? <><Field label="Công cụ"><select className={c("se-input")} value={String(data.tool_name || "")} onChange={(event) => updateData({ tool_name: event.target.value })}><option value="">— Chọn công cụ —</option>{tools.map((tool) => <option key={tool.name} value={tool.name}>{tool.name}{tool.description ? ` — ${tool.description}` : ""}</option>)}</select></Field><Field label="Tham số JSON"><JsonField value={data.args || {}} onValidChange={(args) => updateData({ args })} /></Field><div className={c("json-hint")}>Có thể dùng <code>{"{{product_image}}"}</code>, <code>{"{{product_cut_target}}"}</code>, <code>{"{{last_text}}"}</code>.</div><label className={c("check-field")}><input type="checkbox" checked={Boolean(data.keep_text)} onChange={(event) => updateData({ keep_text: event.target.checked })} /> Giữ nội dung bước trước</label><Field label="Lưu đường dẫn file tạo ra vào"><input className={c("se-input")} value={String(data.output_state_key || "")} onChange={(event) => updateData({ output_state_key: event.target.value })} /></Field></> : null}
    {type === "condition" ? <><Field label="Nguồn dữ liệu"><select className={c("se-input")} value={String(data.field || "last_output")} onChange={(event) => updateData({ field: event.target.value })}><option value="last_output">Kết quả bước trước</option><option value="input">Yêu cầu ban đầu</option><option value="product_image">Ảnh sản phẩm người dùng gửi</option></select></Field><Field label="Phép so sánh"><select className={c("se-input")} value={String(data.mode || "contains")} onChange={(event) => updateData({ mode: event.target.value })}><option value="contains">chứa chữ</option><option value="equals">bằng đúng</option><option value="not_contains">không chứa chữ</option><option value="regex">khớp regex</option><option value="co_du_lieu">có dữ liệu</option><option value="khong_co_du_lieu">không có dữ liệu</option></select></Field>{!["co_du_lieu", "khong_co_du_lieu"].includes(String(data.mode)) ? <Field label="Giá trị"><input className={c("se-input")} value={String(data.value || "")} onChange={(event) => updateData({ value: event.target.value })} /></Field> : <div className={c("json-hint")}>Chỉ xét nguồn dữ liệu có rỗng hay không.</div>}</> : null}
    {type === "workflow_call" ? <><Field label="Tác vụ đích"><select className={c("se-input")} value={String(data.target_task_id || "")} onChange={(event) => updateData({ target_task_id: Number(event.target.value) || null })}><option value="">— Chọn tác vụ —</option>{tasks.filter((item) => item.id !== task.id).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field><label className={c("check-field")}><input type="checkbox" checked={data.wait !== false} onChange={(event) => updateData({ wait: event.target.checked })} /> Chờ tác vụ xong và lấy kết quả</label></> : null}
    {type === "set_data" ? <Field label="Dữ liệu cần đặt (JSON)"><JsonField value={data.assignments || {}} rows={8} onValidChange={(assignments) => updateData({ assignments })} /></Field> : null}
    {type === "delay" ? <Field label="Số giây"><input type="number" min={0} className={c("se-input")} value={Number(data.seconds || 0)} onChange={(event) => updateData({ seconds: Number(event.target.value) })} /></Field> : null}
    {type === "stop_error" ? <Field label="Thông báo lỗi"><textarea className={c("se-input")} rows={4} value={String(data.message || "")} onChange={(event) => updateData({ message: event.target.value })} /></Field> : null}
    {type === "approval_gate" ? <><Field label="Người duyệt"><input className={c("se-input")} value={String(data.approver || "CEO")} onChange={(event) => updateData({ approver: event.target.value })} /></Field><Field label="Lời nhắn cho người duyệt"><textarea className={c("se-input")} rows={3} value={String(data.note || "")} onChange={(event) => updateData({ note: event.target.value })} /></Field><Field label="Số lần viết lại tối đa"><input type="number" min={0} className={c("se-input")} value={Number(data.max_retries ?? 3)} onChange={(event) => updateData({ max_retries: Number(event.target.value) })} /></Field><Field label="Hết hạn chờ (phút, 0 = chờ mãi)"><input type="number" min={0} className={c("se-input")} value={Number(data.timeout_minutes ?? 0)} onChange={(event) => updateData({ timeout_minutes: Number(event.target.value) })} /></Field><Field label="Khi hết hạn"><select className={c("se-input")} value={String(data.on_timeout || "fail")} onChange={(event) => updateData({ on_timeout: event.target.value })}><option value="fail">Dừng và báo lỗi</option><option value="approve">Tự duyệt và đi tiếp</option><option value="reject">Từ chối, chạy lại bước trước</option></select></Field></> : null}
    {type === "noop" ? <label className={c("check-field")}><input type="checkbox" checked={Boolean(data.parallel_out)} onChange={(event) => updateData({ parallel_out: event.target.checked })} /> Chạy song song các nhánh đi ra</label> : null}
  </>;
}
