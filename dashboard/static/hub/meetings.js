import { agentDeptBadgeHtml, agentDeptSuffix, agents } from './agents.js';
import { api, checkAuthOrRedirect } from './api.js';
import { avatarHtml } from './avatar.js';
import { icon } from './icons.js';
import { closeModal, showConfirm, showToast } from './modals.js';
import { openProjectDetail, projects } from './projects.js';
import { switchTab } from './tabs.js';
import { esc } from './utils.js';

// State phòng họp. lastMessageAt dùng để chèn vạch phân tách thời gian
// (giống Messenger) khi có khoảng lặng > SESSION_GAP_MS giữa 2 tin nhắn.
export let meetings = [];
let currentMeetingId = null;
let currentMeetingWs = null;
let lastMessageAt = null;
const SESSION_GAP_MS = 15 * 60 * 1000;

// MEETINGS
// ════════════════════════════════════════
export async function loadMeetings() {
  const data = await api('GET', '/meetings/');
  meetings = data.meetings || [];
  renderMeetingList();
}

export function renderMeetingList() {
  const el = document.getElementById('meetings-list');
  if (!meetings.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${icon('meeting')}</div><div class="empty-state-text">No meetings yet</div></div>`;
    return;
  }
  const statusMeta = {
    active: { label: 'Đang diễn ra', badge: 'badge-green' },
    ended: { label: 'Đã kết thúc', badge: 'badge-muted' },
    finalized: { label: 'Đã chốt', badge: 'badge-amber' },
  };
  el.innerHTML = meetings.map(m => `
    <div class="list-item${m.id===currentMeetingId?' selected':''}" onclick="openMeeting(${m.id})">
      <div style="flex:1;min-width:0;">
        <div class="list-item-name">${esc(m.title)}</div>
        ${m.project_id ? `<div class="list-item-sub meeting-list-project">${icon('folder')} <span>${esc(projects.find(p => p.id === m.project_id)?.name || 'Dự án liên kết')}</span></div>` : ''}
        <div class="list-item-sub meeting-list-meta">
          <span class="badge ${(statusMeta[m.status] || statusMeta.ended).badge}">${esc((statusMeta[m.status] || {label:m.status}).label)}</span>
          <span>${m.participants.length} nhân viên</span>
        </div>
      </div>
      <button class="btn btn-ghost btn-sm meeting-delete-btn" onclick="event.stopPropagation();deleteMeeting(${m.id})" title="Xoá cuộc họp">${icon('close')}</button>
    </div>`).join('');
}

export function newMeeting() {
  document.getElementById('meeting-modal-title').value = '';
  document.getElementById('meeting-modal-topic').value = '';
  const projSel = document.getElementById('meeting-modal-project');
  projSel.innerHTML = '<option value="">— Không gắn dự án —</option>' +
    projects.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
  document.getElementById('meeting-modal').classList.remove('hidden');
}

export async function createMeeting() {
  const title = document.getElementById('meeting-modal-title').value.trim();
  const topic = document.getElementById('meeting-modal-topic').value.trim();
  if (!title) return showToast('Title is required', 'error');
  const projVal = document.getElementById('meeting-modal-project').value;
  const m = await api('POST', '/meetings/', { title, topic, participants: [], project_id: projVal ? parseInt(projVal) : null });
  closeModal('meeting-modal');
  await loadMeetings();
  openMeeting(m.id);
}

export async function openMeeting(id) {
  if (currentMeetingWs) { currentMeetingWs.close(); currentMeetingWs = null; }
  currentMeetingId = id;
  renderMeetingList();
  const m = await api('GET', `/meetings/${id}`).catch(() => meetings.find(x => x.id === id));
  if (!m) return;
  const meetingIndex = meetings.findIndex(x => x.id === id);
  if (meetingIndex >= 0) meetings[meetingIndex] = m;

  document.getElementById('meeting-empty').style.display = 'none';
  document.getElementById('meeting-chat').style.display = 'flex';
  document.getElementById('meeting-title-label').textContent = m.title;
  document.getElementById('meeting-topic-label').textContent = m.topic || '';
  const project = projects.find(p => p.id === m.project_id);
  document.getElementById('meeting-project-label').innerHTML = project
    ? `<span class="meeting-project-link" onclick="openMeetingProject(${project.id})">${icon('folder')} <span>${esc(project.name)}</span></span>`
    : '';
  document.getElementById('meeting-end-btn').style.display = m.status === 'active' ? '' : 'none';
  document.getElementById('meeting-finalize-btn').style.display = m.status === 'ended' ? '' : 'none';
  document.getElementById('meeting-input-area').style.display = m.status === 'active' ? '' : 'none';
  document.getElementById('meeting-messages').innerHTML = '';
  lastMessageAt = null;

  await renderParticipants(m.participants);
  renderMeetingRecord(m);

  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${location.host}/ws/meeting/${id}`);
  currentMeetingWs = ws;

  ws.onmessage = (e) => handleMeetingMsg(JSON.parse(e.data));
  ws.onerror = () => appendMeetingMsg('system', 'WebSocket error', 'var(--red)');
  ws.onclose = (e) => { if (e.code !== 1000) checkAuthOrRedirect(); };
}

export function openMeetingProject(projectId) {
  switchTab('tasks');
  openProjectDetail(projectId);
}

function renderMeetingRecord(m) {
  const panel = document.getElementById('meeting-record-panel');
  if (!m || !['ended', 'finalized'].includes(m.status)) {
    panel.innerHTML = '';
    return;
  }
  const minutes = m.decision_text || m.draft_minutes || 'Chưa có nội dung biên bản.';
  const decided = m.decided_at
    ? ` · Chốt lúc ${_parseServerTime(m.decided_at).toLocaleString('vi-VN')}`
    : '';
  const items = Array.isArray(m.proposed_items) ? m.proposed_items : [];
  const agentOptions = (selectedId) => '<option value="">— Chưa giao —</option>' +
    agents.map(a => `<option value="${a.id}" ${a.id === selectedId ? 'selected' : ''}>${esc(a.name)} — ${esc(a.role || '')}</option>`).join('');
  panel.innerHTML = `
    <details>
      <summary>Biên bản cuộc họp${m.status === 'finalized' ? ' · Đã chốt' : ' · Bản nháp'}${esc(decided)}</summary>
      <div class="meeting-minutes-content">${esc(minutes)}</div>
    </details>
    ${items.length ? `<details open>
      <summary>Đề xuất công việc từ biên bản (${items.length})</summary>
      <div class="meeting-proposals">
        ${items.map((item, index) => `
          <div class="meeting-proposal" data-proposal-index="${index}">
            <input type="checkbox" class="meeting-proposal-include" checked title="Tạo công việc này">
            <div class="meeting-proposal-fields">
              <input class="form-input meeting-proposal-title" value="${esc(item.title || '')}" aria-label="Tiêu đề công việc">
              <textarea class="form-textarea meeting-proposal-description" rows="2" aria-label="Mô tả công việc">${esc(item.description || '')}</textarea>
              <select class="form-select meeting-proposal-priority" aria-label="Độ ưu tiên">
                <option value="low" ${item.priority === 'low' ? 'selected' : ''}>Thấp</option>
                <option value="medium" ${item.priority === 'medium' ? 'selected' : ''}>Trung bình</option>
                <option value="high" ${item.priority === 'high' ? 'selected' : ''}>Cao</option>
              </select>
            </div>
            <div class="meeting-proposal-assignee">
              <select class="form-select meeting-proposal-agent" aria-label="Người được giao">${agentOptions(item.suggested_agent_id)}</select>
              ${item.match_reason ? `<div class="meeting-proposal-reason">${esc(item.match_reason)}</div>` : '<div class="meeting-proposal-reason">Chưa tìm thấy nhân viên đủ điểm phù hợp — hãy chọn thủ công.</div>'}
            </div>
          </div>`).join('')}
        <div class="meeting-proposals-actions">
          <button class="btn btn-primary btn-sm" onclick="approveMeetingItems()">Tạo công việc đã chọn</button>
        </div>
      </div>
    </details>` : ''}`;
}

export async function deleteMeeting(id) {
  const meeting = meetings.find(m => m.id === id);
  if (!(await showConfirm(`Xoá cuộc họp “${meeting?.title || id}”?`, 'Xoá cuộc họp'))) return;
  await api('DELETE', `/meetings/${id}`);
  if (currentMeetingId === id) {
    if (currentMeetingWs) currentMeetingWs.close();
    currentMeetingWs = null;
    currentMeetingId = null;
    document.getElementById('meeting-chat').style.display = 'none';
    document.getElementById('meeting-empty').style.display = '';
  }
  await loadMeetings();
  showToast('Đã xoá cuộc họp.', 'success');
}

export async function approveMeetingItems() {
  if (!currentMeetingId) return;
  const items = [...document.querySelectorAll('.meeting-proposal')].map(row => ({
    title: row.querySelector('.meeting-proposal-title').value.trim(),
    description: row.querySelector('.meeting-proposal-description').value.trim(),
    priority: row.querySelector('.meeting-proposal-priority').value,
    assigned_agent_id: Number(row.querySelector('.meeting-proposal-agent').value) || null,
    include: row.querySelector('.meeting-proposal-include').checked,
  }));
  if (items.some(item => item.include && !item.title)) {
    showToast('Tiêu đề công việc được chọn không được để trống.', 'error');
    return;
  }
  try {
    const res = await api('POST', `/meetings/${currentMeetingId}/approve-items`, { items });
    const m = await api('GET', `/meetings/${currentMeetingId}`);
    const index = meetings.findIndex(item => item.id === currentMeetingId);
    if (index >= 0) meetings[index] = m;
    renderMeetingRecord(m);
    const count = (res.work_item_ids || []).length;
    showToast(`Đã tạo ${count} công việc. Mở tab Công việc để theo dõi.`, 'success');
  } catch (e) {
    showToast('Không thể tạo công việc: ' + e.message, 'error');
  }
}

async function renderParticipants(ids) {
  const agentObjs = await Promise.all(ids.map(id => {
    const a = agents.find(x => x.id === id);
    return a ? Promise.resolve(a) : api('GET', `/agent-configs/${id}`).catch(()=>null);
  }));
  const list = agentObjs.filter(Boolean);

  document.getElementById('participants-count').textContent = list.length;

  const panel = document.getElementById('participants-dropdown-panel');
  panel.innerHTML = list.length
    ? list.map(a => `
      <div class="participant-chip">
        ${avatarHtml(a.avatar_color, a.name, 'avatar-sm')}
        <span>${esc(a.name)}</span>
        ${agentDeptBadgeHtml(a)}
      </div>`).join('')
    : '<div class="participants-dropdown-empty">Chưa có nhân viên nào trong cuộc họp</div>';
}

export function toggleParticipantsDropdown(event) {
  event.stopPropagation();
  document.getElementById('participants-dropdown-panel').classList.toggle('hidden');
}

document.addEventListener('click', (e) => {
  const dropdown = document.getElementById('participants-dropdown');
  const panel = document.getElementById('participants-dropdown-panel');
  if (dropdown && panel && !dropdown.contains(e.target)) panel.classList.add('hidden');
});

// ── Thời gian tin nhắn + vạch phân tách session (giống Messenger) ──

function _parseServerTime(str) {
  // SQLite datetime('now') trả "YYYY-MM-DD HH:MM:SS" (UTC, không có 'Z') -> ép về ISO UTC.
  if (!str) return new Date();
  return new Date(str.includes('T') ? str : str.replace(' ', 'T') + 'Z');
}

function _msgTimeLabel(date) {
  return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

function _dividerLabel(date) {
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  const time = _msgTimeLabel(date);
  if (sameDay) return `Hôm nay ${time}`;
  return `${date.toLocaleDateString('vi-VN')} ${time}`;
}

// Chèn vạch phân tách thời gian nếu khoảng cách với tin nhắn trước > 15 phút (hoặc đây là
// tin nhắn đầu tiên của phòng họp) — giống cơ chế "session" của Messenger/Zalo.
function _maybeInsertTimeDivider(date) {
  const ts = date.getTime();
  if (lastMessageAt === null || ts - lastMessageAt > SESSION_GAP_MS) {
    const area = document.getElementById('meeting-messages');
    area.insertAdjacentHTML('beforeend', `<div class="time-divider">${esc(_dividerLabel(date))}</div>`);
  }
  lastMessageAt = ts;
}

// In đậm "@Tên" khi Tên khớp đúng 1 nhân viên hoặc Xanax — áp dụng trước khi đưa qua
// marked.parse() để render ra <strong>@Tên</strong> trong bong bóng chat.
function _boldenMentions(content) {
  const names = [...new Set([...(agents || []).map(a => a.name), 'Xanax'].filter(Boolean))];
  if (!names.length) return content;
  const sorted = names.sort((a, b) => b.length - a.length).map(n => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const re = new RegExp('@(' + sorted.join('|') + ')\\b', 'gi');
  return content.replace(re, '**@$1**');
}

function handleMeetingMsg(msg) {
  if (msg.type === 'history') {
    msg.messages.forEach(m => {
      const time = _parseServerTime(m.created_at);
      _maybeInsertTimeDivider(time);
      if (m.sender_type === 'user') appendMeetingMsg('user', m.content, 'var(--cyan)', time);
      else if (m.sender_type === 'system') appendSystemMsg(m.content, time);
      else if (m.sender === 'Xanax') appendMeetingMsg('Xanax', m.content, 'var(--gold)', time);
      else {
        const a = agents.find(x => x.name === m.sender);
        appendMeetingMsg(m.sender, m.content, a?.avatar_color || 'var(--purple)', time);
      }
    });
    return;
  }
  if (msg.type === 'user_message') {
    const time = new Date();
    _maybeInsertTimeDivider(time);
    appendMeetingMsg('user', msg.content, 'var(--cyan)', time);
    return;
  }
  if (msg.type === 'agent_thinking') {
    _maybeInsertTimeDivider(new Date());
    appendThinking(msg.agent, msg.agent_id, msg.color);
    return;
  }
  if (msg.type === 'agent_chunk') {
    appendAgentChunk(msg.agent_id, msg.agent, msg.color, msg.content);
    return;
  }
  if (msg.type === 'agent_done') {
    finishAgentMessage(msg.agent_id);
    return;
  }
  if (msg.type === 'agent_cancelled') {
    removeThinking(msg.agent_id);
    return;
  }
  // Thông báo do hệ thống đẩy vào giữa chừng (vd: quy trình đang chờ CEO duyệt).
  // Nội dung đã được lưu vào lịch sử họp phía server, đây chỉ là hiện ngay.
  if (msg.type === 'system_notice') {
    _maybeInsertTimeDivider(new Date());
    appendSystemMsg(msg.content);
    return;
  }
  if (msg.type === 'workflow_progress') {
    renderWorkflowProgress(msg);
    return;
  }
  if (msg.type === 'approval_request') {
    renderApprovalRequest(msg);
    return;
  }
  if (msg.type === 'participants_updated') {
    renderParticipants(msg.participants.map(p => p.id));
    return;
  }
  if (msg.type === 'meeting_ended') {
    appendMeetingMsg('system', 'Cuộc họp đã kết thúc. Xanax đã soạn biên bản nháp — xem lại và bấm "Chốt kế hoạch".', 'var(--muted)');
    const meeting = meetings.find(m => m.id === currentMeetingId);
    if (meeting) {
      meeting.status = 'ended';
      meeting.draft_minutes = msg.draft_minutes || '';
      meeting.proposed_items = [];
      renderMeetingList();
      renderMeetingRecord(meeting);
    }
    document.getElementById('meeting-end-btn').style.display = 'none';
    document.getElementById('meeting-finalize-btn').style.display = '';
    document.getElementById('meeting-input-area').style.display = 'none';
    if (msg.draft_minutes) openFinalizeModal(msg.draft_minutes);
    return;
  }
}

// Thông báo hệ thống được LƯU vào lịch sử họp, nên lúc hiện ngay và lúc tải lại
// phải trông y hệt nhau. Trước đây live gọi appendMeetingMsg('system', …) — ra
// chữ nghiêng xám không tên không giờ — còn lịch sử đi nhánh thường với
// sender = "Hệ thống" nên có avatar, tên và giờ. Cùng một nội dung, hai hình
// dạng, và người dùng phải F5 mới thấy dạng thật.
const SYSTEM_SENDER = 'Hệ thống';
const SYSTEM_COLOR = 'var(--purple)';

function appendSystemMsg(content, time) {
  appendMeetingMsg(SYSTEM_SENDER, content, SYSTEM_COLOR, time || new Date());
}

function appendMeetingMsg(sender, content, color, time) {
  const area = document.getElementById('meeting-messages');
  const isUser = sender === 'user';
  const isSystem = sender === 'system';
  const agentForMsg = !isUser && !isSystem ? agents.find(x => x.name === sender) : null;
  const timeLabel = _msgTimeLabel(time || new Date());
  const html = `
    <div class="message-row${isUser?' user-row':''}">
      ${!isUser && !isSystem ? avatarHtml(agentForMsg?.avatar_color || color, sender, 'avatar-sm') : ''}
      <div>
        ${!isUser && !isSystem ? `<div class="message-sender" style="color:${color}">${esc(sender)}${agentDeptSuffix(agentForMsg)}</div>` : ''}
        <div class="message-bubble ${isUser?'user-bubble':'agent-bubble'}" ${isSystem?'style="background:var(--bg3);border-color:var(--border);color:var(--muted);font-style:italic;"':''}>
          ${marked.parse(_boldenMentions(content))}
        </div>
        ${!isSystem ? `<div class="msg-time">${esc(timeLabel)}</div>` : ''}
      </div>
    </div>`;
  area.insertAdjacentHTML('beforeend', html);
  area.scrollTop = area.scrollHeight;
}

// Một bong bóng tiến độ cho mỗi lần chạy, cập nhật tại chỗ thay vì đẩy tin nhắn
// mới liên tục — CEO thấy đang ở bước nào và khi nào xong.
const WF_PROGRESS_STYLE = {
  running:   { icon: '',   color: 'var(--cyan)'  },
  waiting:   { icon: '✋', color: 'var(--amber)' },
  done:      { icon: '✅', color: 'var(--green)' },
  failed:    { icon: '⚠️', color: 'var(--red)'   },
  cancelled: { icon: '⛔', color: 'var(--muted)' },
};

function renderWorkflowProgress(msg) {
  const area = document.getElementById('meeting-messages');
  if (!area) return;
  const style = WF_PROGRESS_STYLE[msg.status] || WF_PROGRESS_STYLE.running;
  const id = `wf-progress-${msg.run_id}`;
  let el = document.getElementById(id);

  // Chạy xong thì bong bóng này hết việc: server đã lưu kết quả thành tin nhắn
  // "Hệ thống" và đẩy kèm system_notice. Giữ lại bong bóng là hiện hai lần cùng
  // một chuyện, và bong bóng biến mất sau khi tải lại — đúng cái làm màn hình
  // trước và sau F5 khác nhau.
  if (msg.status === 'done' || msg.status === 'failed' || msg.status === 'cancelled') {
    if (el) el.remove();
    return;
  }

  if (!el) {
    el = document.createElement('div');
    el.className = 'message-row';
    el.id = id;
    area.appendChild(el);
  }
  // Tới đây chỉ còn 'running' hoặc 'waiting' — trạng thái kết thúc đã thoát ở trên.
  //
  // Dựng đúng khung của một tin nhắn hệ thống: avatar + tên người gửi + giờ.
  // Trước đây bong bóng này là một khối riêng không avatar không giờ, nên dòng
  // thời gian trong phòng họp có hai loại hình dạng lẫn vào nhau.
  const stepText = msg.total ? ` · bước ${msg.step || 0}/${msg.total}` : '';
  const statusIcon = msg.status === 'running'
    ? '<span class="busy-spinner" aria-hidden="true"></span>'
    : style.icon;
  const title = `${esc(msg.task_name || 'Quy trình')}${esc(stepText)}`;
  el.innerHTML = `
    ${avatarHtml(SYSTEM_COLOR, SYSTEM_SENDER, 'avatar-sm')}
    <div>
      <div class="message-sender" style="color:${style.color}">
        ${statusIcon} ${esc(SYSTEM_SENDER)} · ${title}
      </div>
      <div class="message-bubble agent-bubble"
           style="border-color:${style.color};opacity:.92;">
        ${esc(msg.label || '')} <span class="thinking-dots" aria-hidden="true"></span>
      </div>
      <div class="msg-time">${esc(_msgTimeLabel(new Date()))}</div>
    </div>`;
  area.scrollTop = area.scrollHeight;
}

// ── Duyệt bài ngay trong phòng họp ─────────────────────────────────────────
// CEO xem đủ nội dung + ảnh, sửa được chữ, và chọn duyệt / bắt làm lại mà không
// phải rời phòng họp sang tab Vận hành.
function renderApprovalRequest(msg) {
  const area = document.getElementById('meeting-messages');
  if (!area) return;
  const id = `approval-card-${msg.output_id}`;
  if (document.getElementById(id)) return;   // tránh dựng trùng khi engine báo lại

  const images = (msg.images || []).map(url =>
    `<img src="${esc(url)}" alt="Ảnh của bài đăng" class="approval-image">`).join('');

  const el = document.createElement('div');
  el.className = 'message-row';
  el.id = id;
  el.innerHTML = `
    <div class="approval-card">
      <div class="approval-card-head">
        ✋ ${esc(msg.task_name || 'Quy trình')} — chờ ${esc(msg.approver || 'CEO')} duyệt
        ${esc(msg.deadline_note || '')}
      </div>
      ${msg.note ? `<div class="approval-note">${esc(msg.note)}</div>` : ''}
      ${images ? `<div class="approval-images">${images}</div>` : ''}
      <label class="approval-label">Nội dung bài đăng — sửa trực tiếp trước khi duyệt</label>
      <textarea class="approval-content" rows="10">${esc(msg.content || '')}</textarea>
      <div class="approval-actions">
        <button class="btn btn-sm" onclick="resolveMeetingApproval(${msg.output_id}, false)">
          Không duyệt — làm lại bước trước
        </button>
        <button class="btn btn-sm btn-primary" onclick="resolveMeetingApproval(${msg.output_id}, true)">
          Duyệt &amp; đăng
        </button>
      </div>
      <div class="approval-hint">
        Bấm "Không duyệt" để bước trước chạy lại — nội dung và ảnh sẽ được tạo mới.
      </div>
    </div>`;
  area.appendChild(el);
  area.scrollTop = area.scrollHeight;
}

export async function resolveMeetingApproval(outputId, approved) {
  const card = document.getElementById(`approval-card-${outputId}`);
  const textarea = card?.querySelector('.approval-content');
  const buttons = card?.querySelectorAll('button') || [];
  buttons.forEach(b => { b.disabled = true; });
  try {
    await api('PATCH', `/workflow/outputs/${outputId}`, approved
      ? { review_status: 'approved', edited_content: textarea ? textarea.value : undefined }
      : { review_status: 'rejected' });
    if (card) {
      card.innerHTML = `<div class="approval-card resolved">${
        approved ? '✅ Đã duyệt — quy trình đang chạy tiếp.'
                 : '🔄 Đã yêu cầu làm lại — bước trước đang chạy lại.'
      }</div>`;
    }
  } catch (e) {
    buttons.forEach(b => { b.disabled = false; });
    alert('Không gửi được quyết định duyệt: ' + (e?.message || e));
  }
}

function appendThinking(agentName, agentId, color) {
  const area = document.getElementById('meeting-messages');
  const el = document.createElement('div');
  el.className = 'message-row';
  el.id = `thinking-${agentId}`;
  const agentForThink = agents.find(x => x.name === agentName);
  el.innerHTML = `
    ${avatarHtml(agentForThink?.avatar_color || color, agentName, 'avatar-sm')}
    <div>
      <div class="message-sender" style="color:${color}">${esc(agentName)}${agentDeptSuffix(agentForThink)}</div>
      <div class="message-bubble agent-bubble" id="agent-msg-${agentId}" style="color:var(--muted);font-style:italic;">
        <span class="thinking-dots">thinking</span>
      </div>
    </div>`;
  area.appendChild(el);
  area.scrollTop = area.scrollHeight;
}

function appendAgentChunk(agentId, agentName, color, chunk) {
  const msgEl = document.getElementById(`agent-msg-${agentId}`);
  if (!msgEl) { appendMeetingMsg(agentName, chunk, color); return; }
  if (!msgEl.dataset.started) {
    // Bong bóng "thinking" có inline style italic/muted riêng — phải gỡ khi nội dung thật
    // bắt đầu stream vào, nếu không câu trả lời sẽ hiển thị khác font/màu so với tin nhắn
    // đã lưu (đọc lại từ lịch sử), gây cảm giác 2 kiểu chữ khác nhau không cần thiết (đã có
    // vạch phân tách thời gian để phân biệt lượt rồi, không cần phân biệt bằng font nữa).
    msgEl.removeAttribute('style');
    msgEl.innerHTML = '';
    msgEl.dataset.started = '1';
    msgEl.dataset.raw = '';
  }
  msgEl.dataset.raw += chunk;
  msgEl.innerHTML = marked.parse(_boldenMentions(msgEl.dataset.raw));
  const area = document.getElementById('meeting-messages');
  area.scrollTop = area.scrollHeight;
}

function finishAgentMessage(agentId) {
  const el = document.getElementById(`thinking-${agentId}`);
  if (el) el.removeAttribute('id');
  const msgEl = document.getElementById(`agent-msg-${agentId}`);
  if (msgEl) {
    msgEl.removeAttribute('id');
    if (!msgEl.parentElement.querySelector('.msg-time')) {
      msgEl.insertAdjacentHTML('afterend', `<div class="msg-time">${esc(_msgTimeLabel(new Date()))}</div>`);
    }
  }
}

// Gỡ hẳn bong bóng "đang xử lý" khi agent đó rốt cuộc không nói gì (vd Xanax chỉ mời
// nhân viên khác ra trả lời) — tránh kẹt trạng thái "thinking..." vĩnh viễn trên UI.
function removeThinking(agentId) {
  const el = document.getElementById(`thinking-${agentId}`);
  if (el && !document.getElementById(`agent-msg-${agentId}`)?.dataset.started) el.remove();
}

// ── @mention (gọi thẳng 1 nhân viên, bỏ qua bước Xanax cân nhắc) ──
// Xanax không nằm trong agent_configs (không phải 1 nhân viên) nhưng vẫn phải xuất hiện
// mặc định trong danh sách tag vì Xanax là người điều hành cuộc họp — CEO cần gọi lại
// quyền điều phối bất cứ lúc nào (xem addresses_xanax ở api/websocket_meeting.py).
const XANAX_MENTION_ENTRY = { id: 0, name: 'Xanax', role: 'Điều phối viên', avatar_color: 'var(--cyan)', department_name: null };
let mentionMatches = [], mentionActiveIndex = 0, mentionAtPos = -1;

function _mentionQueryAt(text, caret) {
  const uptoCaret = text.slice(0, caret);
  const at = uptoCaret.lastIndexOf('@');
  if (at === -1) return null;
  const query = uptoCaret.slice(at + 1);
  if (/\s/.test(query)) return null; // đã gõ qua khoảng trắng -> không còn đang gõ mention
  return { at, query };
}

export function handleMeetingInputChange(e) {
  const inp = e.target;
  const q = _mentionQueryAt(inp.value, inp.selectionStart);
  if (!q) { hideMentionDropdown(); return; }
  mentionAtPos = q.at;
  mentionMatches = [XANAX_MENTION_ENTRY, ...agents].filter(a => a.name.toLowerCase().includes(q.query.toLowerCase()));
  mentionActiveIndex = 0;
  if (!mentionMatches.length) { hideMentionDropdown(); return; }
  renderMentionDropdown();
}

function renderMentionDropdown() {
  const el = document.getElementById('mention-dropdown');
  el.innerHTML = mentionMatches.map((a, i) => `
    <div class="mention-item${i===mentionActiveIndex?' active':''}" onmousedown="event.preventDefault();selectMention(${i})">
      ${avatarHtml(a.avatar_color, a.name, 'avatar-sm')}
      <div><div class="mention-item-name">${esc(a.name)}${agentDeptSuffix(a)}</div><div class="mention-item-role">${esc(a.role)}</div></div>
    </div>`).join('');
  el.classList.remove('hidden');
}

function hideMentionDropdown() {
  mentionMatches = []; mentionAtPos = -1;
  const el = document.getElementById('mention-dropdown');
  el.classList.add('hidden');
  el.innerHTML = '';
}

function selectMention(index) {
  const a = mentionMatches[index];
  const inp = document.getElementById('meeting-input');
  if (!a || mentionAtPos === -1) return;
  const before = inp.value.slice(0, mentionAtPos);
  const after = inp.value.slice(inp.selectionStart);
  inp.value = `${before}@${a.name} ${after}`;
  const caret = before.length + a.name.length + 2;
  inp.focus();
  inp.setSelectionRange(caret, caret);
  hideMentionDropdown();
}

function _extractMentionTargets(content) {
  const lower = content.toLowerCase();
  return agents.filter(a => lower.includes(`@${a.name.toLowerCase()}`)).map(a => a.id);
}

export function sendMeetingMessage() {
  if (!currentMeetingWs || currentMeetingWs.readyState !== 1) return;
  const inp = document.getElementById('meeting-input');
  const content = inp.value.trim();
  if (!content) return;
  const targets = _extractMentionTargets(content);
  inp.value = '';
  hideMentionDropdown();
  currentMeetingWs.send(JSON.stringify({ type: 'user_message', content, targets }));
}

export function meetingInputKeydown(e) {
  if (mentionMatches.length) {
    if (e.key === 'ArrowDown') { e.preventDefault(); mentionActiveIndex = (mentionActiveIndex + 1) % mentionMatches.length; renderMentionDropdown(); return; }
    if (e.key === 'ArrowUp') { e.preventDefault(); mentionActiveIndex = (mentionActiveIndex - 1 + mentionMatches.length) % mentionMatches.length; renderMentionDropdown(); return; }
    if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); selectMention(mentionActiveIndex); return; }
    if (e.key === 'Escape') { hideMentionDropdown(); return; }
  }
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMeetingMessage(); }
}

export async function endMeeting() {
  if (!currentMeetingWs) return;
  if (!(await showConfirm('End this meeting?', 'Kết thúc'))) return;
  currentMeetingWs.send(JSON.stringify({ type: 'end_meeting' }));
}

export async function finalizeMeeting() {
  if (!currentMeetingId) return;
  const m = await api('GET', `/meetings/${currentMeetingId}`);
  openFinalizeModal(m.draft_minutes || '');
}

function openFinalizeModal(draftText) {
  document.getElementById('finalize-modal-text').value = draftText || '';
  document.getElementById('finalize-modal').classList.remove('hidden');
}

export async function confirmFinalizeMeeting() {
  if (!currentMeetingId) return;
  const decision = document.getElementById('finalize-modal-text').value.trim();
  if (!decision) { showToast('Vui lòng nhập nội dung biên bản.', 'error'); return; }
  try {
    const res = await api('POST', `/meetings/${currentMeetingId}/finalize`, { decision_text: decision });
    const n = (res.triggered_workflow_ids || []).length;
    const index = meetings.findIndex(m => m.id === currentMeetingId);
    if (index >= 0) meetings[index] = res;
    closeModal('finalize-modal');
    renderMeetingList();
    renderMeetingRecord(res);
    document.getElementById('meeting-finalize-btn').style.display = 'none';
    const proposals = (res.proposed_items || []).length;
    const triggerText = n ? ` Đã kích hoạt ${n} quy trình.` : '';
    const proposalText = proposals ? ` Xanax đã đề xuất ${proposals} công việc để bạn duyệt.` : '';
    showToast(`Đã chốt biên bản.${triggerText}${proposalText}`, 'success');
  } catch (e) { showToast('Lỗi khi chốt biên bản: ' + e.message, 'error'); }
}

// ════════════════════════════════════════
