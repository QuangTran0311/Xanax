import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient } from "../../api/client";
import { buildAttachmentBlock, uploadAttachment, type ChatAttachment } from "../../components/ChatAttach";
import { Icon } from "../../components/Icon";
import { Markdown } from "../../components/Markdown";
import { enqueueToast, type ToastKind } from "../../components/Toast";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useWorkspaceText } from "../../i18n/workspace";
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
interface ToolsResponse { tools: ToolOption[]; allowed: string[] }
interface DistillResponse { notes?: string; lessons?: unknown[] }
interface CloseResponse {
  written_by_scope?: { agent?: number; project?: number; skill?: number };
  agent_name?: string;
  project_name?: string;
}

function fmtDate(value: string | undefined, locale: string, full = false): string {
  if (!value) return "—";
  const normalized = value.endsWith("Z") ? value : `${value}Z`;
  return full
    ? new Date(normalized).toLocaleString(locale)
    : new Date(normalized).toLocaleDateString(locale);
}

function messageFromError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function WorkspacePage({ embedded = false }: { embedded?: boolean }) {
  const navigate = useNavigate();
  const t = useWorkspaceText();
  const tt = useTooltipText();
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
  const [notesBusy, setNotesBusy] = useState(false);
  const [sessionModal, setSessionModal] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newTask, setNewTask] = useState("");
  const [newAgent, setNewAgent] = useState("");
  const [newProject, setNewProject] = useState("");
  const messagesRef = useRef<HTMLDivElement>(null);
  const notesRef = useRef<HTMLTextAreaElement>(null);
  const streamTimerRef = useRef<number | null>(null);
  const streamContentRef = useRef("");
  const attachmentPreviewUrlsRef = useRef(new Set<string>());

  const toast = useCallback((text: string, kind: ToastKind = "info") => {
    enqueueToast(text, kind);
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
      .catch(() => navigate("/login", { replace: true }));
    return () => window.removeEventListener("storage", onStorage);
  }, [loadRosters, loadSessions, navigate]);

  useEffect(() => () => {
    attachmentPreviewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    attachmentPreviewUrlsRef.current.clear();
  }, []);

  useEffect(() => {
    const idleMs = 15 * 60 * 1000;
    let idleTimer = 0;
    const reset = () => {
      window.clearTimeout(idleTimer);
      idleTimer = window.setTimeout(() => {
        if (streaming) { reset(); return; }
        void sessionApi.logout().finally(() => navigate("/login?reason=idle", { replace: true }));
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
      setTools([]); setAllowedTools([]);
      return;
    }
    try {
      const data = await apiClient.get<ToolsResponse>(`/training/sessions/${session.id}/tools`);
      setTools(data.tools ?? []);
      setAllowedTools(data.allowed ?? []);
    } catch {
      setTools([]);
      setAllowedTools([]);
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
        ? t("toast.notes_updated")
        : t("toast.failure_analysed"),
      message.type === "notes_updated" ? "success" : "error");
      return;
    }
    if (message.type === "error") {
      setStreaming(false);
      streamContentRef.current = "";
      setStreamContent("");
      setNotesBusy(false);
      toast(t("toast.socket_error", message.message), "error");
    }
  }, [t, toast]);

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

  const patchSession = async (body: Record<string, unknown>, success?: string) => {
    if (!selected) return;
    const updated = await apiClient.patch<TrainingSession>(`/training/sessions/${selected.id}`, body);
    setSelected((current) => current ? { ...current, ...body, ...updated } : current);
    await loadSessions();
    const successMessage = success === undefined ? t("toast.saved") : success;
    if (successMessage) toast(successMessage, "success");
  };

  const sendMessage = () => {
    if (!selected || !socket.isOpen || streaming || attachments.some((item) => item.uploading)) return;
    const text = input.trim() + buildAttachmentBlock(attachments);
    if (!text.trim()) return;
    setMessages((current) => [...current, { role: "user", content: text }]);
    setInput("");
    attachments.forEach((item) => {
      if (!item.preview_url) return;
      URL.revokeObjectURL(item.preview_url);
      attachmentPreviewUrlsRef.current.delete(item.preview_url);
    });
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
      const previewUrl = file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined;
      if (previewUrl) attachmentPreviewUrlsRef.current.add(previewUrl);
      const placeholder: ChatAttachment = { name: file.name, mime: file.type, uploading: true, preview_url: previewUrl };
      setAttachments((current) => [...current, placeholder]);
      try {
        const uploaded = await uploadAttachment(file);
        setAttachments((current) => current.map((item) => item === placeholder ? { ...uploaded, preview_url: previewUrl } : item));
      } catch (error) {
        if (previewUrl) {
          URL.revokeObjectURL(previewUrl);
          attachmentPreviewUrlsRef.current.delete(previewUrl);
        }
        setAttachments((current) => current.filter((item) => item !== placeholder));
        toast(t("toast.upload_failed", file.name, messageFromError(error, t("toast.unknown_error"))), "error");
      }
    }
  };

  const removeAttachment = (attachment: ChatAttachment) => {
    if (attachment.preview_url) {
      URL.revokeObjectURL(attachment.preview_url);
      attachmentPreviewUrlsRef.current.delete(attachment.preview_url);
    }
    setAttachments((current) => current.filter((item) => item !== attachment));
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
    toast(t("toast.session_created"), "success");
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
          ? t("toast.lessons_distilled", data.lessons.length)
          : t("toast.no_lessons"), "success");
      } catch (error) {
        toast(messageFromError(error, t("toast.distill_failed")), "error");
      } finally {
        setNotesBusy(false);
      }
    } else if (socket.isOpen) {
      setNotesBusy(true);
      socket.send({ action: status === "pass" ? "summarise_pass" : "summarise_fail", session_id: selected.id });
      toast(status === "pass" ? t("toast.pass_recorded") : t("toast.fail_recorded"), status === "pass" ? "success" : "error");
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
      if (counts.agent) parts.push(t("toast.written_agent", counts.agent, data.agent_name ?? ""));
      if (counts.project) parts.push(t("toast.written_project", counts.project, data.project_name ?? ""));
      if (counts.skill) parts.push(t("toast.written_skill", counts.skill));
      toast(parts.length ? t("toast.lesson_closed_with_writes", parts.join(", ")) : t("toast.lesson_closed"), "success");
    } catch (error) {
      toast(messageFromError(error, t("toast.close_failed")), "error");
    }
  };

  const reopenLesson = async () => {
    if (!selected) return;
    await apiClient.post(`/training/sessions/${selected.id}/reopen`);
    await loadSessions();
    await selectSession(selected.id);
    toast(t("toast.lesson_reopened"), "success");
  };

  const saveTools = async (next: string[]) => {
    setAllowedTools(next);
    await patchSession({ allowed_tools: next }, "");
    toast(next.length ? t("toast.tools_allowed", next.length) : t("toast.tools_revoked"), "success");
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
    if (!body.trim()) { toast(t("toast.scope_cursor"), "error"); return; }
    lines[index] = `[${label}] ${body}`;
    const result_notes = lines.join("\n");
    setSelected({ ...selected, result_notes });
    void patchSession({ result_notes }, "");
  };

  const deleteSession = async () => {
    if (!selected) return;
    await apiClient.delete(`/training/sessions/${selected.id}`);
    setConfirmDelete(false);
    setSelected(null);
    setMessages([]);
    await loadSessions();
    toast(t("toast.session_deleted"), "success");
  };

  const logout = async () => {
    await sessionApi.logout();
    navigate("/login", { replace: true });
  };

  const connectionText = useMemo(() => {
    if (socket.state === "open") return "";
    if (socket.reconnectAttempt) return t("connection.retrying", socket.reconnectAttempt);
    return t("connection.offline");
  }, [socket.reconnectAttempt, socket.state, t]);

  const isClosed = Boolean(selected?.closed);
  const currentStudent = selected?.agent_id ? selected.agent_name || `#${selected.agent_id}` : null;
  const currentProject = selected?.project_id ? selected.project_name || `#${selected.project_id}` : null;

  return (
    <div className={cx(c("workspace-page-root"), embedded && c("workspace-page-embedded"))}>
      {!embedded ? <header className={c("topbar")}>
        <span className={c("topbar-logo")}><span className={c("dot")} />Xanax</span>
        <nav className={c("topbar-nav")}>
          <a className={c("active")} href="/workspace">{t("nav.training")}</a>
          <a href="/taskrunner">{t("nav.workflows")}</a>
        </nav>
        <div className={c("topbar-user")}><span>{user?.username ?? "—"}</span><Tooltip label={tt("tooltip.workspace.logout")}><button className={c("btn-logout")} onClick={() => void logout()}>{t("common.logout")}</button></Tooltip></div>
      </header> : null}

      <main className={c("workspace")} data-testid="workspace-page">
        <aside className={c("sessions-panel")}>
          <div className={c("sessions-header")}><h2>{t("sessions.title")}</h2><Tooltip label={tt("tooltip.workspace.create_session")}><button data-testid="new-session" className={c("btn-new")} aria-label={tt("tooltip.workspace.create_session")} onClick={() => { void loadRosters(); setSessionModal(true); }}>+</button></Tooltip></div>
          <div className={c("sessions-list")}>
            {!sessions.length ? <div className={c("empty-list")}>{t("sessions.empty")}<br />{t("sessions.empty_action_before")} <strong>+</strong> {t("sessions.empty_action_after")}</div> : sessions.map((session) => (
              <Tooltip key={session.id} label={tt("tooltip.workspace.select_session")}><button type="button" data-session-id={session.id} className={cx(c("session-item"), session.id === selected?.id && c("active"))} onClick={() => void selectSession(session.id)}>
                <span className={cx(c("session-dot"), c(`dot-${session.status}`))} />
                <span className={c("session-info")}><span className={c("session-title")}>{session.title}</span></span>
              </button></Tooltip>
            ))}
          </div>
        </aside>

        <section className={c("chat-panel")}>
          {selected && socket.state !== "open" && !isClosed ? <div className={cx(c("hermes-banner"), c("visible"))}><Icon name="warning" className={c("icon")} size={16} /> {connectionText}</div> : null}
          {!selected ? <div className={c("chat-empty")}><div className={c("chat-empty-icon")}><Icon name="chat" className={c("icon")} size={40} /></div><h3>{t("chat.empty_title")}</h3><p>{t("chat.empty_description")}</p></div> : (
            <>
              <div className={c("chat-messages")} ref={messagesRef}>
                {messages.map((message, index) => <ChatMessage key={message.id ?? `${message.role}-${index}`} message={message} />)}
                {(streaming || streamContent) ? <div className={cx(c("msg"), c("msg-assistant"))}><div className={c("msg-avatar")}><Icon name="bot" className={c("icon")} /></div><div className={c("msg-bubble")}>{streamContent ? <Markdown content={streamContent} streaming /> : <Typing />}</div></div> : null}
                {toolResults.length ? <div className={cx(c("msg"), c("msg-tool"))}><div className={c("msg-avatar")}><Icon name="bolt" className={c("icon")} /></div><div className={cx(c("msg-bubble"), c("tool-results"))}>{toolResults.map((result, index) => <div key={`${result.action}-${index}`} className={cx(c("tool-result-item"), c(result.ok ? "ok" : "err"))}><Icon name={result.ok ? "check" : "close"} className={c("icon")} size={14} /> <strong>{result.action}</strong>: {result.message || result.error || ""}</div>)}</div></div> : null}
              </div>
              {!isClosed ? <div className={c("chat-input-area")}>
                {attachments.length ? <div className={c("chat-attach-bar")}>{attachments.map((item, index) => {
                  const isImage = item.mime?.startsWith("image/") && item.preview_url;
                  return <span key={`${item.name}-${index}`} className={cx(c("chat-attach-chip"), item.uploading && c("uploading"))}>
                    {isImage ? <span className={c("chat-attach-preview")}>
                      <img src={item.preview_url} alt={t("chat.preview_alt", item.name)} />
                      {item.uploading ? <span className={c("chat-attach-loading")} role="status" aria-label={t("chat.uploading_aria", item.name)} /> : null}
                    </span> : item.uploading
                      ? <span className={c("chat-attach-loading")} role="status" aria-label={t("chat.uploading_aria", item.name)} />
                      : <span className={c("chat-attach-icon")} aria-hidden="true">📎</span>}
                    <span className={c("chat-attach-name")}>{item.name}</span>
                    <Tooltip label={tt("tooltip.workspace.remove_attachment")}><button type="button" aria-label={t("chat.remove_aria", item.name)} onClick={() => removeAttachment(item)}>×</button></Tooltip>
                  </span>;
                })}</div> : null}
                <div className={c("chat-input-row")}>
                  <Tooltip label={tt("tooltip.workspace.attach")}><label className={c("btn-attach")} aria-label={tt("tooltip.workspace.attach")}><Icon name="link" /><input type="file" multiple hidden onChange={(event) => { void attachFiles(event.target.files); event.target.value = ""; }} /></label></Tooltip>
                  <textarea data-testid="chat-input" className={c("chat-input")} value={input} placeholder={t("chat.input_placeholder")} rows={1} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } }} />
                  <Tooltip label={tt("tooltip.workspace.send")}><button data-testid="send-message" className={c("btn-send")} aria-label={tt("tooltip.workspace.send")} onClick={sendMessage} disabled={!socket.isOpen || streaming || attachments.some((item) => item.uploading)}><Icon name="send" /></button></Tooltip>
                </div>
              </div> : null}
            </>
          )}
        </section>

        <aside className={c("info-panel")}>
          {!selected ? <div className={c("info-empty")}>{t("info.empty")}</div> : <div className={cx(c("info-content"), c("visible"))}>
            <div className={c("info-heading")}>
              <input className={c("info-title-edit")} value={selected.title} onChange={(event) => setSelected({ ...selected, title: event.target.value })} onBlur={() => void patchSession({ title: selected.title })} />
              <div className={c("info-meta")}>{[
                currentStudent ? `👤 ${currentStudent}` : null,
                currentProject ? `📁 ${currentProject}` : null,
                selected.created_at ? fmtDate(selected.created_at, t("common.locale"), true) : null,
              ].filter(Boolean).join(" · ")}</div>
            </div>
            <Divider />
            <div className={c("info-section")}>
              <InfoLabel>{t("info.evaluation")}</InfoLabel>
              <div className={c("status-buttons")}><Tooltip label={tt("tooltip.workspace.pass")}><button className={cx(c("btn-status"), c("btn-pass"), selected.status === "pass" && c("btn-status-selected"))} disabled={isClosed} onClick={() => void setStatus("pass")}>{selected.status === "pass" ? <Icon name="check" className={c("icon")} size={14} /> : null} {t("info.pass")}</button></Tooltip><Tooltip label={tt("tooltip.workspace.fail")}><button className={cx(c("btn-status"), c("btn-fail"), selected.status === "fail" && c("btn-status-selected"))} disabled={isClosed} onClick={() => void setStatus("fail")}>{selected.status === "fail" ? <Icon name="check" className={c("icon")} size={14} /> : null} {t("info.fail")}</button></Tooltip></div>
            </div>
            <div className={c("info-section")}>
              <InfoLabel>{t("info.task")}</InfoLabel>
              <textarea className={c("info-task-edit")} value={selected.task_description ?? ""} onChange={(event) => setSelected({ ...selected, task_description: event.target.value })} onBlur={() => void patchSession({ task_description: selected.task_description })} placeholder={t("info.task_placeholder")} />
            </div>

            {selected.agent_id && tools.length ? <div className={c("info-section")}><InfoLabel>{t("info.tools")}</InfoLabel><div className={c("student-tools")}>
              {tools.map((tool) => <label key={tool.name} className={c("student-tool")} title={tool.description}><input type="checkbox" checked={allowedTools.includes(tool.name)} disabled={isClosed} onChange={(event) => void saveTools(event.target.checked ? [...allowedTools, tool.name] : allowedTools.filter((name) => name !== tool.name))} /><span>{tool.name}</span></label>)}
            </div></div> : null}

            <div className={c("info-section")}>
              <InfoLabel primary>{t("notes.title")} {notesBusy ? <span className={c("notes-spinner")} /> : null}</InfoLabel>
              {currentStudent && !isClosed ? <div className={c("scope-bar")}><span className={c("scope-bar-label")}>{t("notes.scope_label")}</span><Tooltip label={tt("tooltip.workspace.scope_agent", currentStudent)}><button className={cx(c("scope-chip"), c("scope-agent"))} onClick={() => tagLine("nhân viên")}>{t("notes.scope_agent")}</button></Tooltip><Tooltip label={currentProject ? tt("tooltip.workspace.scope_project", currentProject) : tt("tooltip.workspace.scope_project_unavailable")}><button className={cx(c("scope-chip"), c("scope-project"))} disabled={!currentProject} onClick={() => tagLine("dự án")}>{t("notes.scope_project")}</button></Tooltip><Tooltip label={tt("tooltip.workspace.scope_skill")}><button className={cx(c("scope-chip"), c("scope-skill"))} onClick={() => tagLine("kỹ năng")}>{t("notes.scope_skill")}</button></Tooltip></div> : null}
              <textarea data-testid="result-notes" ref={notesRef} className={cx(c("notes-edit"), selected.result_notes && c("has-content"))} value={selected.result_notes ?? ""} readOnly={isClosed} onChange={(event) => setSelected({ ...selected, result_notes: event.target.value })} onBlur={() => void patchSession({ result_notes: selected.result_notes })} placeholder={t("notes.placeholder")} />
              {currentStudent && !isClosed ? <div className={c("field-hint")}>{t("notes.hint")}</div> : null}
              <Tooltip label={tt("tooltip.workspace.close_lesson")}><button data-testid="close-lesson" className={cx(c("btn-feedback"), c("visible"))} disabled={isClosed} onClick={() => void closeLesson()}><Icon name="save" className={c("icon")} size={15} /> {t("notes.save")}</button></Tooltip>
              {isClosed ? <Tooltip label={tt("tooltip.workspace.reopen_lesson")}><button data-testid="reopen-lesson" className={c("btn-reopen")} onClick={() => void reopenLesson()}>{t("notes.reopen")}</button></Tooltip> : null}
            </div>
            <div className={c("info-footer")}>
              <Divider />
              <Tooltip label={tt("tooltip.workspace.delete_session")}><button className={c("btn-delete-session")} onClick={() => setConfirmDelete(true)}>{t("session.delete")}</button></Tooltip>
            </div>
          </div>}
        </aside>
      </main>

      {!embedded ? <footer className={c("page-footer")}>{t("footer.copyright", new Date().getFullYear())}</footer> : null}

      <Modal visible={sessionModal} className="modal-overlay" onBackdrop={() => setSessionModal(false)}><div className={c("modal")}><h3><Icon name="chat" className={c("icon")} size={15} /> {t("session.create_title")}</h3><input value={newTitle} maxLength={100} autoFocus onChange={(event) => setNewTitle(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void createSession(); }} placeholder={t("session.name_placeholder")} /><label className={c("field-label")} htmlFor="new-agent">{t("session.student_label")}</label><select id="new-agent" className={c("modal-select")} value={newAgent} onChange={(event) => setNewAgent(event.target.value)}><option value="">{t("session.student_xanax")}</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}{agent.role ? ` — ${agent.role}` : ""}</option>)}</select><div className={c("field-hint")}>{t("session.student_hint")}</div><label className={c("field-label")} htmlFor="new-project">{t("session.project_label")}</label><select id="new-project" className={c("modal-select")} value={newProject} onChange={(event) => setNewProject(event.target.value)}><option value="">{t("session.project_none")}</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select><textarea value={newTask} onChange={(event) => setNewTask(event.target.value)} placeholder={t("session.task_placeholder")} /><div className={c("modal-footer")}><Tooltip label={tt("tooltip.workspace.create_cancel")}><button className={c("btn-cancel")} onClick={() => setSessionModal(false)}>{t("common.cancel")}</button></Tooltip><Tooltip label={tt("tooltip.workspace.create_confirm")}><button className={c("btn-create")} onClick={() => void createSession()}>{t("session.create")}</button></Tooltip></div></div></Modal>

      <Modal visible={confirmDelete} className="cp-overlay" onBackdrop={() => setConfirmDelete(false)}><div className={c("cp-box")}><div className={c("cp-title")}><Icon name="warning" className={c("icon")} size={15} /> {t("delete.title")}</div><div className={c("cp-body")}>{t("delete.body")}</div><div className={c("cp-footer")}><Tooltip label={tt("tooltip.workspace.delete_cancel")}><button className={c("cp-btn-cancel")} onClick={() => setConfirmDelete(false)}>{t("common.cancel")}</button></Tooltip><Tooltip label={tt("tooltip.workspace.delete_confirm")}><button className={c("cp-btn-confirm")} onClick={() => void deleteSession()}>{t("common.delete")}</button></Tooltip></div></div></Modal>

    </div>
  );
}

function Divider() { return <div className={c("info-divider")} />; }
function InfoLabel({ children, primary = false }: { children: React.ReactNode; primary?: boolean }) {
  return <div className={c(primary ? "info-section-label-primary" : "info-section-label")}>{children}</div>;
}

function ChatMessage({ message }: { message: Message }) {
  const user = message.role === "user";
  return <div className={cx(c("msg"), c(user ? "msg-user" : "msg-assistant"))}><div className={c("msg-avatar")}>{user ? "P" : <Icon name="bot" className={c("icon")} />}</div><div className={c("msg-bubble")}><Markdown content={message.content} /></div></div>;
}

function Typing() { return <div className={c("typing-indicator")}><span /><span /><span /></div>; }

function Modal({ visible, className, onBackdrop, children }: { visible: boolean; className: string; onBackdrop: () => void; children: React.ReactNode }) {
  // Đóng bằng ESC cho cả ba popup của trang, giống hộp xem ảnh trong khung chat.
  useEffect(() => {
    if (!visible) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") onBackdrop(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [visible, onBackdrop]);

  if (!visible) return null;
  return <div className={cx(c(className), c("visible"))} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onBackdrop(); }}>{children}</div>;
}
