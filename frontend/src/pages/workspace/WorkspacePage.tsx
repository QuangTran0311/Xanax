import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient, ApiError } from "../../api/client";
import { buildAttachmentBlock, uploadAttachment, type ChatAttachment } from "../../components/ChatAttach";
import { Icon } from "../../components/Icon";
import { Markdown } from "../../components/Markdown";
import { sessionApi } from "../../store/session";
import { useWebSocket } from "../../ws/useWebSocket";
import type {
  AgentOption,
  Message,
  ProjectOption,
  ToolOption,
  ToolResult,
  TrainingSession,
  TrainingSocketMessage,
} from "./types";
import styles from "./WorkspacePage.module.css";

const cx = (...names: Array<string | false | null | undefined>) => names.filter(Boolean).join(" ");
const c = (name: string) => styles[name] ?? name;

interface CurrentUser { username: string }
interface SessionListResponse { sessions: TrainingSession[] }
interface AgentListResponse { agents: AgentOption[] }
interface ProjectListResponse { projects: ProjectOption[] }
interface ToolsResponse { tools: ToolOption[]; allowed: string[]; note?: string }
interface DistillResponse { notes?: string; lessons?: unknown[] }
interface CloseResponse {
  written_by_scope?: { agent?: number; project?: number; skill?: number };
  agent_name?: string;
  project_name?: string;
}

type ToastKind = "" | "success" | "error";

function fmtDate(value?: string, full = false): string {
  if (!value) return "—";
  const normalized = value.endsWith("Z") ? value : `${value}Z`;
  return full
    ? new Date(normalized).toLocaleString("vi-VN")
    : new Date(normalized).toLocaleDateString("vi-VN");
}

function messageFromError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function WorkspacePage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [selected, setSelected] = useState<TrainingSession | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState("");
  const [toolResults, setToolResults] = useState<ToolResult[]>([]);
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [tools, setTools] = useState<ToolOption[]>([]);
  const [allowedTools, setAllowedTools] = useState<string[]>([]);
  const [toolsNote, setToolsNote] = useState("");
  const [notesBusy, setNotesBusy] = useState(false);
  const [sessionModal, setSessionModal] = useState(false);
  const [feedbackModal, setFeedbackModal] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newTask, setNewTask] = useState("");
  const [newAgent, setNewAgent] = useState("");
  const [newProject, setNewProject] = useState("");
  const [feedback, setFeedback] = useState("");
  const [toastState, setToastState] = useState<{ text: string; kind: ToastKind }>({ text: "", kind: "" });
  const messagesRef = useRef<HTMLDivElement>(null);
  const notesRef = useRef<HTMLTextAreaElement>(null);
  const streamTimerRef = useRef<number | null>(null);
  const streamContentRef = useRef("");
  const toastTimerRef = useRef<number | null>(null);

  const toast = useCallback((text: string, kind: ToastKind = "") => {
    setToastState({ text, kind });
    if (toastTimerRef.current !== null) window.clearTimeout(toastTimerRef.current);
    toastTimerRef.current = window.setTimeout(() => setToastState({ text: "", kind: "" }), 2800);
  }, []);

  const loadSessions = useCallback(async () => {
    const data = await apiClient.get<SessionListResponse>("/training/sessions");
    setSessions(data.sessions ?? []);
  }, []);

  const loadRosters = useCallback(async () => {
    const [agentResult, projectResult] = await Promise.allSettled([
      apiClient.get<AgentListResponse>("/agent-configs/"),
      apiClient.get<ProjectListResponse>("/projects/"),
    ]);
    if (agentResult.status === "fulfilled") setAgents(agentResult.value.agents ?? []);
    if (projectResult.status === "fulfilled") setProjects(projectResult.value.projects ?? []);
  }, []);

  useEffect(() => {
    const theme = localStorage.getItem("hub_theme") || "light";
    document.body.classList.toggle("light", theme === "light");
    const onStorage = (event: StorageEvent) => {
      if (event.key === "hub_theme") document.body.classList.toggle("light", (event.newValue || "light") === "light");
    };
    window.addEventListener("storage", onStorage);
    void Promise.all([sessionApi.current(), loadSessions(), loadRosters()])
      .then(([me]) => setUser(me))
      .catch(() => navigate("/v2/login", { replace: true }));
    return () => window.removeEventListener("storage", onStorage);
  }, [loadRosters, loadSessions, navigate]);

  useEffect(() => {
    const idleMs = 15 * 60 * 1000;
    let idleTimer = 0;
    const reset = () => {
      window.clearTimeout(idleTimer);
      idleTimer = window.setTimeout(() => {
        if (streaming) { reset(); return; }
        void sessionApi.logout().finally(() => navigate("/v2/login?reason=idle", { replace: true }));
      }, idleMs);
    };
    const events: Array<keyof WindowEventMap> = ["mousemove", "mousedown", "keydown", "touchstart", "scroll"];
    events.forEach((event) => window.addEventListener(event, reset, { passive: true }));
    reset();
    return () => {
      window.clearTimeout(idleTimer);
      events.forEach((event) => window.removeEventListener(event, reset));
    };
  }, [navigate, streaming]);

  const loadTools = useCallback(async (session: TrainingSession) => {
    if (!session.agent_id) {
      setTools([]); setAllowedTools([]); setToolsNote("");
      return;
    }
    try {
      const data = await apiClient.get<ToolsResponse>(`/training/sessions/${session.id}/tools`);
      setTools(data.tools ?? []);
      setAllowedTools(data.allowed ?? []);
      setToolsNote(data.note ?? "");
    } catch (error) {
      setTools([]);
      setAllowedTools([]);
      setToolsNote(error instanceof ApiError && error.status === 404
        ? "Server chưa có API này — mã mới chưa được nạp. Khởi động lại server rồi tải lại trang."
        : `Không đọc được danh sách công cụ: ${messageFromError(error, "lỗi không xác định")}`);
    }
  }, []);

  const selectSession = useCallback(async (id: number) => {
    const session = await apiClient.get<TrainingSession>(`/training/sessions/${id}`);
    setSelected(session);
    setMessages(session.messages ?? []);
    setStreaming(false);
    streamContentRef.current = "";
    setStreamContent("");
    setToolResults([]);
    await Promise.all([loadSessions(), loadTools(session)]);
  }, [loadSessions, loadTools]);

  const onSocketMessage = useCallback((message: TrainingSocketMessage) => {
    if (message.type === "status") {
      if (["summarising", "analysing", "improving"].includes(message.status ?? "")) setNotesBusy(true);
      else {
        setStreaming(true);
        streamContentRef.current = "";
        setStreamContent("");
        setToolResults([]);
      }
      return;
    }
    if (message.type === "chunk") {
      setStreaming(true);
      streamContentRef.current += message.content;
      setStreamContent(streamContentRef.current);
      return;
    }
    if (message.type === "tool_executed") {
      streamContentRef.current = message.clean_text ?? "";
      setStreamContent(streamContentRef.current);
      if (message.results?.length) setToolResults((current) => [...current, ...message.results!]);
      return;
    }
    if (message.type === "done") {
      setStreaming(false);
      const completed = streamContentRef.current;
      streamContentRef.current = "";
      setStreamContent("");
      if (completed) setMessages((current) => [...current, { role: "assistant", content: completed }]);
      if (streamTimerRef.current !== null) window.clearTimeout(streamTimerRef.current);
      streamTimerRef.current = null;
      return;
    }
    if (message.type === "notes_updated" || message.type === "failure_analysed") {
      setNotesBusy(false);
      setSelected((current) => current ? { ...current, result_notes: message.content } : current);
      toast(message.type === "notes_updated"
        ? "Đã đúc kết xong — sửa lại nếu cần rồi bấm \"Lưu bài học kinh nghiệm\""
        : "Đã phân tích xong — sửa lại nếu cần rồi bấm \"Lưu bài học kinh nghiệm\"",
      message.type === "notes_updated" ? "success" : "error");
      return;
    }
    if (message.type === "error") {
      setStreaming(false);
      streamContentRef.current = "";
      setStreamContent("");
      setNotesBusy(false);
      toast(`Lỗi: ${message.message}`, "error");
    }
  }, [toast]);

  const socket = useWebSocket<TrainingSocketMessage>({
    path: "/ws/training",
    enabled: selected !== null && !selected.closed,
    connectionKey: selected?.id ?? null,
    onMessage: onSocketMessage,
    onClose: () => setStreaming(false),
  });

  useEffect(() => {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight });
  }, [messages, streamContent, toolResults]);

  const patchSession = async (body: Record<string, unknown>, success = "Đã lưu") => {
    if (!selected) return;
    const updated = await apiClient.patch<TrainingSession>(`/training/sessions/${selected.id}`, body);
    setSelected((current) => current ? { ...current, ...body, ...updated } : current);
    await loadSessions();
    if (success) toast(success, "success");
  };

  const sendMessage = () => {
    if (!selected || !socket.isOpen || streaming || attachments.some((item) => item.uploading)) return;
    const text = input.trim() + buildAttachmentBlock(attachments);
    if (!text.trim()) return;
    setMessages((current) => [...current, { role: "user", content: text }]);
    setInput("");
    setAttachments([]);
    setStreaming(true);
    streamContentRef.current = "";
    setStreamContent("");
    socket.send({ training_session_id: selected.id, message: text });
    if (streamTimerRef.current !== null) window.clearTimeout(streamTimerRef.current);
    streamTimerRef.current = window.setTimeout(() => setStreaming(false), 90_000);
  };

  const attachFiles = async (files: FileList | null) => {
    for (const file of Array.from(files ?? [])) {
      const placeholder: ChatAttachment = { name: file.name, mime: file.type, uploading: true };
      setAttachments((current) => [...current, placeholder]);
      try {
        const uploaded = await uploadAttachment(file);
        setAttachments((current) => current.map((item) => item === placeholder ? uploaded : item));
      } catch (error) {
        setAttachments((current) => current.filter((item) => item !== placeholder));
        toast(`Không tải lên được ${file.name}: ${messageFromError(error, "lỗi không xác định")}`, "error");
      }
    }
  };

  const createSession = async () => {
    if (!newTitle.trim()) return;
    const session = await apiClient.post<TrainingSession>("/training/sessions", {
      title: newTitle.trim(),
      task_description: newTask.trim(),
      agent_id: newAgent ? Number(newAgent) : null,
      project_id: newProject ? Number(newProject) : null,
    });
    setSessionModal(false);
    setNewTitle(""); setNewTask(""); setNewAgent(""); setNewProject("");
    await loadSessions();
    await selectSession(session.id);
    toast("Đã tạo phiên dạy học mới", "success");
  };

  const setStatus = async (status: "pass" | "fail") => {
    if (!selected) return;
    await patchSession({ status }, "");
    if (selected.agent_id) {
      setNotesBusy(true);
      try {
        const data = await apiClient.post<DistillResponse>(`/training/sessions/${selected.id}/distill`);
        setSelected((current) => current ? { ...current, result_notes: data.notes ?? "" } : current);
        toast(data.lessons?.length
          ? `Đã đúc kết ${data.lessons.length} bài học — kiểm tra phạm vi ở đầu mỗi dòng rồi bấm \"Lưu bài học kinh nghiệm\"`
          : "Chưa rút được bài học nào — bạn có thể tự viết vào ô đúc kết", "success");
      } catch (error) {
        toast(messageFromError(error, "Không đúc kết được"), "error");
      } finally {
        setNotesBusy(false);
      }
    } else if (socket.isOpen) {
      setNotesBusy(true);
      socket.send({ action: status === "pass" ? "summarise_pass" : "summarise_fail", session_id: selected.id });
      toast(status === "pass" ? "Đã ghi nhận — đang đúc kết bài học..." : "Đã ghi nhận — đang phân tích để cải thiện...", status === "pass" ? "success" : "error");
    }
  };

  const closeLesson = async () => {
    if (!selected) return;
    try {
      const data = await apiClient.post<CloseResponse>(`/training/sessions/${selected.id}/close`, { notes: selected.result_notes });
      await loadSessions();
      await selectSession(selected.id);
      const counts = data.written_by_scope ?? {};
      const parts: string[] = [];
      if (counts.agent) parts.push(`${counts.agent} vào soul ${data.agent_name}`);
      if (counts.project) parts.push(`${counts.project} vào soul dự án ${data.project_name}`);
      if (counts.skill) parts.push(`${counts.skill} vào phụ lục kỹ năng`);
      toast(parts.length ? `Đã ghi ${parts.join(", ")} — buổi học đã đóng` : "Đã đóng buổi học", "success");
    } catch (error) {
      toast(messageFromError(error, "Không đóng được buổi học"), "error");
    }
  };

  const reopenLesson = async () => {
    if (!selected) return;
    await apiClient.post(`/training/sessions/${selected.id}/reopen`);
    await loadSessions();
    await selectSession(selected.id);
    toast("Đã mở lại buổi học", "success");
  };

  const saveTools = async (next: string[]) => {
    setAllowedTools(next);
    await patchSession({ allowed_tools: next }, "");
    toast(next.length ? `Học viên được dùng ${next.length} công cụ thật trong buổi này` : "Đã thu lại hết công cụ — học viên chỉ nói chuyện", "success");
  };

  const tagLine = (label: "nhân viên" | "dự án" | "kỹ năng") => {
    if (!selected || !notesRef.current) return;
    const value = selected.result_notes ?? "";
    const position = notesRef.current.selectionStart;
    const lines = value.split("\n");
    let index = 0;
    let seen = 0;
    while (index < lines.length && seen + lines[index].length < position) {
      seen += lines[index].length + 1;
      index += 1;
    }
    index = Math.min(index, lines.length - 1);
    const body = lines[index].replace(/^\s*(?:[-*•]|\d+[.)])?\s*(?:\[[^\]]{1,60}\]\s*)?/, "");
    if (!body.trim()) { toast("Đặt con trỏ vào dòng bài học rồi bấm", "error"); return; }
    lines[index] = `[${label}] ${body}`;
    const result_notes = lines.join("\n");
    setSelected({ ...selected, result_notes });
    void patchSession({ result_notes }, "");
  };

  const submitFeedback = () => {
    if (!selected || !socket.isOpen) { toast("Chưa kết nối WebSocket", "error"); return; }
    setFeedbackModal(false);
    setNotesBusy(true);
    socket.send(feedback.trim()
      ? { action: "improve_from_fail", session_id: selected.id, feedback: feedback.trim() }
      : { action: "summarise_pass", session_id: selected.id });
    toast(feedback.trim() ? "Đang đúc kết từ góp ý..." : "Đang đúc kết tự động...");
  };

  const deleteSession = async () => {
    if (!selected) return;
    await apiClient.delete(`/training/sessions/${selected.id}`);
    setConfirmDelete(false);
    setSelected(null);
    setMessages([]);
    await loadSessions();
    toast("Đã xoá session", "success");
  };

  const logout = async () => {
    await sessionApi.logout();
    navigate("/v2/login", { replace: true });
  };

  const connectionText = useMemo(() => {
    if (socket.state === "open") return "";
    if (socket.reconnectAttempt) return `Mất kết nối — thử lại... (${socket.reconnectAttempt}/5)`;
    return "Hermes offline — không thể gửi tin nhắn";
  }, [socket.reconnectAttempt, socket.state]);

  const isClosed = Boolean(selected?.closed);
  const currentStudent = selected?.agent_id ? selected.agent_name || `#${selected.agent_id}` : null;
  const currentProject = selected?.project_id ? selected.project_name || `#${selected.project_id}` : null;

  return (
    <>
      <header className={c("topbar")}>
        <span className={c("topbar-logo")}><span className={c("dot")} />Xanax</span>
        <nav className={c("topbar-nav")}>
          <a className={c("active")} href="/v2/workspace">Training</a>
          <a href="/taskrunner">Quy trình</a>
        </nav>
        <div className={c("topbar-user")}><span>{user?.username ?? "—"}</span><button className={c("btn-logout")} onClick={() => void logout()}>Đăng xuất</button></div>
      </header>

      <main className={c("workspace")} data-testid="workspace-page">
        <aside className={c("sessions-panel")}>
          <div className={c("sessions-header")}><h2>Phiên dạy học AI</h2><button data-testid="new-session" className={c("btn-new")} onClick={() => { void loadRosters(); setSessionModal(true); }} title="Tạo phiên dạy học mới">+</button></div>
          <div className={c("sessions-list")}>
            {!sessions.length ? <div className={c("empty-list")}>Chưa có session nào.<br />Nhấn <strong>+</strong> để tạo mới.</div> : sessions.map((session) => (
              <button type="button" key={session.id} data-session-id={session.id} className={cx(c("session-item"), session.id === selected?.id && c("active"))} onClick={() => void selectSession(session.id)}>
                <span className={cx(c("session-dot"), c(`dot-${session.status}`))} />
                <span className={c("session-info")}><span className={c("session-title")}>{session.title}</span><span className={c("session-meta")}>{session.agent_name ? `👤 ${session.agent_name} · ` : ""}{fmtDate(session.created_at)}</span></span>
              </button>
            ))}
          </div>
        </aside>

        <section className={c("chat-panel")}>
          {selected && socket.state !== "open" && !isClosed ? <div className={cx(c("hermes-banner"), c("visible"))}><Icon name="warning" className={c("icon")} size={16} /> {connectionText}</div> : null}
          {!selected ? <div className={c("chat-empty")}><div className={c("chat-empty-icon")}><Icon name="chat" className={c("icon")} size={40} /></div><h3>Chưa chọn Phiên Dạy Học</h3><p>Chọn một phiên dạy học bên trái hoặc tạo mới để bắt đầu hướng dẫn trợ lý AI.</p></div> : (
            <>
              <div className={c("chat-messages")} ref={messagesRef}>
                {messages.map((message, index) => <ChatMessage key={message.id ?? `${message.role}-${index}`} message={message} />)}
                {(streaming || streamContent) ? <div className={cx(c("msg"), c("msg-assistant"))}><div className={c("msg-avatar")}><Icon name="bot" className={c("icon")} /></div><div className={c("msg-bubble")}>{streamContent ? <Markdown content={streamContent} streaming /> : <Typing />}</div></div> : null}
                {toolResults.length ? <div className={cx(c("msg"), c("msg-tool"))}><div className={c("msg-avatar")}><Icon name="bolt" className={c("icon")} /></div><div className={cx(c("msg-bubble"), c("tool-results"))}>{toolResults.map((result, index) => <div key={`${result.action}-${index}`} className={cx(c("tool-result-item"), c(result.ok ? "ok" : "err"))}><Icon name={result.ok ? "check" : "close"} className={c("icon")} size={14} /> <strong>{result.action}</strong>: {result.message || result.error || ""}</div>)}</div></div> : null}
              </div>
              {!isClosed ? <div className={c("chat-input-area")}>
                {attachments.length ? <div className={c("chat-attach-bar")}>{attachments.map((item, index) => <span key={`${item.name}-${index}`} className={cx(c("chat-attach-chip"), item.uploading && c("uploading"))}>{item.uploading ? "Đang tải " : "📎 "}{item.name}<button type="button" aria-label={`Bỏ ${item.name}`} onClick={() => setAttachments((current) => current.filter((_, itemIndex) => itemIndex !== index))}>×</button></span>)}</div> : null}
                <div className={c("chat-input-row")}>
                  <label className={c("btn-attach")} title="Đính kèm ảnh hoặc file"><Icon name="link" /><input type="file" multiple hidden onChange={(event) => { void attachFiles(event.target.files); event.target.value = ""; }} /></label>
                  <textarea data-testid="chat-input" className={c("chat-input")} value={input} placeholder="Nhắn tin hướng dẫn trợ lý AI..." rows={1} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } }} />
                  <button data-testid="send-message" className={c("btn-send")} onClick={sendMessage} disabled={!socket.isOpen || streaming || attachments.some((item) => item.uploading)}><Icon name="send" /></button>
                </div>
              </div> : null}
            </>
          )}
        </section>

        <aside className={c("info-panel")}>
          {!selected ? <div className={c("info-empty")}>Chọn phiên dạy học bên trái để xem thông tin</div> : <div className={cx(c("info-content"), c("visible"))}>
            <InfoLabel>Tên phiên dạy học</InfoLabel>
            <input className={c("info-title-edit")} value={selected.title} onChange={(event) => setSelected({ ...selected, title: event.target.value })} onBlur={() => void patchSession({ title: selected.title })} />
            <Divider />
            <InfoLabel>Kết quả đánh giá</InfoLabel>
            <StatusBadge status={selected.status} />
            <div className={c("status-buttons")}><button className={cx(c("btn-status"), c("btn-pass"))} disabled={isClosed} onClick={() => void setStatus("pass")}><Icon name="check" className={c("icon")} size={15} /> Hài lòng</button><button className={cx(c("btn-status"), c("btn-fail"))} disabled={isClosed} onClick={() => void setStatus("fail")}><Icon name="close" className={c("icon")} size={15} /> Cần cải thiện</button></div>
            <Divider />
            <InfoLabel>Ngày tạo</InfoLabel><div className={c("info-date")}>{fmtDate(selected.created_at, true)}</div>
            <Divider />
            <InfoLabel>Yêu cầu nhiệm vụ huấn luyện</InfoLabel>
            <textarea className={c("info-task-edit")} value={selected.task_description ?? ""} onChange={(event) => setSelected({ ...selected, task_description: event.target.value })} onBlur={() => void patchSession({ task_description: selected.task_description })} placeholder="Mô tả chi tiết nhiệm vụ bạn muốn trợ lý AI học và thực hiện tốt..." />

            {selected.agent_id ? <><Divider /><InfoLabel>Công cụ cho buổi học này</InfoLabel><div className={c("student-tools")}>
              {tools.length ? tools.map((tool) => <label key={tool.name} className={c("student-tool")} title={tool.description}><input type="checkbox" checked={allowedTools.includes(tool.name)} disabled={isClosed} onChange={(event) => void saveTools(event.target.checked ? [...allowedTools, tool.name] : allowedTools.filter((name) => name !== tool.name))} /><span>{tool.name}</span></label>) : <span className={c("student-tools-msg")}>{toolsNote || "Học viên này chưa có công cụ nào để cấp. Kỹ năng loại custom không sinh ra công cụ; chỉ skill loại api / builtin / mcp mới có."}</span>}
              <div className={c("student-tools-warn")}>Công cụ tick ở đây chạy THẬT trong buổi học — không phải mô phỏng. Không tick gì thì học viên chỉ nói chuyện, không làm được việc thật.</div>
            </div></> : null}

            <Divider />
            <InfoLabel>Bài học ghi nhớ (Đúc kết) {notesBusy ? <span className={c("notes-spinner")} /> : null}</InfoLabel>
            {currentStudent && !isClosed ? <div className={c("scope-bar")}><span className={c("scope-bar-label")}>Gắn phạm vi cho dòng đang sửa:</span><button className={cx(c("scope-chip"), c("scope-agent"))} onClick={() => tagLine("nhân viên")}>nhân viên</button><button className={cx(c("scope-chip"), c("scope-project"))} disabled={!currentProject} title={currentProject ? `Ghi vào soul dự án \"${currentProject}\"` : "Buổi dạy này không gắn dự án nào"} onClick={() => tagLine("dự án")}>dự án</button><button className={cx(c("scope-chip"), c("scope-skill"))} onClick={() => tagLine("kỹ năng")}>kỹ năng</button></div> : null}
            <textarea data-testid="result-notes" ref={notesRef} className={cx(c("notes-edit"), selected.result_notes && c("has-content"))} value={selected.result_notes ?? ""} readOnly={isClosed} onChange={(event) => setSelected({ ...selected, result_notes: event.target.value })} onBlur={() => void patchSession({ result_notes: selected.result_notes })} placeholder="Bấm 'Hài lòng' hoặc 'Cần cải thiện' để AI đúc kết bản nháp vào đây. Sửa thoải mái — mỗi dòng là một bài học." />
            {currentStudent && !isClosed ? <div className={c("field-hint")}><strong>nhân viên</strong> → chỉ {currentStudent} nhớ · {currentProject ? <><strong>dự án</strong> → mọi nhân viên làm cho “{currentProject}” đều nhớ · </> : null}<strong>kỹ năng</strong> → ai dùng kỹ năng đó cũng nhớ. Dòng không gắn thẻ mặc định là của riêng nhân viên.</div> : null}
            <div className={c("field-hint")}>{currentStudent ? `Sửa xong phần đúc kết rồi bấm nút dưới — mỗi dòng thành một bài học trong soul của ${currentStudent}, và buổi học mới đóng.` : "Sửa xong phần đúc kết rồi bấm nút dưới để chốt và đóng buổi học."}</div>
            <button data-testid="close-lesson" className={cx(c("btn-feedback"), c("visible"))} disabled={isClosed} onClick={() => void closeLesson()}><Icon name="save" className={c("icon")} size={15} /> Lưu bài học kinh nghiệm</button>
            {isClosed ? <button data-testid="reopen-lesson" className={c("btn-reopen")} onClick={() => void reopenLesson()}>Mở lại buổi học để sửa tiếp</button> : null}
            <button className={c("btn-refine")} disabled={isClosed} onClick={() => { setFeedback(""); setFeedbackModal(true); }}>Nhờ AI đúc kết lại từ góp ý</button>
            <Divider />
            <button className={c("btn-delete-session")} onClick={() => setConfirmDelete(true)}>Xoá phiên dạy học này</button>
          </div>}
        </aside>
      </main>

      <footer className={c("page-footer")}>© 2025 Xanax — Personal AI Agent</footer>

      <Modal visible={sessionModal} className="modal-overlay" onBackdrop={() => setSessionModal(false)}><div className={c("modal")}><h3><Icon name="chat" className={c("icon")} size={15} /> Tạo Phiên Dạy Học Mới</h3><input value={newTitle} maxLength={100} autoFocus onChange={(event) => setNewTitle(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void createSession(); }} placeholder="Tên phiên dạy học" /><label className={c("field-label")} htmlFor="new-agent">Học viên của buổi dạy</label><select id="new-agent" value={newAgent} onChange={(event) => setNewAgent(event.target.value)}><option value="">Dạy chính Xanax (như trước)</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}{agent.role ? ` — ${agent.role}` : ""}</option>)}</select><div className={c("field-hint")}>Mỗi phòng dạy đúng một nhân viên. Chọn xong không đổi được.</div><label className={c("field-label")} htmlFor="new-project">Dự án của buổi dạy</label><select id="new-project" value={newProject} onChange={(event) => setNewProject(event.target.value)}><option value="">Không gắn dự án nào</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select><textarea value={newTask} onChange={(event) => setNewTask(event.target.value)} placeholder="Mô tả yêu cầu nhiệm vụ huấn luyện (không bắt buộc)" /><div className={c("modal-footer")}><button className={c("btn-cancel")} onClick={() => setSessionModal(false)}>Huỷ</button><button className={c("btn-create")} onClick={() => void createSession()}>Tạo phiên</button></div></div></Modal>

      <Modal visible={feedbackModal} className="fp-overlay" onBackdrop={() => setFeedbackModal(false)}><div className={c("fp-box")}><div className={c("fp-title")}><Icon name="chat" className={c("icon")} size={15} /> Góp ý để Trợ lý AI cải thiện</div><div className={c("fp-hint")}>Nhập <strong>góp ý / hướng dẫn cụ thể</strong> để trợ lý AI ghi nhớ. Để trống để trợ lý tự đúc kết từ cuộc đối thoại.</div><textarea className={c("fp-textarea")} value={feedback} autoFocus onChange={(event) => setFeedback(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && event.ctrlKey) submitFeedback(); }} /><div className={c("fp-footer")}><button className={c("fp-btn-cancel")} onClick={() => setFeedbackModal(false)}>Huỷ</button><button className={c("fp-btn-submit")} onClick={submitFeedback}>Xác nhận</button></div></div></Modal>

      <Modal visible={confirmDelete} className="cp-overlay" onBackdrop={() => setConfirmDelete(false)}><div className={c("cp-box")}><div className={c("cp-title")}><Icon name="warning" className={c("icon")} size={15} /> Xác nhận xoá</div><div className={c("cp-body")}>Xoá session này? Hành động không thể hoàn tác.</div><div className={c("cp-footer")}><button className={c("cp-btn-cancel")} onClick={() => setConfirmDelete(false)}>Huỷ</button><button className={c("cp-btn-confirm")} onClick={() => void deleteSession()}>Xoá</button></div></div></Modal>

      <div className={cx(c("toast"), toastState.text && c("show"), toastState.kind && c(toastState.kind))}>{toastState.text}</div>
    </>
  );
}

function Divider() { return <div className={c("info-divider")} />; }
function InfoLabel({ children }: { children: React.ReactNode }) { return <div className={c("info-section-label")}>{children}</div>; }

function StatusBadge({ status }: { status: TrainingSession["status"] }) {
  const content = status === "pass" ? <><Icon name="check" className={c("icon")} size={14} /> Đạt</> : status === "fail" ? <><Icon name="close" className={c("icon")} size={14} /> Không đạt</> : <><span className={cx(c("sdot"), c("on"))} />Đang thực hiện</>;
  return <span className={cx(c("status-badge"), c(`status-${status}`))}>{content}</span>;
}

function ChatMessage({ message }: { message: Message }) {
  const user = message.role === "user";
  return <div className={cx(c("msg"), c(user ? "msg-user" : "msg-assistant"))}><div className={c("msg-avatar")}>{user ? "P" : <Icon name="bot" className={c("icon")} />}</div><div className={c("msg-bubble")}><Markdown content={message.content} /></div></div>;
}

function Typing() { return <div className={c("typing-indicator")}><span /><span /><span /></div>; }

function Modal({ visible, className, onBackdrop, children }: { visible: boolean; className: string; onBackdrop: () => void; children: React.ReactNode }) {
  if (!visible) return null;
  return <div className={cx(c(className), c("visible"))} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onBackdrop(); }}>{children}</div>;
}
