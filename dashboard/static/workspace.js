marked.setOptions({ breaks: true, gfm: true });

// ── Bộ icon SVG dùng chung (thay toàn bộ emoji chức năng) ──────────────────────
const UI_ICONS = {
  bot: '<rect x="5" y="7" width="14" height="12" rx="5" /><circle cx="9.5" cy="12.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="14.5" cy="12.5" r="1.1" fill="currentColor" stroke="none"/><path d="M9.5 16c.8.6 3.2.6 4 0" /><line x1="12" y1="7" x2="12" y2="4.5"/><circle cx="12" cy="4" r="1" fill="currentColor" stroke="none"/>',
  warning: '<path d="M12 4l9 15.5H3L12 4z"/><line x1="12" y1="10" x2="12" y2="14"/><circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none"/>',
  check: '<path d="M4 12l5 5L20 6"/>',
  close: '<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>',
  bolt: '<path d="M13 3L6 14h5l-1 7 7-11h-5l1-7z" fill="currentColor" stroke="none"/>',
  send: '<path d="M4 12l16-8-6 16-3-6-7-2z"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
};
function icon(name, cls) {
  const inner = UI_ICONS[name] || UI_ICONS.bot;
  return `<svg class="icon${cls ? ' ' + cls : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">${inner}</svg>`;
}

// ── State ─────────────────────────────────────────────────────────────────────
let currentSessionId = null;
let ws = null;
let isStreaming = false;
let currentBubble = null;
let currentContent = '';
let streamTimer = null;

// ── Init ──────────────────────────────────────────────────────────────────────
(async function init() {
  const me = await fetch('/api/auth/me').then(r => r.ok ? r.json() : null);
  if (!me) { window.top.location.href = '/login'; return; }
  document.getElementById('username-display').textContent = me.username;
  await Promise.all([loadSessions(), loadAgentRoster()]);
})();

// ── Sessions ──────────────────────────────────────────────────────────────────
async function loadSessions() {
  const res = await fetch('/api/training/sessions');
  if (!res.ok) {
    document.getElementById('sessions-list').innerHTML =
      `<div style="padding:20px;text-align:center;color:var(--fail);font-size:12px;">Lỗi tải sessions (${res.status})</div>`;
    return;
  }
  const { sessions } = await res.json();
  renderSessionList(sessions);
}

function renderSessionList(sessions) {
  const list = document.getElementById('sessions-list');
  if (!sessions.length) {
    list.innerHTML = `<div style="padding:20px;text-align:center;color:var(--muted);font-size:12px;line-height:1.8;">
      Chưa có session nào.<br>Nhấn <strong>+</strong> để tạo mới.
    </div>`;
    return;
  }
  list.innerHTML = sessions.map(s => `
    <div class="session-item ${s.id === currentSessionId ? 'active' : ''}"
         onclick="selectSession(${s.id})">
      <div class="session-dot dot-${s.status}"></div>
      <div class="session-info">
        <div class="session-title">${esc(s.title)}</div>
        <div class="session-meta">${s.agent_name ? '👤 ' + esc(s.agent_name) + ' · ' : ''}${fmtDate(s.created_at)}</div>
      </div>
    </div>
  `).join('');
}

async function selectSession(id) {
  currentSessionId = id;

  const res = await fetch(`/api/training/sessions/${id}`);
  if (!res.ok) return;
  const session = await res.json();

  await loadSessions(); // refresh list to show active highlight

  // Info panel
  document.getElementById('info-empty').style.display  = 'none';
  document.getElementById('info-content').classList.add('visible');
  document.getElementById('info-title').value = session.title;
  document.getElementById('info-date').textContent = fmtDateFull(session.created_at);
  document.getElementById('info-task').value  = session.task_description;
  const notesEl = document.getElementById('info-notes');
  notesEl.value = session.result_notes;
  notesEl.classList.toggle('has-content', !!session.result_notes);
  renderBadge(session.status);
  // Phòng ĐÓNG hay chưa là chuyện khác với kết quả đánh giá. Bấm Hài lòng /
  // Cần cải thiện chỉ ghi verdict và dựng bản nháp đúc kết; phòng vẫn mở để
  // sửa. Chỉ nút "Lưu bài học kinh nghiệm" mới đóng.
  const isClosed = !!session.closed;
  document.querySelector('.btn-pass').disabled = isClosed;
  document.querySelector('.btn-fail').disabled = isClosed;
  document.getElementById('btn-feedback').disabled = isClosed;
  document.getElementById('btn-refine').disabled = isClosed;
  document.getElementById('info-notes').readOnly = isClosed;
  document.getElementById('btn-reopen').style.display = isClosed ? '' : 'none';

  // Chat area
  document.getElementById('chat-empty').style.display   = 'none';
  document.getElementById('chat-messages').style.display = 'flex';
  document.getElementById('chat-input-area').style.display = isClosed ? 'none' : 'block';

  renderStudentBar(session);

  const wrap = document.getElementById('chat-messages');
  wrap.innerHTML = '';
  (session.messages || []).forEach(m => appendMsg(m.role, m.content));
  scrollBottom();

  connectWS(id);
}

// ── Buổi dạy có học viên ─────────────────────────────────────────────────────

let currentStudent = null;   // { id, name } của phiên đang mở, null = dạy Xanax

function renderStudentBar(session) {
  currentStudent = session.agent_id
    ? { id: session.agent_id, name: session.agent_name || `#${session.agent_id}` }
    : null;
  renderCloseHint();
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
let _reconnectTimer = null;
let _reconnectCount = 0;
const _MAX_RECONNECT = 5;

function connectWS(sessionId) {
  if (ws) { ws.onclose = null; ws.close(); ws = null; }
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
  updateSendBtn(false);

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws/training`);

  ws.onopen = () => {
    _reconnectCount = 0;
    updateSendBtn(true);
    document.getElementById('hermes-banner').classList.remove('visible');
    document.getElementById('hermes-banner').textContent = 'Hermes offline — không thể gửi tin nhắn';
  };

  ws.onmessage = ({ data }) => {
    let msg;
    try { msg = JSON.parse(data); } catch { return; }
    if (msg.type === 'status')  { showTyping(); }
    else if (msg.type === 'chunk') { appendChunk(msg.content); }
    else if (msg.type === 'tool_executed') { applyToolResult(msg); }
    else if (msg.type === 'done')  { finalizeStream(); }
    else if (msg.type === 'status') {
      if (['summarising', 'analysing', 'improving'].includes(msg.status)) showNotesSpinner(true);
    }
    else if (msg.type === 'notes_updated') { updateNotes(msg.content, 'pass'); }
    else if (msg.type === 'failure_analysed') { updateNotes(msg.content, 'fail'); }
    else if (msg.type === 'error') { finalizeStream(); showNotesSpinner(false); toast('Lỗi: ' + msg.message, 'error'); }
  };

  ws.onerror = () => {
    updateSendBtn(false);
  };

  ws.onclose = async (ev) => {
    updateSendBtn(false);
    if (isStreaming) finalizeStream();

    // Don't reconnect if we deliberately closed (no currentSessionId)
    if (!currentSessionId) return;

    // Check auth before attempting reconnect — server restart clears sessions
    const authOk = await fetch('/api/health').then(r => r.status !== 401).catch(() => true);
    if (!authOk) { window.top.location.href = '/login'; return; }

    if (_reconnectCount < _MAX_RECONNECT) {
      _reconnectCount++;
      const delay = Math.min(1000 * _reconnectCount, 5000);
      const banner = document.getElementById('hermes-banner');
      banner.textContent = `Mất kết nối — thử lại sau ${delay/1000}s... (${_reconnectCount}/${_MAX_RECONNECT})`;
      banner.classList.add('visible');
      _reconnectTimer = setTimeout(() => connectWS(currentSessionId), delay);
    } else {
      const banner = document.getElementById('hermes-banner');
      banner.textContent = 'Mất kết nối — tải lại trang để thử lại';
      banner.classList.add('visible');
    }
  };
}

// ── Chat ──────────────────────────────────────────────────────────────────────
function sendMessage() {
  if (!currentSessionId || !ws || ws.readyState !== WebSocket.OPEN || isStreaming) return;
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  appendMsg('user', text);
  scrollBottom();
  input.value = '';
  input.style.height = 'auto';
  updateSendBtn(false);

  ws.send(JSON.stringify({ training_session_id: currentSessionId, message: text }));

  if (streamTimer) clearTimeout(streamTimer);
  streamTimer = setTimeout(() => { if (isStreaming) finalizeStream(); }, 90_000);
}

function showTyping() {
  isStreaming = true;
  currentContent = '';
  const wrap = document.getElementById('chat-messages');
  const row = document.createElement('div');
  row.className = 'msg msg-assistant';
  row.id = 'streaming-msg';
  row.innerHTML = `<div class="msg-avatar">${icon('bot')}</div>
    <div class="msg-bubble">
      <div class="typing-indicator"><span></span><span></span><span></span></div>
    </div>`;
  wrap.appendChild(row);
  currentBubble = row.querySelector('.msg-bubble');
  scrollBottom();
}

function appendChunk(chunk) {
  if (!currentBubble) showTyping();
  currentContent += chunk;
  currentBubble.innerHTML = marked.parse(currentContent);
  scrollBottom();
}

function finalizeStream() {
  isStreaming = false;
  if (streamTimer) { clearTimeout(streamTimer); streamTimer = null; }
  const row = document.getElementById('streaming-msg');
  if (row) row.removeAttribute('id');
  currentBubble = null;
  currentContent = '';
  updateSendBtn(ws && ws.readyState === WebSocket.OPEN);
  scrollBottom();
}

function applyToolResult(msg) {
  // Replace streamed content (which may contain raw [[XANAX:...]] blocks) with clean text
  if (currentBubble && msg.clean_text !== undefined) {
    currentContent = msg.clean_text;
    currentBubble.innerHTML = marked.parse(currentContent);
  }
  // Show tool execution results as a separate bubble
  if (msg.results && msg.results.length) {
    const wrap = document.getElementById('chat-messages');
    const row = document.createElement('div');
    row.className = 'msg msg-tool';
    const items = msg.results.map(r =>
      `<div class="tool-result-item ${r.ok ? 'ok' : 'err'}">
        ${r.ok ? icon('check') : icon('close')} <strong>${esc(r.action)}</strong>: ${esc(r.message || r.error || '')}
      </div>`
    ).join('');
    row.innerHTML = `<div class="msg-avatar">${icon('bolt')}</div><div class="msg-bubble tool-results">${items}</div>`;
    wrap.appendChild(row);
    scrollBottom();
  }
}

function appendMsg(role, content) {
  const wrap = document.getElementById('chat-messages');
  const row = document.createElement('div');
  row.className = `msg msg-${role}`;
  const av = role === 'user' ? 'P' : icon('bot');
  const html = role === 'assistant'
    ? marked.parse(content)
    : esc(content).replace(/\n/g, '<br>');
  row.innerHTML = `<div class="msg-avatar">${av}</div><div class="msg-bubble">${html}</div>`;
  wrap.appendChild(row);
}

function scrollBottom() {
  const w = document.getElementById('chat-messages');
  w.scrollTop = w.scrollHeight;
}

function updateSendBtn(enabled) {
  document.getElementById('btn-send').disabled = !enabled;
  document.getElementById('chat-input').disabled = !enabled;
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

// ── Session info ──────────────────────────────────────────────────────────────
function renderBadge(status) {
  const labels = { in_progress: '<span class="sdot on"></span>Đang thực hiện', pass: icon('check') + ' Đạt', fail: icon('close') + ' Không đạt' };
  document.getElementById('status-badge').innerHTML =
    `<span class="status-badge status-${status}">${labels[status] || status}</span>`;
}

async function saveField(field, value) {
  if (!currentSessionId) return;
  const body = {};
  if (field === 'title')            body.title = value;
  if (field === 'task_description') body.task_description = value;
  if (field === 'result_notes')     body.result_notes = value;
  const res = await fetch(`/api/training/sessions/${currentSessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (res.ok) { await loadSessions(); toast('Đã lưu', 'success'); }
  else toast('Lỗi khi lưu', 'error');
}

async function setStatus(status) {
  if (!currentSessionId) return;
  const res = await fetch(`/api/training/sessions/${currentSessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) return;

  // KHÔNG đóng phòng ở đây: chat vẫn mở, hai nút vẫn bấm được để đổi kết quả.
  // Việc duy nhất còn lại là dựng BẢN NHÁP đúc kết cho Papa sửa.
  renderBadge(status);
  await loadSessions();
  renderCloseHint();

  if (currentStudent) {
    // Buổi dạy có học viên: đúc kết bằng /distill rồi đổ vào ô cho Papa sửa.
    // Không dùng đường summarise của WS vì đường đó ghi thẳng SOUL.md của
    // Xanax — sai sổ, đây là bài học của nhân viên.
    showNotesSpinner(true);
    try {
      const r = await fetch(`/api/training/sessions/${currentSessionId}/distill`, { method: 'POST' });
      const d = await r.json();
      if (!r.ok) { toast(d.detail || 'Không đúc kết được', 'error'); return; }
      const lessons = d.lessons || [];
      updateNotes(lessons.map(x => `- ${x}`).join('\n'), 'draft');
      toast(lessons.length
        ? `Đã đúc kết ${lessons.length} bài học — sửa lại rồi bấm "Lưu bài học kinh nghiệm"`
        : 'Chưa rút được bài học nào — bạn có thể tự viết vào ô đúc kết', 'success');
    } finally {
      showNotesSpinner(false);
    }
    return;
  }

  if (ws && ws.readyState === WebSocket.OPEN) {
    showNotesSpinner(true);
    const action = status === 'pass' ? 'summarise_pass' : 'summarise_fail';
    ws.send(JSON.stringify({ action, session_id: currentSessionId }));
    toast(status === 'pass' ? 'Đã ghi nhận — đang đúc kết bài học...' : 'Đã ghi nhận — đang phân tích để cải thiện...', status === 'pass' ? 'success' : 'error');
  } else {
    toast(status === 'pass' ? 'Đã đánh dấu Đạt' : 'Đã đánh dấu Không đạt', status === 'pass' ? 'success' : 'error');
  }
}

// ── Đóng / mở lại buổi học ───────────────────────────────────────────────────

function renderCloseHint() {
  const el = document.getElementById('close-hint');
  if (!el) return;
  el.textContent = currentStudent
    ? `Sửa xong phần đúc kết rồi bấm nút dưới — mỗi dòng thành một bài học trong soul của ${currentStudent.name}, và buổi học mới đóng.`
    : 'Sửa xong phần đúc kết rồi bấm nút dưới để chốt và đóng buổi học.';
}

async function closeLesson() {
  if (!currentSessionId) return;
  const notes = document.getElementById('info-notes').value;
  const btn = document.getElementById('btn-feedback');
  btn.disabled = true;
  try {
    const r = await fetch(`/api/training/sessions/${currentSessionId}/close`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    const d = await r.json();
    if (!r.ok) { toast(d.detail || 'Không đóng được buổi học', 'error'); return; }
    await loadSessions();
    await selectSession(currentSessionId);
    toast(d.written
      ? `Đã ghi ${d.written} bài học vào soul của ${d.agent_name} — buổi học đã đóng`
      : 'Đã đóng buổi học', 'success');
  } finally {
    btn.disabled = false;
  }
}

async function reopenLesson() {
  if (!currentSessionId) return;
  const r = await fetch(`/api/training/sessions/${currentSessionId}/reopen`, { method: 'POST' });
  if (!r.ok) { toast('Không mở lại được', 'error'); return; }
  await loadSessions();
  await selectSession(currentSessionId);
  toast('Đã mở lại buổi học', 'success');
}

function showNotesSpinner(visible) {
  document.getElementById('notes-spinner').style.display = visible ? 'inline-block' : 'none';
}

function updateNotes(content, verdict) {
  showNotesSpinner(false);
  const el = document.getElementById('info-notes');
  el.value = content;
  el.classList.add('has-content');

  // 'draft' = bản nháp cho buổi dạy có học viên; toast do bên gọi tự lo.
  if (verdict === 'draft') return;
  if (verdict === 'pass') {
    toast('Đã đúc kết xong — sửa lại nếu cần rồi bấm "Lưu bài học kinh nghiệm"', 'success');
  } else if (verdict === 'fail') {
    toast('Đã phân tích xong — sửa lại nếu cần rồi bấm "Lưu bài học kinh nghiệm"', 'error');
  } else {
    toast('Đã đúc kết lại từ góp ý — kiểm tra rồi bấm "Lưu bài học kinh nghiệm"', 'success');
  }
}

function openFeedbackPopup() {
  document.getElementById('popup-feedback').value = '';
  document.getElementById('feedback-popup').classList.add('visible');
  setTimeout(() => document.getElementById('popup-feedback').focus(), 50);
}

function closeFeedbackPopup(e) {
  if (e && e.target !== document.getElementById('feedback-popup')) return;
  document.getElementById('feedback-popup').classList.remove('visible');
}

function submitFeedbackPopup() {
  if (!currentSessionId) return;
  const feedback = document.getElementById('popup-feedback').value.trim();
  document.getElementById('feedback-popup').classList.remove('visible');
  if (!ws || ws.readyState !== WebSocket.OPEN) { toast('Chưa kết nối WebSocket', 'error'); return; }
  showNotesSpinner(true);
  if (feedback) {
    ws.send(JSON.stringify({ action: 'improve_from_fail', session_id: currentSessionId, feedback }));
    toast('Đang đúc kết từ góp ý...', '');
  } else {
    ws.send(JSON.stringify({ action: 'summarise_pass', session_id: currentSessionId }));
    toast('Đang đúc kết tự động...', '');
  }
}

let _confirmCallback = null;
function showConfirmPopup(msg, onConfirm) {
  document.getElementById('confirm-msg').textContent = msg;
  _confirmCallback = onConfirm;
  const btn = document.getElementById('confirm-ok-btn');
  btn.onclick = () => { const cb = _confirmCallback; closeConfirmPopup(); cb && cb(); };
  document.getElementById('confirm-popup').classList.add('visible');
}
function closeConfirmPopup() {
  document.getElementById('confirm-popup').classList.remove('visible');
  _confirmCallback = null;
}

async function deleteCurrentSession() {
  if (!currentSessionId) return;
  showConfirmPopup('Xoá session này? Hành động không thể hoàn tác.', async () => {
    const res = await fetch(`/api/training/sessions/${currentSessionId}`, { method: 'DELETE' });
    if (res.ok) {
      currentSessionId = null;
      _reconnectCount = _MAX_RECONNECT;
      if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
      document.getElementById('info-content').classList.remove('visible');
      document.getElementById('info-empty').style.display = 'flex';
      document.getElementById('chat-empty').style.display = 'flex';
      document.getElementById('chat-messages').style.display = 'none';
      document.getElementById('chat-input-area').style.display = 'none';
      document.getElementById('hermes-banner').classList.remove('visible');
      if (ws) { ws.onclose = null; ws.close(); ws = null; }
      await loadSessions();
      toast('Đã xoá session', 'success');
    }
  });
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function openNewSession() {
  document.getElementById('new-title').value = '';
  document.getElementById('new-task').value  = '';
  document.getElementById('modal-overlay').classList.add('visible');
  setTimeout(() => document.getElementById('new-title').focus(), 50);
}

function closeNewSession() {
  document.getElementById('modal-overlay').classList.remove('visible');
}

function closeModal(e) {
  if (e.target === document.getElementById('modal-overlay')) closeNewSession();
}

// ── Học viên của buổi dạy ────────────────────────────────────────────────────
// Danh sách nhân viên nạp một lần, dùng cho ô chọn lúc tạo phòng.
let agentRoster = [];

async function loadAgentRoster() {
  try {
    const res = await fetch('/api/agent-configs/');
    if (!res.ok) return;
    agentRoster = (await res.json()).agents || [];
  } catch { /* mất mạng — ô chọn vẫn dùng được với mỗi lựa chọn Xanax */ }

  const sel = document.getElementById('new-agent');
  if (!sel) return;
  sel.innerHTML = '<option value="">Dạy chính Xanax (như trước)</option>' +
    agentRoster.map(a =>
      `<option value="${a.id}">${esc(a.name)}${a.role ? ' — ' + esc(a.role) : ''}</option>`
    ).join('');
}

async function createSession() {
  const title = document.getElementById('new-title').value.trim();
  if (!title) { document.getElementById('new-title').focus(); return; }
  const task  = document.getElementById('new-task').value.trim();
  const agentId = document.getElementById('new-agent').value;
  const res = await fetch('/api/training/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title,
      task_description: task,
      agent_id: agentId ? parseInt(agentId) : null,
    }),
  });
  if (!res.ok) { toast('Không tạo được session', 'error'); return; }
  const session = await res.json();
  closeNewSession();
  await loadSessions();
  await selectSession(session.id);
  toast('Đã tạo phiên dạy học mới', 'success');
}

// ── Auth ──────────────────────────────────────────────────────────────────────
async function logout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.top.location.href = '/login';
}

setInterval(async () => {
  try {
    const r = await fetch('/api/auth/me');
    if (r.status === 401) window.top.location.href = '/login';
  } catch (_) {}
}, 5000);

// ── Helpers ───────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  return d.toLocaleDateString('vi-VN');
}

function fmtDateFull(iso) {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  return d.toLocaleString('vi-VN');
}

let toastTimer;
function toast(msg, type='') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show' + (type ? ' ' + type : '');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = 'toast'; }, 2800);
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeNewSession();
    document.getElementById('feedback-popup').classList.remove('visible');
    closeConfirmPopup();
  }
  if (e.key === 'Enter'
      && document.getElementById('modal-overlay').classList.contains('visible')
      && document.activeElement === document.getElementById('new-title')) {
    createSession();
  }
});

// ── Idle timeout (15 min, paused while streaming) ─────────────────────────────
const IDLE_MS = 15 * 60 * 1000;
let _idleTimer = null;

function _resetIdle() {
  if (_idleTimer) clearTimeout(_idleTimer);
  _idleTimer = setTimeout(async () => {
    if (isStreaming) { _resetIdle(); return; }
    await fetch('/api/auth/logout', { method: 'POST' });
    window.top.location.href = '/login?reason=idle';
  }, IDLE_MS);
}

['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'].forEach(ev =>
  document.addEventListener(ev, _resetIdle, { passive: true })
);
_resetIdle();

// Hide chrome when embedded in hub
if (new URLSearchParams(location.search).get('embed') === '1') {
  document.head.insertAdjacentHTML('beforeend',
    '<style>.topbar,.page-footer{display:none!important}#main{height:100vh!important}</style>'
  );
}

// ── Theme sync với hub (light/dark) ───────────────────────────────────────
function _applyTheme(theme) {
  document.body.classList.toggle('light', theme === 'light');
}
_applyTheme(localStorage.getItem('hub_theme') || 'light');
window.addEventListener('storage', e => {
  if (e.key === 'hub_theme') _applyTheme(e.newValue || 'light');
});
