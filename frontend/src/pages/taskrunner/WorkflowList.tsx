import { useEffect, useMemo, useState } from "react";

import { Icon } from "../../components/Icon";
import { Modal } from "./Modal";
import { workflowApi } from "./workflowApi";
import type { ProjectOption, WorkflowOutput, WorkflowRun, WorkflowTask } from "./types";
import styles from "./TaskrunnerPage.module.css";

const c = (name: string) => styles[name] ?? name;
const STATUS_LABEL: Record<string, string> = { active: "Đang bật", paused: "Tạm dừng", draft: "Nháp", failed: "Thất bại" };
const FILTERS = ["all", "active", "paused", "draft", "failed"] as const;
const FILTER_LABEL: Record<(typeof FILTERS)[number], string> = { all: "Tất cả", active: "Đang bật", paused: "Tạm dừng", draft: "Nháp", failed: "Thất bại" };

export interface TaskSummary extends WorkflowTask {
  runs: WorkflowRun[];
}

function relativeTime(value?: string): string {
  if (!value) return "Chưa chạy";
  const date = new Date(value.replace(" ", "T") + (value.includes("Z") ? "" : "Z"));
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return "Vừa xong";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} phút trước`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} giờ trước`;
  if (seconds < 2592000) return `${Math.floor(seconds / 86400)} ngày trước`;
  return date.toLocaleDateString("vi-VN");
}

function flowDots(task: WorkflowTask): Array<{ title: string; color: string }> {
  try {
    const graph = JSON.parse(task.graph_json || "null") as { nodes?: Array<Record<string, unknown>> } | null;
    if (graph?.nodes?.length) return [...graph.nodes]
      .sort((left, right) => Number(left.x || 0) - Number(right.x || 0))
      .map((node) => {
        const data = (node.data || {}) as Record<string, unknown>;
        const type = String(node.type || "agent");
        const colors: Record<string, string> = { trigger: "#22c55e", agent: "#3b82f6", condition: "#8b5cf6", end: "#ef4444", approval_gate: "#f59e0b" };
        return { title: String(data.label || data.agent_name || type), color: String(node.color || colors[type] || "#8892a4") };
      });
  } catch { /* legacy below */ }
  try {
    const agents = JSON.parse(task.agents_json || "[]") as Array<{ agent_name?: string; order?: number }>;
    return [{ title: "Bắt đầu", color: "#22c55e" }, ...agents.sort((a, b) => (a.order || 0) - (b.order || 0)).map((agent) => ({ title: agent.agent_name || "Nhân viên AI", color: "#3b82f6" }))];
  } catch { return []; }
}

function OutputReview({ output, onChange }: { output: WorkflowOutput; onChange: (next: WorkflowOutput) => void }) {
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
    <header><strong>Bước {output.step_order || 0} · {output.agent_name || "Hệ thống"}</strong><span>{output.status || "—"}</span></header>
    {editing ? <textarea className={c("modal-input")} rows={7} value={content} onChange={(event) => setContent(event.target.value)} /> : <pre className={c("output-content")}>{content || "(chưa có nội dung)"}</pre>}
    <textarea className={c("modal-input")} rows={2} placeholder="Ghi chú / phản hồi..." value={notes} onChange={(event) => setNotes(event.target.value)} onBlur={() => { if (!editing) void workflowApi.updateOutput(output.id, { notes }); }} />
    <div className={c("output-actions")}>
      <button className={`${c("wf-btn")} ${output.pass_fail === "pass" ? c("selected") : ""}`} onClick={() => void setPassFail("pass")}><Icon name="check" size={14} /> ĐẠT</button>
      <button className={`${c("wf-btn")} ${output.pass_fail === "fail" ? c("selected-danger") : ""}`} onClick={() => void setPassFail("fail")}><Icon name="close" size={14} /> KHÔNG ĐẠT</button>
      <button className={c("wf-btn")} onClick={() => editing ? void save() : setEditing(true)}><Icon name={editing ? "save" : "edit"} size={14} /> {editing ? "Lưu" : "Sửa"}</button>
      <button className={c("wf-btn")} onClick={() => void navigator.clipboard.writeText(content)}><Icon name="document" size={14} /> Sao chép</button>
    </div>
  </article>;
}

export function WorkflowList({ kind, tasks, projects, onKind, onReload, onOpen, toast }: {
  kind: "company" | "automation";
  tasks: TaskSummary[];
  projects: ProjectOption[];
  onKind: (kind: "company" | "automation") => void;
  onReload: () => Promise<void>;
  onOpen: (id: number, run?: boolean) => void;
  toast: (text: string, kind?: "success" | "error" | "info") => void;
}) {
  const [status, setStatus] = useState<(typeof FILTERS)[number]>("all");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [projectId, setProjectId] = useState("");
  const [historyTask, setHistoryTask] = useState<TaskSummary | null>(null);
  const [history, setHistory] = useState<WorkflowRun[]>([]);
  const [runDetail, setRunDetail] = useState<WorkflowRun | null>(null);

  useEffect(() => { setStatus("all"); setSearch(""); }, [kind]);
  const filtered = useMemo(() => tasks.filter((task) =>
    (status === "all" || task.status === status) && task.name.toLocaleLowerCase("vi").includes(search.trim().toLocaleLowerCase("vi"))), [search, status, tasks]);
  const noun = kind === "automation" ? "tác vụ" : "quy trình";

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

  return <div className={c("task-list-page")} data-testid="taskrunner-list">
    <div className={c("main-tabs")}>
      <button className={`${c("main-tab-btn")} ${kind === "company" ? c("active") : ""}`} onClick={() => onKind("company")}><Icon name="people" /> Quy trình</button>
      <button className={`${c("main-tab-btn")} ${kind === "automation" ? c("active") : ""}`} onClick={() => onKind("automation")}><Icon name="robot" /> Tác vụ tự động</button>
    </div>
    <div className={c("filter-tabs")}>
      <div className={c("filter-tabs-list")}>{FILTERS.map((filter) => <button key={filter} className={`${c("filter-tab")} ${filter === status ? c("active") : ""}`} onClick={() => setStatus(filter)}>{FILTER_LABEL[filter]} <span className={c("count")}>{filter === "all" ? tasks.length : tasks.filter((task) => task.status === filter).length}</span></button>)}</div>
      <div className={c("filter-search")}><Icon name="search" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Tìm ${noun}...`} /></div>
    </div>
    <div id="grid-wrap"><div className={c("workflow-grid")}>
      {filtered.length ? filtered.map((task) => {
        const completed = task.runs.filter((run) => run.status === "completed").length;
        const success = task.runs.length ? Math.round(completed / task.runs.length * 1000) / 10 : 0;
        return <article className={c("workflow-card")} key={task.id} data-task-id={task.id} onClick={() => onOpen(task.id)}>
          <div className={c("wf-card-top")}><div className={c("wf-name")}>{task.name}</div><div className={`${c("wf-status")} ${c(task.status)}`}><span className={c("dot")} />{STATUS_LABEL[task.status] || task.status}</div></div>
          <div className={c("wf-desc")}>{task.description || "Chưa có mô tả."}</div>
          <div className={c("wf-flow")}>{flowDots(task).map((dot, index, dots) => <span key={`${dot.title}-${index}`} title={dot.title} className={c("flow-fragment")}><span className={c("wf-flow-node")} style={{ background: dot.color }} />{index < dots.length - 1 ? <span className={c("wf-flow-line")} style={{ background: dot.color }} /> : null}</span>)}</div>
          <div className={c("wf-stats")}><div className={c("wf-stat")}><span className={c("wf-stat-label")}>Tỷ lệ thành công</span><span className={c("wf-stat-value")}>{task.runs.length ? `${success}%` : "—"}</span></div><div className={c("wf-stat")}><span className={c("wf-stat-label")}>Tổng lần chạy</span><span className={c("wf-stat-value")}>{task.runs.length}</span></div><div className={c("wf-stat")}><span className={c("wf-stat-label")}>Lần chạy cuối</span><span className={c("wf-stat-value")}>{relativeTime(task.runs[0]?.created_at)}</span></div></div>
          {task.schedule_enabled ? <div className={c("wf-schedule")}><Icon name="clock" /> {task.schedule_cron}</div> : null}
          <footer className={c("wf-footer")} onClick={(event) => event.stopPropagation()}>
            <button className={`${c("wf-btn")} ${c("primary")}`} onClick={() => onOpen(task.id, true)}><Icon name="play" size={14} /> Chạy</button>
            <button className={c("wf-btn")} onClick={async () => { await workflowApi.updateTask(task.id, { status: task.status === "active" ? "paused" : "active" }); await onReload(); }}><Icon name={task.status === "active" ? "stop" : "play"} size={14} /> {task.status === "active" ? "Tạm dừng" : "Bật"}</button>
            <button className={c("wf-btn")} onClick={() => onOpen(task.id)}><Icon name="edit" size={14} /> Chỉnh sửa</button>
            <button className={c("wf-btn")} onClick={() => void openHistory(task)}><Icon name="clock" size={14} /> Lịch sử</button>
            <button className={`${c("wf-btn")} ${c("danger")}`} onClick={async () => { if (!window.confirm(`Xoá vĩnh viễn ${noun} \"${task.name}\"?`)) return; await workflowApi.deleteTask(task.id); await onReload(); toast(`Đã xoá ${noun}.`, "success"); }}><Icon name="trash" size={14} /></button>
          </footer>
        </article>;
      }) : <div className={c("empty-state")}><Icon name="folder" size={44} /><div className={c("empty-state-text")}>Không tìm thấy {noun} phù hợp</div></div>}
    </div></div>
    <button id="add-workflow-btn" onClick={() => setCreateOpen(true)}><Icon name="x" className={c("plus-icon")} size={16} /> {kind === "automation" ? "Tác vụ" : "Quy trình"} mới</button>

    <Modal open={createOpen} title={`Tạo ${noun} mới`} onClose={() => setCreateOpen(false)}>
      <label className={c("se-field-label")}>Tên *</label><input className={c("se-input")} autoFocus value={name} onChange={(event) => setName(event.target.value)} />
      <label className={c("se-field-label")}>Mô tả</label><textarea className={c("se-input")} rows={3} value={description} onChange={(event) => setDescription(event.target.value)} />
      <label className={c("se-field-label")}>Dự án (tuỳ chọn)</label><select className={c("se-input")} value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">— Không gắn dự án —</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select>
      <div className={c("modal-actions")}><button className={c("modal-btn")} onClick={() => setCreateOpen(false)}>Huỷ</button><button className={`${c("modal-btn")} ${c("primary")}`} onClick={() => void create()}>Tạo và mở trình sửa</button></div>
    </Modal>

    <Modal open={Boolean(historyTask)} title={`Lịch sử — ${historyTask?.name || ""}`} onClose={() => { setHistoryTask(null); setRunDetail(null); }} wide>
      <div className={c("history-layout")}><div className={c("history-runs")}>{history.length ? history.map((run) => <button key={run.id} className={`${c("history-row")} ${run.id === runDetail?.id ? c("active") : ""}`} onClick={() => void inspectRun(run.id)}><span><strong>#{run.id}</strong> · {run.triggered_by || "manual"}<small>{relativeTime(run.created_at)}</small></span><span className={`${c("wf-status")} ${c(run.status === "completed" ? "active" : run.status === "failed" ? "failed" : "paused")}`}>{run.status}</span></button>) : <div className={c("modal-desc")}>Chưa được chạy lần nào.</div>}</div>
        <div className={c("history-detail")}>{runDetail ? (runDetail.outputs?.length ? runDetail.outputs.map((output) => <OutputReview key={output.id} output={output} onChange={(next) => setRunDetail((current) => current ? { ...current, outputs: current.outputs?.map((item) => item.id === next.id ? next : item) } : current)} />) : <div className={c("modal-desc")}>Lần chạy chưa có output.</div>) : <div className={c("modal-desc")}>Chọn một lần chạy để xem và nghiệm thu output.</div>}</div></div>
    </Modal>
  </div>;
}
