import { useEffect, useMemo, useReducer, useRef, useState } from "react";

import { apiClient } from "../../api/client";
import { buildAttachmentBlock, uploadAttachment, type ChatAttachment } from "../../components/ChatAttach";
import { Icon } from "../../components/Icon";
import { Markdown } from "../../components/Markdown";
import { useLanguage } from "../../store/language";
import { useWebSocket } from "../../ws/useWebSocket";
import { useHub } from "./HubContext";
import styles from "./HubPage.module.css";
import {
  emptyMeetingLiveState,
  reduceMeetingMessage,
  type ApprovalRequest,
  type ImageSourceRequest,
  type MeetingServerMessage,
} from "./meetingProtocol";
import type { MeetingRecord } from "./types";

const c = (name: string) => styles[name] ?? name;
type Proposal = {
  title: string;
  description: string;
  priority: string;
  suggested_agent_id?: number | null;
  assigned_agent_id?: number | null;
  match_reason?: string;
  include?: boolean;
};

function statusLabel(status: string | undefined, vi: boolean) {
  if (status === "active") return vi ? "Đang diễn ra" : "Active";
  if (status === "ended") return vi ? "Đã kết thúc" : "Ended";
  if (status === "finalized") return vi ? "Đã chốt" : "Finalized";
  return status || "—";
}

export function MeetingsPage() {
  const { language } = useLanguage();
  const vi = language === "vi";
  const { meetings, agents, projects, refreshMeetings, toast, confirm } = useHub();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", topic: "", projectId: "", participants: [] as number[] });
  const selected = meetings.find((meeting) => meeting.id === selectedId) || null;

  useEffect(() => {
    if (selectedId !== null && !meetings.some((meeting) => meeting.id === selectedId)) setSelectedId(null);
  }, [meetings, selectedId]);

  async function createMeeting() {
    if (!form.title.trim())
      return toast(vi ? "Cần nhập tên cuộc họp." : "Meeting title is required.", "error");
    try {
      const created = await apiClient.post<MeetingRecord>("/meetings/", {
        title: form.title.trim(),
        topic: form.topic.trim(),
        participants: form.participants,
        project_id: form.projectId ? Number(form.projectId) : null,
      });
      await refreshMeetings();
      setCreating(false);
      setSelectedId(created.id);
      setForm({ title: "", topic: "", projectId: "", participants: [] });
      toast(vi ? "Đã tạo cuộc họp." : "Meeting created.", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), "error");
    }
  }

  async function removeMeeting(meeting: MeetingRecord) {
    if (!(await confirm(vi ? `Xoá cuộc họp “${meeting.title}”?` : `Delete “${meeting.title}”?`))) return;
    try {
      await apiClient.delete(`/meetings/${meeting.id}`);
      if (selectedId === meeting.id) setSelectedId(null);
      await refreshMeetings();
      toast(vi ? "Đã xoá cuộc họp." : "Meeting deleted.", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), "error");
    }
  }

  return (
    <div className={c("page")}>
      <header className={c("pageHeader")}>
        <div>
          <h1>{vi ? "Phòng họp" : "Meeting room"}</h1>
          <p>
            {vi
              ? "Trao đổi cùng Xanax và nhân viên, theo dõi quy trình ngay trong cuộc họp."
              : "Talk with Xanax and staff, and follow workflow progress in the room."}
          </p>
        </div>
        <button className={c("primaryButton")} onClick={() => setCreating(true)}>
          <Icon name="meeting" />
          {vi ? "Cuộc họp mới" : "New meeting"}
        </button>
      </header>
      <div className={c("meetingLayout")}>
        <aside className={c("meetingList")} data-testid="meeting-list">
          {meetings.length ? (
            meetings.map((meeting) => (
              <div
                key={meeting.id}
                className={`${c("meetingListItem")} ${selectedId === meeting.id ? c("meetingListSelected") : ""}`}
              >
                <button onClick={() => setSelectedId(meeting.id)}>
                  <strong>{meeting.title}</strong>
                  <small>
                    {statusLabel(meeting.status, vi)} · {(meeting.participants || []).length}{" "}
                    {vi ? "nhân viên" : "staff"}
                  </small>
                  {meeting.project_id ? (
                    <span>
                      <Icon name="folder" />
                      {projects.find((project) => project.id === meeting.project_id)?.name ||
                        (vi ? "Dự án" : "Project")}
                    </span>
                  ) : null}
                </button>
                <button
                  className={c("meetingDelete")}
                  title={vi ? "Xoá" : "Delete"}
                  onClick={() => void removeMeeting(meeting)}
                >
                  <Icon name="trash" />
                </button>
              </div>
            ))
          ) : (
            <div className={c("empty")}>
              <Icon name="meeting" />
              {vi ? "Chưa có cuộc họp" : "No meetings yet"}
            </div>
          )}
        </aside>
        {selected ? (
          <MeetingRoom key={selected.id} meeting={selected} />
        ) : (
          <section className={c("meetingRoomEmpty")}>
            <Icon name="chat" />
            <span>{vi ? "Chọn hoặc tạo một cuộc họp" : "Select or create a meeting"}</span>
          </section>
        )}
      </div>
      {creating ? (
        <div
          className={c("modalBackdrop")}
          onMouseDown={(event) => event.target === event.currentTarget && setCreating(false)}
        >
          <section className={c("dialog")}>
            <header>
              <h2>{vi ? "Tạo cuộc họp" : "Create meeting"}</h2>
              <button onClick={() => setCreating(false)}>
                <Icon name="close" />
              </button>
            </header>
            <div className={c("dialogBody")}>
              <div className={c("formStack")}>
                <label className={c("field")}>
                  <span>{vi ? "Tên cuộc họp" : "Title"}</span>
                  <input
                    className={c("input")}
                    value={form.title}
                    onChange={(event) => setForm({ ...form, title: event.target.value })}
                    autoFocus
                  />
                </label>
                <label className={c("field")}>
                  <span>{vi ? "Chủ đề" : "Topic"}</span>
                  <textarea
                    className={c("textarea")}
                    rows={3}
                    value={form.topic}
                    onChange={(event) => setForm({ ...form, topic: event.target.value })}
                  />
                </label>
                <label className={c("field")}>
                  <span>{vi ? "Dự án liên kết" : "Linked project"}</span>
                  <select
                    className={c("select")}
                    value={form.projectId}
                    onChange={(event) => setForm({ ...form, projectId: event.target.value })}
                  >
                    <option value="">— {vi ? "Không gắn dự án" : "No project"} —</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                </label>
                <fieldset className={c("meetingPeoplePicker")}>
                  <legend>{vi ? "Người tham dự" : "Participants"}</legend>
                  {agents.map((agent) => (
                    <label key={agent.id}>
                      <input
                        type="checkbox"
                        checked={form.participants.includes(agent.id)}
                        onChange={() =>
                          setForm({
                            ...form,
                            participants: form.participants.includes(agent.id)
                              ? form.participants.filter((id) => id !== agent.id)
                              : [...form.participants, agent.id],
                          })
                        }
                      />
                      <span>{agent.name}</span>
                      <small>{agent.role}</small>
                    </label>
                  ))}
                </fieldset>
                <div className={c("formActions")}>
                  <span />
                  <div>
                    <button className={c("buttonGhost")} onClick={() => setCreating(false)}>
                      {vi ? "Huỷ" : "Cancel"}
                    </button>
                    <button className={c("primaryButton")} onClick={() => void createMeeting()}>
                      {vi ? "Tạo" : "Create"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function MeetingRoom({ meeting }: { meeting: MeetingRecord }) {
  const { language } = useLanguage();
  const vi = language === "vi";
  const { agents, projects, refreshMeetings, toast, confirm } = useHub();
  const [live, dispatch] = useReducer(reduceMeetingMessage, emptyMeetingLiveState);
  const [record, setRecord] = useState(meeting);
  const [content, setContent] = useState("");
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [mentionIndex, setMentionIndex] = useState(0);
  const [finalizing, setFinalizing] = useState(false);
  const [decision, setDecision] = useState(String(meeting.decision_text || meeting.draft_minutes || ""));
  const [proposals, setProposals] = useState<Proposal[]>(() =>
    (meeting.proposed_items || []).map((item) => ({
      ...(item as Proposal),
      include: true,
      assigned_agent_id: (item as Proposal).suggested_agent_id,
    })),
  );
  const messagesRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const participantIds = live.participantIds ?? record.participants ?? [];
  const participants = agents.filter((agent) => participantIds.includes(agent.id));
  const mention = /(?:^|\s)@([^\s@]*)$/.exec(content);
  const mentionCandidates = useMemo(
    () =>
      [
        { id: 0, name: "Xanax" },
        ...participants.map((agent) => ({ id: agent.id, name: agent.name || `Agent ${agent.id}` })),
      ].filter((candidate) => !mention || candidate.name.toLowerCase().includes(mention[1].toLowerCase())),
    [mention?.[1], participants],
  );

  useEffect(() => {
    setRecord(meeting);
    setDecision(String(meeting.decision_text || meeting.draft_minutes || ""));
  }, [meeting]);
  useEffect(() => {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight });
  }, [live]);
  useEffect(() => {
    if (live.endedDraft === null) return;
    const draft = live.endedDraft;
    setRecord((current) => ({ ...current, status: "ended", draft_minutes: draft }));
    setDecision(draft);
    setFinalizing(Boolean(draft));
    void refreshMeetings();
  }, [live.endedDraft, refreshMeetings]);
  useEffect(() => {
    if (live.error) toast(live.error, "error");
  }, [live.error, toast]);

  const socket = useWebSocket<MeetingServerMessage>({
    path: `/ws/meeting/${meeting.id}`,
    connectionKey: meeting.id,
    enabled: record.status === "active",
    onMessage: dispatch,
  });

  function chooseMention(name: string) {
    if (!mention) return;
    const start = (mention.index ?? 0) + (mention[0].startsWith(" ") ? 1 : 0);
    setContent(
      `${content.slice(0, start)}@${name} ${content.slice((mention.index ?? 0) + mention[0].length)}`,
    );
    setMentionIndex(0);
  }
  function sendMessage() {
    const clean = content.trim();
    if (!clean || uploading || !socket.isOpen) return;
    const payload = clean + buildAttachmentBlock(attachments);
    const targets = participants
      .filter((agent) =>
        new RegExp(`@${String(agent.name).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i").test(clean),
      )
      .map((agent) => agent.id);
    socket.send({ type: "user_message", content: payload, targets });
    setContent("");
    setAttachments([]);
  }
  async function addFiles(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    try {
      const uploaded = await Promise.all(Array.from(files).map(uploadAttachment));
      setAttachments((current) => [...current, ...uploaded]);
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), "error");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }
  async function updateParticipants(next: number[]) {
    try {
      const updated = await apiClient.patch<MeetingRecord>(`/meetings/${meeting.id}`, { participants: next });
      setRecord(updated);
      await refreshMeetings();
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), "error");
    }
  }
  async function endMeeting() {
    if (await confirm(vi ? "Kết thúc cuộc họp và soạn biên bản nháp?" : "End the meeting and draft minutes?"))
      socket.send({ type: "end_meeting" });
  }
  async function finalize() {
    if (!decision.trim())
      return toast(vi ? "Biên bản không được để trống." : "Minutes cannot be empty.", "error");
    try {
      const updated = await apiClient.post<MeetingRecord & { triggered_workflow_ids?: number[] }>(
        `/meetings/${meeting.id}/finalize`,
        { decision_text: decision.trim() },
      );
      setRecord(updated);
      setProposals(
        ((updated.proposed_items || []) as Proposal[]).map((item) => ({
          ...item,
          include: true,
          assigned_agent_id: item.suggested_agent_id,
        })),
      );
      setFinalizing(false);
      await refreshMeetings();
      toast(vi ? "Đã chốt biên bản." : "Minutes finalized.", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), "error");
    }
  }
  async function approveItems() {
    try {
      const result = await apiClient.post<{ work_item_ids: number[] }>(
        `/meetings/${meeting.id}/approve-items`,
        { items: proposals },
      );
      setProposals([]);
      await refreshMeetings();
      toast(
        vi
          ? `Đã tạo ${result.work_item_ids.length} công việc.`
          : `Created ${result.work_item_ids.length} work items.`,
        "success",
      );
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), "error");
    }
  }

  return (
    <section className={c("meetingRoom")} data-testid="meeting-room">
      <header className={c("meetingRoomHeader")}>
        <div>
          <h2>{record.title}</h2>
          <p>
            {record.topic || (vi ? "Không có chủ đề" : "No topic")}
            {record.project_id
              ? ` · ${projects.find((project) => project.id === record.project_id)?.name || ""}`
              : ""}
          </p>
        </div>
        <span className={`${c("meetingConnection")} ${socket.isOpen ? c("meetingConnected") : ""}`}>
          <i />
          {record.status !== "active"
            ? statusLabel(record.status, vi)
            : socket.isOpen
              ? vi
                ? "Đã kết nối"
                : "Connected"
              : socket.state === "connecting"
                ? vi
                  ? "Đang nối"
                  : "Connecting"
                : vi
                  ? `Nối lại ${socket.reconnectAttempt}/5`
                  : `Reconnect ${socket.reconnectAttempt}/5`}
        </span>
        {record.status === "active" ? (
          <button className={c("buttonDanger")} onClick={() => void endMeeting()}>
            <Icon name="stop" />
            {vi ? "Kết thúc" : "End"}
          </button>
        ) : record.status === "ended" ? (
          <button className={c("primaryButton")} onClick={() => setFinalizing(true)}>
            <Icon name="save" />
            {vi ? "Chốt kế hoạch" : "Finalize"}
          </button>
        ) : null}
      </header>
      <details className={c("participantPanel")}>
        <summary>
          <Icon name="people" />
          {participants.length} {vi ? "người tham dự" : "participants"}
        </summary>
        <div>
          {agents.map((agent) => (
            <label key={agent.id}>
              <input
                type="checkbox"
                disabled={record.status !== "active"}
                checked={participantIds.includes(agent.id)}
                onChange={() =>
                  void updateParticipants(
                    participantIds.includes(agent.id)
                      ? participantIds.filter((id) => id !== agent.id)
                      : [...participantIds, agent.id],
                  )
                }
              />
              <span>{agent.name}</span>
              <small>{agent.role}</small>
            </label>
          ))}
        </div>
      </details>
      {record.status !== "active" ? (
        <MeetingRecord
          record={record}
          proposals={proposals}
          setProposals={setProposals}
          approveItems={approveItems}
          vi={vi}
          agents={agents}
        />
      ) : null}
      <div className={c("meetingMessages")} ref={messagesRef} data-testid="meeting-messages">
        {live.messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {Object.values(live.streams).map((stream) => (
          <div key={stream.agentId} className={c("agentMessage")} data-testid="agent-stream">
            <strong>{stream.agent}</strong>
            <div>
              {stream.thinking ? (
                <span className={c("thinkingDots")}>•••</span>
              ) : (
                <Markdown content={stream.content} streaming />
              )}
            </div>
          </div>
        ))}
        {Object.values(live.progress).map((progress) => (
          <div key={progress.run_id} className={c("workflowProgress")} data-testid="workflow-progress">
            <span className={c("busyDot")} />
            <div>
              <strong>
                {vi ? "Hệ thống" : "System"} · {progress.task_name || (vi ? "Quy trình" : "Workflow")}
              </strong>
              <p>
                {progress.label}
                {progress.total ? ` · ${vi ? "bước" : "step"} ${progress.step || 0}/${progress.total}` : ""}
              </p>
            </div>
          </div>
        ))}
        {Object.values(live.approvals).map((approval) => (
          <ApprovalCard
            key={approval.output_id}
            approval={approval}
            resolve={(resolution) =>
              dispatch({ type: "__approval_resolved", output_id: approval.output_id, resolution })
            }
            refresh={refreshMeetings}
            vi={vi}
            toast={toast}
          />
        ))}
        {Object.values(live.imageSources).map((request) => (
          <ImageSourceCard
            key={`${request.run_id}:${request.node_id}`}
            request={request}
            resolve={(mode) =>
              dispatch({
                type: "__image_source_resolved",
                run_id: request.run_id,
                node_id: request.node_id,
                mode,
              })
            }
            vi={vi}
            toast={toast}
          />
        ))}
      </div>
      {record.status === "active" ? (
        <footer className={c("meetingComposer")}>
          {attachments.length ? (
            <div className={c("attachmentChips")}>
              {attachments.map((attachment, index) => (
                <span key={`${attachment.name}-${index}`}>
                  {attachment.name}
                  <button
                    onClick={() =>
                      setAttachments((current) => current.filter((_, itemIndex) => itemIndex !== index))
                    }
                  >
                    <Icon name="close" />
                  </button>
                </span>
              ))}
            </div>
          ) : null}
          <div className={c("composerRow")}>
            <button
              className={c("attachButton")}
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              title={vi ? "Đính kèm" : "Attach"}
            >
              <Icon name="upload" />
            </button>
            <input
              ref={fileRef}
              type="file"
              multiple
              hidden
              onChange={(event) => void addFiles(event.target.files)}
            />
            <div className={c("composerInput")}>
              <textarea
                value={content}
                rows={2}
                placeholder={
                  vi
                    ? "Nhắn cho Xanax hoặc gõ @ để gọi nhân viên…"
                    : "Message Xanax or type @ to mention staff…"
                }
                onChange={(event) => {
                  setContent(event.target.value);
                  setMentionIndex(0);
                }}
                onKeyDown={(event) => {
                  if (mention && mentionCandidates.length) {
                    if (event.key === "ArrowDown") {
                      event.preventDefault();
                      setMentionIndex((mentionIndex + 1) % mentionCandidates.length);
                    } else if (event.key === "ArrowUp") {
                      event.preventDefault();
                      setMentionIndex(
                        (mentionIndex - 1 + mentionCandidates.length) % mentionCandidates.length,
                      );
                    } else if (event.key === "Enter" || event.key === "Tab") {
                      event.preventDefault();
                      chooseMention(mentionCandidates[mentionIndex]?.name || "Xanax");
                    } else if (event.key === "Escape") setContent(`${content} `);
                  } else if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                  }
                }}
              />
              {mention && mentionCandidates.length ? (
                <div className={c("mentionMenu")} role="listbox">
                  {mentionCandidates.map((candidate, index) => (
                    <button
                      key={`${candidate.id}-${candidate.name}`}
                      className={index === mentionIndex ? c("mentionActive") : ""}
                      onMouseDown={(event) => {
                        event.preventDefault();
                        chooseMention(candidate.name);
                      }}
                    >
                      @{candidate.name}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            <button
              className={c("primaryButton")}
              disabled={!content.trim() || uploading || !socket.isOpen}
              onClick={sendMessage}
            >
              <Icon name="send" />
              {vi ? "Gửi" : "Send"}
            </button>
          </div>
        </footer>
      ) : null}
      {finalizing ? (
        <div className={c("modalBackdrop")}>
          <section className={`${c("dialog")} ${c("dialogWide")}`}>
            <header>
              <h2>{vi ? "Chốt biên bản" : "Finalize minutes"}</h2>
              <button onClick={() => setFinalizing(false)}>
                <Icon name="close" />
              </button>
            </header>
            <div className={c("dialogBody")}>
              <label className={c("field")}>
                <span>
                  {vi ? "Biên bản — có thể sửa trước khi chốt" : "Minutes — edit before finalizing"}
                </span>
                <textarea
                  className={c("textarea")}
                  rows={16}
                  value={decision}
                  onChange={(event) => setDecision(event.target.value)}
                />
              </label>
              <div className={c("formActions")}>
                <span />
                <div>
                  <button className={c("buttonGhost")} onClick={() => setFinalizing(false)}>
                    {vi ? "Đóng" : "Close"}
                  </button>
                  <button className={c("primaryButton")} onClick={() => void finalize()}>
                    {vi ? "Chốt kế hoạch" : "Finalize"}
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function MessageBubble({
  message,
}: {
  message: { sender: string; senderType: string; content: string; createdAt?: string };
}) {
  const user = message.senderType === "user";
  const system = message.senderType === "system";
  return (
    <div
      className={`${c("meetingMessage")} ${user ? c("userMessage") : system ? c("systemMessage") : c("agentMessage")}`}
    >
      <strong>{user ? "Bạn" : message.sender}</strong>
      <div>
        <Markdown content={message.content} />
      </div>
      {message.createdAt ? (
        <time>
          {new Date(
            message.createdAt.includes("T") ? message.createdAt : `${message.createdAt.replace(" ", "T")}Z`,
          ).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </time>
      ) : null}
    </div>
  );
}

function ApprovalCard({
  approval,
  resolve,
  refresh,
  vi,
  toast,
}: {
  approval: ApprovalRequest;
  resolve: (value: "approved" | "rejected") => void;
  refresh: () => Promise<void>;
  vi: boolean;
  toast: (message: string, kind?: "success" | "error" | "info") => void;
}) {
  const [edited, setEdited] = useState(approval.content || "");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  async function decide(resolution: "approved" | "rejected") {
    setBusy(true);
    try {
      await apiClient.patch(
        `/workflow/outputs/${approval.output_id}`,
        resolution === "approved"
          ? { review_status: "approved", edited_content: edited }
          : { review_status: "rejected", notes: reason },
      );
      resolve(resolution);
      await refresh();
      toast(
        resolution === "approved"
          ? vi
            ? "Đã duyệt."
            : "Approved."
          : vi
            ? "Đã yêu cầu làm lại."
            : "Revision requested.",
        "success",
      );
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), "error");
    } finally {
      setBusy(false);
    }
  }
  if (approval.resolved)
    return (
      <div className={c("resolvedCard")}>
        {approval.resolved === "approved"
          ? "✓ " + (vi ? "Đã duyệt" : "Approved")
          : "↻ " + (vi ? "Đã yêu cầu làm lại" : "Revision requested")}
      </div>
    );
  return (
    <article className={c("approvalCard")} data-testid="approval-request">
      <header>
        ✋ {approval.task_name || (vi ? "Quy trình" : "Workflow")} — {vi ? "chờ" : "waiting for"}{" "}
        {approval.approver || "CEO"}{" "}
        {approval.restored ? (
          <small>{vi ? "(khôi phục sau khi nối lại)" : "(restored after reconnect)"}</small>
        ) : null}
      </header>
      {approval.note ? <p>{approval.note}</p> : null}
      {approval.images?.length ? (
        <div className={c("approvalImages")}>
          {approval.images.map((url) => (
            <img key={url} src={url} alt="Approval" />
          ))}
        </div>
      ) : null}
      <label>
        <span>{vi ? "Nội dung — sửa trực tiếp trước khi duyệt" : "Content — edit before approval"}</span>
        <textarea value={edited} rows={8} onChange={(event) => setEdited(event.target.value)} />
      </label>
      <label>
        <span>{vi ? "Lý do không duyệt" : "Rejection reason"}</span>
        <textarea value={reason} rows={2} onChange={(event) => setReason(event.target.value)} />
      </label>
      <footer>
        <button className={c("buttonGhost")} disabled={busy} onClick={() => void decide("rejected")}>
          {vi ? "Không duyệt — làm lại" : "Reject — revise"}
        </button>
        <button className={c("primaryButton")} disabled={busy} onClick={() => void decide("approved")}>
          {vi ? "Duyệt & đăng" : "Approve & publish"}
        </button>
      </footer>
    </article>
  );
}

function ImageSourceCard({
  request,
  resolve,
  vi,
  toast,
}: {
  request: ImageSourceRequest;
  resolve: (mode: "asset" | "generate") => void;
  vi: boolean;
  toast: (message: string, kind?: "success" | "error" | "info") => void;
}) {
  const [busy, setBusy] = useState(false);
  async function choose(mode: "asset" | "generate", assetId?: number) {
    setBusy(true);
    try {
      await apiClient.post(`/workflow/runs/${request.run_id}/image-source`, {
        node_id: request.node_id,
        mode,
        asset_id: assetId,
      });
      resolve(mode);
      toast(vi ? "Đã gửi lựa chọn ảnh." : "Image choice sent.", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), "error");
    } finally {
      setBusy(false);
    }
  }
  async function upload(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("note", vi ? "Tải lên khi chạy quy trình" : "Uploaded during workflow");
      const asset = await apiClient.postForm<{ id: number }>("/assets/upload", form);
      await choose("asset", asset.id);
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), "error");
      setBusy(false);
    }
  }
  if (request.resolved)
    return (
      <div className={c("resolvedCard")}>
        {request.resolved === "asset"
          ? "🖼️ " + (vi ? "Đã dùng ảnh có sẵn" : "Existing image selected")
          : "🎨 " + (vi ? "Nhân viên tự vẽ" : "Agent will generate")}
      </div>
    );
  return (
    <article className={c("approvalCard")} data-testid="image-source-request">
      <header>
        🖼️ {request.task_name || (vi ? "Quy trình" : "Workflow")} —{" "}
        {vi ? "lấy ảnh từ đâu?" : "where should the image come from?"}
      </header>
      <footer>
        <button className={c("primaryButton")} disabled={busy} onClick={() => void choose("generate")}>
          {vi ? "Để nhân viên tự vẽ" : "Generate image"}
        </button>
        <label className={c("buttonGhost")}>
          {vi ? "Tải ảnh lên" : "Upload image"}
          <input
            type="file"
            accept="image/*"
            hidden
            disabled={busy}
            onChange={(event) => void upload(event.target.files?.[0])}
          />
        </label>
      </footer>
      {request.assets?.length ? (
        <div className={c("imageSourceGrid")}>
          {request.assets.map((asset) => (
            <button
              key={asset.id}
              disabled={busy}
              onClick={() => void choose("asset", asset.id)}
              title={asset.note}
            >
              <img src={asset.url} alt={asset.filename} />
              <span>{asset.filename}</span>
            </button>
          ))}
        </div>
      ) : (
        <p>
          {vi
            ? `Chưa có ảnh. Sau ${request.timeout_minutes || 10} phút, nhân viên sẽ tự vẽ.`
            : `No images available. After ${request.timeout_minutes || 10} minutes, the agent will generate one.`}
        </p>
      )}
    </article>
  );
}

function MeetingRecord({
  record,
  proposals,
  setProposals,
  approveItems,
  vi,
  agents,
}: {
  record: MeetingRecord;
  proposals: Proposal[];
  setProposals: React.Dispatch<React.SetStateAction<Proposal[]>>;
  approveItems: () => Promise<void>;
  vi: boolean;
  agents: Array<{ id: number; name?: string; role?: string }>;
}) {
  const minutes = String(
    record.decision_text || record.draft_minutes || (vi ? "Chưa có nội dung biên bản." : "No minutes yet."),
  );
  return (
    <section className={c("meetingRecord")}>
      <details open>
        <summary>
          {vi ? "Biên bản cuộc họp" : "Meeting minutes"} ·{" "}
          {record.status === "finalized" ? (vi ? "Đã chốt" : "Finalized") : vi ? "Bản nháp" : "Draft"}
        </summary>
        <div className={c("minutesText")}>
          <Markdown content={minutes} />
        </div>
      </details>
      {proposals.length ? (
        <details open>
          <summary>
            {vi ? "Đề xuất công việc" : "Work item proposals"} ({proposals.length})
          </summary>
          <div className={c("proposalList")}>
            {proposals.map((item, index) => (
              <article key={index}>
                <input
                  type="checkbox"
                  checked={item.include !== false}
                  onChange={(event) =>
                    setProposals((current) =>
                      current.map((value, i) =>
                        i === index ? { ...value, include: event.target.checked } : value,
                      ),
                    )
                  }
                />
                <div>
                  <input
                    value={item.title}
                    onChange={(event) =>
                      setProposals((current) =>
                        current.map((value, i) =>
                          i === index ? { ...value, title: event.target.value } : value,
                        ),
                      )
                    }
                  />
                  <textarea
                    rows={2}
                    value={item.description}
                    onChange={(event) =>
                      setProposals((current) =>
                        current.map((value, i) =>
                          i === index ? { ...value, description: event.target.value } : value,
                        ),
                      )
                    }
                  />
                  <select
                    value={item.priority}
                    onChange={(event) =>
                      setProposals((current) =>
                        current.map((value, i) =>
                          i === index ? { ...value, priority: event.target.value } : value,
                        ),
                      )
                    }
                  >
                    <option value="low">{vi ? "Thấp" : "Low"}</option>
                    <option value="medium">{vi ? "Trung bình" : "Medium"}</option>
                    <option value="high">{vi ? "Cao" : "High"}</option>
                  </select>
                </div>
                <select
                  value={item.assigned_agent_id || ""}
                  onChange={(event) =>
                    setProposals((current) =>
                      current.map((value, i) =>
                        i === index
                          ? { ...value, assigned_agent_id: Number(event.target.value) || null }
                          : value,
                      ),
                    )
                  }
                >
                  <option value="">— {vi ? "Chưa giao" : "Unassigned"} —</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name} — {agent.role}
                    </option>
                  ))}
                </select>
              </article>
            ))}
          </div>
          <button className={c("primaryButton")} onClick={() => void approveItems()}>
            {vi ? "Tạo công việc đã chọn" : "Create selected items"}
          </button>
        </details>
      ) : null}
    </section>
  );
}
