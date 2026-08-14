import { useEffect, useMemo, useState } from "react";

import { Icon } from "../../components/Icon";
import { Markdown } from "../../components/Markdown";
import { Tooltip } from "../../components/Tooltip";
import { useTaskrunnerText, type TaskrunnerMessageKey, type TaskrunnerTranslator } from "../../i18n/taskrunner";
import { useTooltipText, type TooltipMessageKey } from "../../i18n/tooltips";
import { useLanguage, type Language } from "../../store/language";
import type { ProjectSubtab } from "../hub/types";
import { Modal } from "./Modal";
import { describeScheduleCron } from "./SchedulePicker";
import type { GraphEdge, GraphNode, GraphNodeType } from "./graphAdapter";
import { workflowApi } from "./workflowApi";
import type { ProjectOption, WorkflowOutput, WorkflowRun, WorkflowTask } from "./types";
import styles from "./TaskrunnerPage.module.css";

const c = (name: string) => styles[name] ?? name;
const STATUS_LABEL: Record<string, TaskrunnerMessageKey> = { active: "status.active", paused: "status.paused", draft: "status.draft", failed: "status.failed" };
const FILTERS = ["all", "active", "paused", "draft", "failed"] as const;
const FILTER_LABEL: Record<(typeof FILTERS)[number], TaskrunnerMessageKey> = { all: "filter.all", active: "filter.active", paused: "filter.paused", draft: "filter.draft", failed: "filter.failed" };
const FILTER_TOOLTIP: Record<(typeof FILTERS)[number], TooltipMessageKey> = {
  all: "tooltip.workflow.filter.all",
  active: "tooltip.workflow.filter.active",
  paused: "tooltip.workflow.filter.paused",
  draft: "tooltip.workflow.filter.draft",
  failed: "tooltip.workflow.filter.failed",
};
const NODE_TITLE_LABEL: Record<GraphNodeType, TaskrunnerMessageKey> = {
  trigger: "node.trigger.title", agent: "node.agent.title", condition: "node.condition.title",
  workflow_call: "node.workflow_call.title", tool_call: "node.tool_call.title", set_data: "node.set_data.title",
  delay: "node.delay.title", stop_error: "node.stop_error.title", approval_gate: "node.approval_gate.title",
  noop: "node.noop.title", end: "node.end.title",
};
const RUN_STATUS_LABEL: Record<string, TaskrunnerMessageKey> = {
  active: "status.active", paused: "status.paused", draft: "status.draft", failed: "status.failed",
  running: "status.running", completed: "status.completed", cancelled: "status.cancelled", done: "status.done", error: "status.error",
};
const TRIGGER_LABEL: Record<string, TaskrunnerMessageKey> = {
  manual: "trigger.manual", scheduled: "trigger.scheduled", webhook: "trigger.webhook", chained: "trigger.chained",
  meeting_decision: "trigger.meeting_decision", meeting_chat: "trigger.meeting_chat", chat: "trigger.chat",
};

export interface TaskSummary extends WorkflowTask {
  runs: WorkflowRun[];
}

function relativeTime(value: string | undefined, text: TaskrunnerTranslator, language: Language): string {
  if (!value) return text("relative.never");
  const date = new Date(value.replace(" ", "T") + (value.includes("Z") ? "" : "Z"));
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return text("relative.just_now");
  if (seconds < 3600) return text("relative.minutes", Math.floor(seconds / 60));
  if (seconds < 86400) return text("relative.hours", Math.floor(seconds / 3600));
  if (seconds < 2592000) return text("relative.days", Math.floor(seconds / 86400));
  return date.toLocaleDateString(language === "en" ? "en-US" : "vi-VN");
}

function cardRelativeTime(value: string | undefined, text: TaskrunnerTranslator, language: Language): string {
  if (!value) return text("relative.never");
  const date = new Date(value.replace(" ", "T") + (value.includes("Z") ? "" : "Z"));
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return text("relative.just_now");
  if (seconds < 3600) return text("relative.card_minutes", Math.floor(seconds / 60));
  if (seconds < 86400) return text("relative.card_hours", Math.floor(seconds / 3600));
  if (seconds < 2592000) return text("relative.card_days", Math.floor(seconds / 86400));
  return date.toLocaleDateString(language === "en" ? "en-US" : "vi-VN");
}

interface MiniFlowNode {
  id: string;
  title: string;
  color: string;
  x: number;
  y: number;
}

interface MiniFlowEdge {
  from: string;
  to: string;
}

interface MiniFlow {
  nodes: MiniFlowNode[];
  edges: MiniFlowEdge[];
}

const MINI_FLOW_WIDTH = 280;
const MINI_FLOW_HEIGHT = 52;
const MINI_FLOW_PADDING = 7;

function edgeEnds(edge: GraphEdge): MiniFlowEdge | null {
  if (Array.isArray(edge)) {
    const from = String(edge[0] ?? "");
    const to = String(edge[1] ?? "");
    return from && to ? { from, to } : null;
  }
  const from = String(edge.from ?? edge.source ?? "");
  const to = String(edge.to ?? edge.target ?? "");
  return from && to ? { from, to } : null;
}

function sequentialEdges(nodes: MiniFlowNode[]): MiniFlowEdge[] {
  const ordered = [...nodes].sort((left, right) => left.x - right.x || left.y - right.y);
  return ordered.slice(1).map((node, index) => ({ from: ordered[index].id, to: node.id }));
}

function normalizeMiniFlow(nodes: MiniFlowNode[]): MiniFlowNode[] {
  if (!nodes.length) return [];
  const xs = nodes.map((node) => node.x);
  const ys = nodes.map((node) => node.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const rangeX = maxX - minX;
  const rangeY = maxY - minY;
  const drawableWidth = MINI_FLOW_WIDTH - MINI_FLOW_PADDING * 2;
  const drawableHeight = MINI_FLOW_HEIGHT - MINI_FLOW_PADDING * 2;

  // Trục không có độ trải được đặt giữa khung để tránh chia cho 0 và sinh NaN.
  return nodes.map((node) => ({
    ...node,
    x: rangeX ? MINI_FLOW_PADDING + (node.x - minX) / rangeX * drawableWidth : MINI_FLOW_WIDTH / 2,
    y: rangeY ? MINI_FLOW_PADDING + (node.y - minY) / rangeY * drawableHeight : MINI_FLOW_HEIGHT / 2,
  }));
}

function flowDots(task: WorkflowTask, text: TaskrunnerTranslator): MiniFlow {
  try {
    const graph = JSON.parse(task.graph_json || "null") as { nodes?: GraphNode[]; edges?: GraphEdge[] } | null;
    if (graph?.nodes?.length) {
      const nodes = graph.nodes.map((node, index) => {
        const data = (node.data || {}) as Record<string, unknown>;
        const type = String(node.type || "agent");
        const colors: Record<string, string> = { trigger: "#22c55e", agent: "#3b82f6", condition: "#8b5cf6", end: "#ef4444", approval_gate: "#f59e0b" };
        const rawX = Number(node.x);
        const rawY = Number(node.y);
        return {
          id: String(node.id ?? index),
          title: String(data.label || data.agent_name || (type in NODE_TITLE_LABEL ? text(NODE_TITLE_LABEL[type as GraphNodeType]) : type)),
          color: String(node.color || colors[type] || "#8892a4"),
          x: Number.isFinite(rawX) ? rawX : index,
          y: Number.isFinite(rawY) ? rawY : 0,
        };
      });
      const edges = (graph.edges || []).map(edgeEnds).filter((edge): edge is MiniFlowEdge => Boolean(edge));
      return { nodes: normalizeMiniFlow(nodes), edges: edges.length ? edges : sequentialEdges(nodes) };
    }
  } catch { /* dùng dữ liệu kiểu cũ ở dưới */ }
  try {
    const agents = JSON.parse(task.agents_json || "[]") as Array<{ agent_name?: string; order?: number }>;
    const nodes = [{ id: "legacy-trigger", title: text("list.legacy_start"), color: "#22c55e", x: 0, y: 0 }, ...agents
      .sort((a, b) => (a.order || 0) - (b.order || 0))
      .map((agent, index) => ({ id: `legacy-agent-${index}`, title: agent.agent_name || text("list.legacy_agent"), color: "#3b82f6", x: index + 1, y: 0 }))];
    return { nodes: normalizeMiniFlow(nodes), edges: sequentialEdges(nodes) };
  } catch { return { nodes: [], edges: [] }; }
}

function OutputReview({ output, onChange }: { output: WorkflowOutput; onChange: (next: WorkflowOutput) => void }) {
  const tt = useTooltipText();
  const text = useTaskrunnerText();
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(output.edited_content || output.output_content || "");
  const [notes, setNotes] = useState(output.notes || "");
  const setPassFail = async (pass_fail: "pass" | "fail") => {
    await workflowApi.updateOutput(output.id, { pass_fail });
    onChange({ ...output, pass_fail });
  };
  const save = async () => {
    await workflowApi.updateOutput(output.id, { edited_content: content, notes });
    onChange({ ...output, edited_content: content, notes });
    setEditing(false);
  };
  return <article className={c("output-review")} data-output-id={output.id}>
    <header><strong>{text("output.step", output.step_order || 0, output.agent_name || text("common.system"))}</strong><span>{output.status && RUN_STATUS_LABEL[output.status] ? text(RUN_STATUS_LABEL[output.status]) : output.status || "—"}</span></header>
    {editing ? <textarea className={c("modal-input")} rows={7} value={content} onChange={(event) => setContent(event.target.value)} /> : <div className={c("output-content")}><Markdown content={content || text("common.no_content")} /></div>}
    <textarea className={c("modal-input")} rows={2} placeholder={text("output.notes_placeholder")} value={notes} onChange={(event) => setNotes(event.target.value)} onBlur={() => { if (!editing) void workflowApi.updateOutput(output.id, { notes }); }} />
    <div className={c("output-actions")}>
      <Tooltip label={tt("tooltip.workflow.output.pass")}><button className={`${c("wf-btn")} ${output.pass_fail === "pass" ? c("selected") : ""}`} onClick={() => void setPassFail("pass")}><Icon name="check" size={14} /> {text("output.pass")}</button></Tooltip>
      <Tooltip label={tt("tooltip.workflow.output.fail")}><button className={`${c("wf-btn")} ${output.pass_fail === "fail" ? c("selected-danger") : ""}`} onClick={() => void setPassFail("fail")}><Icon name="close" size={14} /> {text("output.fail")}</button></Tooltip>
      <Tooltip label={tt(editing ? "tooltip.workflow.output.save" : "tooltip.workflow.output.edit")}><button className={c("wf-btn")} onClick={() => editing ? void save() : setEditing(true)}><Icon name={editing ? "save" : "edit"} size={14} /> {text(editing ? "common.save" : "common.edit")}</button></Tooltip>
      <Tooltip label={tt("tooltip.workflow.output.copy")}><button className={c("wf-btn")} onClick={() => void navigator.clipboard.writeText(content)}><Icon name="document" size={14} /> {text("common.copy")}</button></Tooltip>
    </div>
  </article>;
}

export function WorkflowList({
  kind,
  tasks,
  projects,
  showKindTabs = true,
  onKind,
  onReload,
  onOpen,
  onOpenProject,
  toast,
}: {
  kind: "company" | "automation";
  tasks: TaskSummary[];
  projects: ProjectOption[];
  showKindTabs?: boolean;
  onKind: (kind: "company" | "automation") => void;
  onReload: () => Promise<void>;
  onOpen: (id: number, run?: boolean) => void;
  onOpenProject?: (projectId: number, subtab: ProjectSubtab) => void;
  toast: (text: string, kind?: "success" | "error" | "info") => void;
}) {
  const tt = useTooltipText();
  const text = useTaskrunnerText();
  const { language } = useLanguage();
  const [status, setStatus] = useState<(typeof FILTERS)[number]>("all");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [projectId, setProjectId] = useState("");
  const [historyTask, setHistoryTask] = useState<TaskSummary | null>(null);
  const [history, setHistory] = useState<WorkflowRun[]>([]);
  const [runDetail, setRunDetail] = useState<WorkflowRun | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<TaskSummary | null>(null);

  useEffect(() => { setStatus("all"); setSearch(""); }, [kind]);
  const filtered = useMemo(() => tasks.filter((task) =>
    (status === "all" || task.status === status) && task.name.toLocaleLowerCase(language).includes(search.trim().toLocaleLowerCase(language))), [language, search, status, tasks]);
  const cardTooltip = (action: "run" | "follow" | "pause" | "enable" | "edit" | "history" | "delete" | "delete_running") =>
    `tooltip.${kind === "automation" ? "automation" : "workflow"}.card.${action}` as TooltipMessageKey;

  const create = async () => {
    if (!name.trim()) return;
    const task = await workflowApi.createTask({
      name: name.trim(), kind, description: description.trim(), project_id: projectId ? Number(projectId) : null,
      agents_json: "[]", graph_json: "", trigger_type: "manual", trigger_config_json: "{}", schedule_enabled: false, schedule_cron: "",
    });
    setCreateOpen(false); setName(""); setDescription(""); setProjectId("");
    await onReload();
    onOpen(task.id);
  };

  const openHistory = async (task: TaskSummary) => {
    setHistoryTask(task); setRunDetail(null);
    const data = await workflowApi.runs(task.id);
    setHistory(data.runs || []);
  };

  const inspectRun = async (id: number) => {
    setRunDetail(await workflowApi.run(id));
  };

  const deleteSelected = async () => {
    if (!deleteTarget) return;
    await workflowApi.deleteTask(deleteTarget.id);
    setDeleteTarget(null);
    await onReload();
    toast(text(kind === "automation" ? "list.deleted_automation" : "list.deleted_company"), "success");
  };

  return <div className={c("task-list-page")} data-testid="taskrunner-list">
    {showKindTabs ? <div className={c("main-tabs")}>
      <Tooltip label={tt("tooltip.workflow.tab.company")}><button className={`${c("main-tab-btn")} ${kind === "company" ? c("active") : ""}`} onClick={() => onKind("company")}><Icon name="people" /> {text("kind.company")}</button></Tooltip>
      <Tooltip label={tt("tooltip.workflow.tab.automation")}><button className={`${c("main-tab-btn")} ${kind === "automation" ? c("active") : ""}`} onClick={() => onKind("automation")}><Icon name="robot" /> {text("kind.automation")}</button></Tooltip>
    </div> : null}
    <div className={c("filter-tabs")}>
      <div className={c("filter-tabs-list")}>{FILTERS.map((filter) => <Tooltip key={filter} label={tt(FILTER_TOOLTIP[filter])}><button className={`${c("filter-tab")} ${filter === status ? c("active") : ""}`} onClick={() => setStatus(filter)}>{text(FILTER_LABEL[filter])} <span className={c("count")}>{filter === "all" ? tasks.length : tasks.filter((task) => task.status === filter).length}</span></button></Tooltip>)}</div>
      <div className={c("filter-search")}><Icon name="search" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={text(kind === "automation" ? "list.search_automation" : "list.search_company")} /></div>
    </div>
    <div id="grid-wrap"><div className={c("workflow-grid")}>
      {filtered.length ? filtered.map((task) => {
        const completed = task.runs.filter((run) => run.status === "completed").length;
        const success = task.runs.length ? Math.round(completed / task.runs.length * 1000) / 10 : 0;
        const miniFlow = flowDots(task, text);
        const miniNodes = new Map(miniFlow.nodes.map((node) => [node.id, node]));
        const isRunning = task.runs[0]?.status === "running";
        return <article className={c("workflow-card")} key={task.id} data-task-id={task.id} onClick={() => onOpen(task.id)}>
          <div className={c("wf-card-top")}><div className={c("wf-name")}>{task.name}</div>{isRunning ? <div className={`${c("wf-status")} ${c("running")}`}><span className={c("dot")} />{text("list.running")}</div> : <div className={`${c("wf-status")} ${c(task.status)}`}><span className={c("dot")} />{STATUS_LABEL[task.status] ? text(STATUS_LABEL[task.status]) : task.status}</div>}</div>
          <div className={c("wf-desc")}>{task.description || text("list.no_description")}</div>
          <div className={c("wf-flow")}>
            <svg className={c("wf-flow-graph")} viewBox={`0 0 ${MINI_FLOW_WIDTH} ${MINI_FLOW_HEIGHT}`} preserveAspectRatio="xMidYMid meet" role="img" aria-label={text("list.graph_aria", miniFlow.nodes.length)} focusable="false">
              {miniFlow.edges.map((edge, index) => {
                const from = miniNodes.get(edge.from);
                const to = miniNodes.get(edge.to);
                return from && to ? <line key={`${edge.from}-${edge.to}-${index}`} className={c("wf-flow-line")} x1={from.x} y1={from.y} x2={to.x} y2={to.y} /> : null;
              })}
              {miniFlow.nodes.map((node, index) => <circle key={`${node.id}-${index}`} className={c("wf-flow-node")} cx={node.x} cy={node.y} r={4} fill={node.color}><title>{node.title}</title></circle>)}
            </svg>
            <span className={c("wf-flow-label")}>{text("list.steps", miniFlow.nodes.length)}</span>
          </div>
          <div className={c("wf-stats")}><div className={c("wf-stat")}><span className={c("wf-stat-label")}>{text("list.success")}</span><span className={c("wf-stat-value")}>{task.runs.length ? `${success}%` : "—"}</span></div><div className={c("wf-stat")}><span className={c("wf-stat-label")}>{text("list.runs")}</span><span className={c("wf-stat-value")}>{task.runs.length}</span></div><div className={c("wf-stat")}><span className={c("wf-stat-label")}>{text("list.last_run")}</span><span className={`${c("wf-stat-value")} ${c("muted")}`}>{cardRelativeTime(task.runs[0]?.created_at, text, language)}</span></div></div>
          {task.schedule_enabled ? <div className={c("wf-schedule")}><Icon name="clock" /> {describeScheduleCron(task.schedule_cron, language)}</div> : null}
          <footer className={c("wf-footer")} onClick={(event) => event.stopPropagation()}>
            <Tooltip label={tt(cardTooltip(isRunning ? "follow" : "run"))}><button className={`${c("wf-btn")} ${c("primary")}`} aria-label={tt(cardTooltip(isRunning ? "follow" : "run"))} onClick={() => onOpen(task.id, isRunning ? undefined : true)}><Icon name={isRunning ? "eye" : "play"} size={13} /><span className={c("wf-btn-label")}>{text(isRunning ? "list.follow" : "common.run")}</span></button></Tooltip>
            <Tooltip label={tt(cardTooltip(task.status === "active" ? "pause" : "enable"))}><button className={c("wf-btn")} aria-label={tt(cardTooltip(task.status === "active" ? "pause" : "enable"))} onClick={async () => { await workflowApi.updateTask(task.id, { status: task.status === "active" ? "paused" : "active" }); await onReload(); }}><Icon name={task.status === "active" ? "stop" : "play"} size={13} /><span className={c("wf-btn-label")}>{text(task.status === "active" ? "list.pause" : "list.enable")}</span></button></Tooltip>
            <Tooltip label={tt(cardTooltip("edit"))}><button className={c("wf-btn")} aria-label={tt(cardTooltip("edit"))} onClick={() => onOpen(task.id)}><Icon name="edit" size={13} /><span className={c("wf-btn-label")}>{text("list.edit")}</span></button></Tooltip>
            <Tooltip label={tt(cardTooltip("history"))}><button className={c("wf-btn")} aria-label={tt(cardTooltip("history"))} onClick={() => void openHistory(task)}><Icon name="clock" size={13} /><span className={c("wf-btn-label")}>{text("list.history")}</span></button></Tooltip>
            <Tooltip label={tt(cardTooltip(isRunning ? "delete_running" : "delete"))}><button className={`${c("wf-btn")} ${c("danger")} ${c("icon-only")}`} disabled={isRunning} aria-label={tt(cardTooltip("delete"))} onClick={() => setDeleteTarget(task)}><Icon name="trash" size={14} /></button></Tooltip>
          </footer>
        </article>;
      }) : <div className={c("empty-state")}><Icon name="folder" size={44} /><div className={c("empty-state-text")}>{text(kind === "automation" ? "list.empty_automation" : "list.empty_company")}</div></div>}
    </div></div>
    <Tooltip label={tt(kind === "automation" ? "tooltip.automation.create" : "tooltip.workflow.create")}><button id="add-workflow-btn" onClick={() => setCreateOpen(true)}><Icon name="x" className={c("plus-icon")} size={16} /> {text(kind === "automation" ? "list.new_automation" : "list.new_company")}</button></Tooltip>

    <Modal open={createOpen} title={text(kind === "automation" ? "list.create_automation" : "list.create_company")} onClose={() => setCreateOpen(false)}>
      <label className={c("se-field-label")}>{text("list.name")}</label><input className={c("se-input")} autoFocus value={name} onChange={(event) => setName(event.target.value)} />
      <label className={c("se-field-label")}>{text("list.description")}</label><textarea className={c("se-input")} rows={3} value={description} onChange={(event) => setDescription(event.target.value)} />
      <label className={c("se-field-label")}>{text("list.optional_project")}</label><select className={c("se-input")} value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">{text("list.no_project")}</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select>
      <div className={c("modal-actions")}><Tooltip label={tt("tooltip.common.cancel_dialog")}><button className={c("modal-btn")} onClick={() => setCreateOpen(false)}>{text("common.cancel")}</button></Tooltip><Tooltip label={tt("tooltip.workflow.create_confirm")}><button className={`${c("modal-btn")} ${c("primary")}`} onClick={() => void create()}>{text("list.create_and_edit")}</button></Tooltip></div>
    </Modal>

    <Modal open={Boolean(deleteTarget)} title={text(kind === "automation" ? "list.delete_automation_title" : "list.delete_company_title")} onClose={() => setDeleteTarget(null)}>
      <div className={c("modal-desc")}>{text(kind === "automation" ? "list.delete_automation_desc" : "list.delete_company_desc", deleteTarget?.name || "")}</div>
      <div className={c("modal-actions")}><Tooltip label={tt("tooltip.common.cancel_dialog")}><button className={c("modal-btn")} onClick={() => setDeleteTarget(null)}>{text("common.cancel")}</button></Tooltip><Tooltip label={tt("tooltip.workflow.delete_confirm")}><button className={`${c("modal-btn")} ${c("danger")}`} onClick={() => void deleteSelected()}>{text("common.delete")}</button></Tooltip></div>
    </Modal>

    <Modal open={Boolean(historyTask)} title={text("list.history_title", historyTask?.name || "")} onClose={() => { setHistoryTask(null); setRunDetail(null); }} wide>
      <div className={c("history-layout")}><div className={c("history-runs")}>{history.length ? history.map((run) => <Tooltip key={run.id} label={tt("tooltip.workflow.history.select_run")}><button className={`${c("history-row")} ${run.id === runDetail?.id ? c("active") : ""}`} onClick={() => void inspectRun(run.id)}><span><strong>#{run.id}</strong> · {run.triggered_by && TRIGGER_LABEL[run.triggered_by] ? text(TRIGGER_LABEL[run.triggered_by]) : run.triggered_by || text("trigger.manual")}<small>{relativeTime(run.created_at, text, language)}</small></span><span className={`${c("wf-status")} ${c(run.status === "completed" ? "active" : run.status === "failed" ? "failed" : "paused")}`}>{RUN_STATUS_LABEL[run.status] ? text(RUN_STATUS_LABEL[run.status]) : run.status}</span></button></Tooltip>) : <div className={c("modal-desc")}>{text("list.never_run")}</div>}</div>
        <div className={c("history-detail")}>
          {runDetail && historyTask?.project_id && onOpenProject ? <div className={c("run-project-nav")}>
            <Tooltip label={tt("tooltip.workflow.history.open_project")}><button
              data-testid="open-run-project"
              className={`${c("wf-btn")} ${c("primary")}`}
              onClick={() => onOpenProject(
                historyTask.project_id!,
                runDetail.outputs?.some((output) => output.review_status === "waiting_review") ? "review" : "runs",
              )}
            >
              <Icon name="folder" size={14} /> {text("list.open_project_result")}
            </button></Tooltip>
          </div> : null}
          {runDetail ? (runDetail.outputs?.length ? runDetail.outputs.map((output) => <OutputReview key={output.id} output={output} onChange={(next) => setRunDetail((current) => current ? { ...current, outputs: current.outputs?.map((item) => item.id === next.id ? next : item) } : current)} />) : <div className={c("modal-desc")}>{text("list.no_output")}</div>) : <div className={c("modal-desc")}>{text("list.select_run")}</div>}
        </div></div>
    </Modal>
  </div>;
}
