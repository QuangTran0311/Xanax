// ════════════════════════════════════════
// Bộ icon SVG dùng chung cho UI chrome (khác với ICONS bên dưới — đó là icon
// cho từng loại node trong palette, giữ nguyên hệ thống riêng của nó)
// ════════════════════════════════════════
const UI_ICONS = {
  bolt: '<path d="M13 3L6 14h5l-1 7 7-11h-5l1-7z" fill="currentColor" stroke="none"/>',
  workflow: '<circle cx="5" cy="6" r="2" fill="currentColor" stroke="none"/><circle cx="19" cy="6" r="2" fill="currentColor" stroke="none"/><circle cx="12" cy="18" r="2" fill="currentColor" stroke="none"/><path d="M7 6h10"/><path d="M12 8v6"/>',
  scale: '<path d="M12 3v18"/><path d="M5 7h14"/><path d="M5 7l-2.5 6a2.5 2.5 0 005 0L5 7z"/><path d="M19 7l-2.5 6a2.5 2.5 0 005 0L19 7z"/>',
  brain: '<path d="M9 4a3 3 0 00-3 3v1a3 3 0 000 6v1a3 3 0 003 3M15 4a3 3 0 013 3v1a3 3 0 010 6v1a3 3 0 01-3 3M9 4v16M15 4v16"/>',
  folder: '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>',
  arrowDown: '<line x1="12" y1="5" x2="12" y2="18"/><path d="M7 13.5L12 18 17 13.5"/>',
};
function icon(name, cls) {
  const inner = UI_ICONS[name] || UI_ICONS.bolt;
  return `<svg class="icon${cls ? ' ' + cls : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">${inner}</svg>`;
}

function showToast(message, type = 'info', duration = 3200) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = String(message || '');
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('visible'));
  setTimeout(() => {
    toast.classList.remove('visible');
    setTimeout(() => toast.remove(), 220);
  }, duration);
}

let _confirmResolver = null;
function showConfirm(message, options = {}) {
  if (_confirmResolver) _confirmResolver(false);
  const modal = document.getElementById('confirm-modal');
  if (modal.parentElement !== document.body) document.body.appendChild(modal);
  document.getElementById('confirm-modal-title').textContent = options.title || 'Xác nhận';
  document.getElementById('confirm-modal-desc').textContent = message;
  const action = document.getElementById('confirm-modal-action');
  action.textContent = options.confirmLabel || 'Xác nhận';
  action.classList.toggle('danger', options.danger !== false);
  modal.style.display = 'flex';
  return new Promise(resolve => { _confirmResolver = resolve; });
}

function resolveConfirmModal(result) {
  document.getElementById('confirm-modal').style.display = 'none';
  const resolve = _confirmResolver;
  _confirmResolver = null;
  if (resolve) resolve(Boolean(result));
}

function closeConfirmModal() {
  resolveConfirmModal(false);
}

let _workflowInputResolver = null;
function requestWorkflowInput(isTest) {
  if (_workflowInputResolver) _workflowInputResolver(null);
  document.getElementById('workflow-input-title').textContent =
    isTest ? 'Dữ liệu đầu vào cho lần chạy thử' : 'Yêu cầu đầu vào cho quy trình';
  const input = document.getElementById('workflow-input-value');
  input.value = '';
  document.getElementById('workflow-input-modal').style.display = 'flex';
  setTimeout(() => input.focus(), 0);
  return new Promise(resolve => { _workflowInputResolver = resolve; });
}

function resolveWorkflowInputModal() {
  const value = document.getElementById('workflow-input-value').value;
  document.getElementById('workflow-input-modal').style.display = 'none';
  const resolve = _workflowInputResolver;
  _workflowInputResolver = null;
  if (resolve) resolve(value);
}

function closeWorkflowInputModal() {
  document.getElementById('workflow-input-modal').style.display = 'none';
  const resolve = _workflowInputResolver;
  _workflowInputResolver = null;
  if (resolve) resolve(null);
}

// ── Popup chờ duyệt (node Cổng Duyệt) ─────────────────────────────────────
let _approvalQueue = [];
let _activeApproval = null;

function openApprovalModal(message) {
  _approvalQueue.push(message);
  if (!_activeApproval) _showNextApproval();
}

function _showNextApproval() {
  _activeApproval = _approvalQueue.shift() || null;
  if (!_activeApproval) return;
  const approver = _activeApproval.approver || 'CEO';
  document.getElementById('approval-modal-title').textContent = `Chờ ${approver} duyệt`;
  document.getElementById('approval-modal-title').dataset.approver = approver;
  const noteEl = document.getElementById('approval-modal-note');
  if (_activeApproval.note) { noteEl.textContent = _activeApproval.note; noteEl.style.display = ''; }
  else noteEl.style.display = 'none';
  // Ảnh hiện thật, không hiện link markdown.
  const imgWrap = document.getElementById('approval-modal-images');
  const images = _activeApproval.images || [];
  if (images.length) {
    imgWrap.innerHTML = images.map(url =>
      `<img src="${url}" alt="Ảnh bài đăng" style="max-width:100%;max-height:320px;border-radius:8px;border:1px solid var(--border,#334155)">`
    ).join('');
    imgWrap.style.display = '';
  } else {
    imgWrap.innerHTML = '';
    imgWrap.style.display = 'none';
  }
  document.getElementById('approval-modal-content').value = _activeApproval.content || '';
  document.getElementById('approval-modal').style.display = 'flex';
}

async function resolveApprovalModal(approved) {
  if (!_activeApproval) return;
  const outputId = _activeApproval.output_id;
  const editedContent = document.getElementById('approval-modal-content').value;
  document.getElementById('approval-modal').style.display = 'none';
  try {
    await runnerApi('PATCH', `/workflow/outputs/${outputId}`, approved
      ? { review_status: 'approved', edited_content: editedContent }
      : { review_status: 'rejected' });
  } catch (error) {
    showToast(`Không thể gửi quyết định duyệt: ${error.message}`, 'error');
  }
  _showNextApproval();
}

let REAL_TASKS = [];

const STATUS_LABEL = { active: 'Đang bật', paused: 'Tạm dừng', draft: 'Nháp', failed: 'Thất bại' };

const FILTERS = [
  { key: 'all',    label: 'Tất cả',    icon: '<path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"/>' },
  { key: 'active', label: 'Đang bật',  icon: '<polygon points="6 3 20 12 6 21 6 3"/>' },
  { key: 'paused', label: 'Tạm dừng',  icon: '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>' },
  { key: 'draft',  label: 'Nháp',      icon: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>' },
  { key: 'failed', label: 'Thất bại',  icon: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>' },
];

const urlParams = new URLSearchParams(location.search);
let currentMainTab = urlParams.get('tab') || 'company';
let currentStatus = 'all';
let searchQuery = '';

function wfNoun(cap) {
  const isAutomation = currentMainTab === 'automation';
  if (cap) return isAutomation ? 'Tác vụ' : 'Quy trình';
  return isAutomation ? 'tác vụ' : 'quy trình';
}

function updateMainTabLabels() {
  document.getElementById('search-input').placeholder = `Tìm ${wfNoun()}...`;
  document.getElementById('add-workflow-btn').lastChild.textContent = ` ${wfNoun(true)} Mới`;
}

function rateClass(v) {
  if (v >= 80) return 'good';
  if (v >= 50) return 'warn';
  return 'bad';
}

async function switchMainTab(tabKey) {
  currentMainTab = tabKey;
  document.querySelectorAll('.main-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.id === `btn-tab-${tabKey}`);
  });
  currentStatus = 'all';
  updateMainTabLabels();
  await loadWorkflowList();
}

function renderFilterTabs() {
  const wrap = document.getElementById('filter-tabs');
  const activeList = REAL_TASKS;
  wrap.innerHTML = FILTERS.map(f => {
    const count = f.key === 'all' ? activeList.length : activeList.filter(w => w.status === f.key).length;
    return `<button class="filter-tab ${f.key === currentStatus ? 'active' : ''}" data-key="${f.key}" onclick="setStatusFilter('${f.key}')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${f.icon}</svg>
      ${f.label} <span class="count">${count}</span>
    </button>`;
  }).join('');
}

function setStatusFilter(key) {
  currentStatus = key;
  renderFilterTabs();
  renderGrid();
}

function renderFlow(flow) {
  return `<div class="wf-flow">` + flow.map((s, i) => {
    const color = s.color || 'var(--text3)';
    const node = `<div class="wf-flow-node" title="${s.title || ''}" style="background:${color}"></div>`;
    const line = i < flow.length - 1 ? `<div class="wf-flow-line" style="background:${color}"></div>` : '';
    return node + line;
  }).join('') + `</div>`;
}

function renderFooterButtons(w) {
  const runBtn = `<button class="wf-btn primary" onclick="event.stopPropagation();runTaskFromCard(${w.id})">
    <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 3 20 12 6 21 6 3"/></svg> Chạy
  </button>`;
  const toggleBtn = w.status === 'active'
    ? `<button class="wf-btn" onclick="event.stopPropagation();toggleTaskStatus(${w.id},'paused')">
        <svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Tạm Dừng
      </button>`
    : `<button class="wf-btn" onclick="event.stopPropagation();toggleTaskStatus(${w.id},'active')">
        <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 3 20 12 6 21 6 3"/></svg> Bật
      </button>`;
  return `
    ${runBtn}
    ${toggleBtn}
    <button class="wf-btn" onclick="event.stopPropagation();openEditor(${w.id})">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg> Chỉnh Sửa
    </button>
    <button class="wf-btn icon-only" title="Lịch sử" onclick="event.stopPropagation();openRunHistory(${w.id})">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/></svg>
    </button>
    <button class="wf-btn icon-only danger" title="Xoá" onclick="event.stopPropagation();deleteWorkflowTask(${w.id})">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
    </button>
  `;
}

function renderGrid() {
  const activeList = REAL_TASKS;
  let items = currentStatus === 'all' ? activeList : activeList.filter(w => w.status === currentStatus);
  if (searchQuery.trim()) {
    const q = searchQuery.trim().toLowerCase();
    items = items.filter(w => w.name.toLowerCase().includes(q));
  }
  const grid = document.getElementById('workflow-grid');

  if (!items.length) {
    const trulyEmpty = !REAL_TASKS.length && currentStatus === 'all' && !searchQuery.trim();
    grid.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">${icon('folder')}</div>
      <div class="empty-state-text">${trulyEmpty ? `Chưa có ${wfNoun()} nào — tạo cái đầu tiên của bạn` : `Không tìm thấy ${wfNoun()} phù hợp`}</div>
      ${trulyEmpty ? `<button class="wf-btn primary" style="margin-top:12px" onclick="openCreateWorkflowModal()">+ Tạo ${wfNoun()}</button>` : ''}
    </div>`;
    return;
  }

  grid.innerHTML = items.map(w => `
    <div class="workflow-card" onclick="openEditor(${w.id})">
      <div class="wf-card-top">
        <div class="wf-name">${w.name}</div>
        <div class="wf-status ${w.status}"><span class="dot"></span>${STATUS_LABEL[w.status]}</div>
      </div>
      <div class="wf-desc">${w.desc}</div>
      ${renderFlow(w.flow)}
      <div class="wf-stats">
        <div class="wf-stat">
          <span class="wf-stat-label">Tỷ lệ thành công</span>
          <span class="wf-stat-value ${w.totalRuns ? rateClass(w.successRate) : 'muted'}">${w.totalRuns ? w.successRate + '%' : '—'}</span>
        </div>
        <div class="wf-stat">
          <span class="wf-stat-label">Tổng lần chạy</span>
          <span class="wf-stat-value neutral">${w.totalRuns}</span>
        </div>
        <div class="wf-stat">
          <span class="wf-stat-label">Lần chạy cuối</span>
          <span class="wf-stat-value muted">${w.lastRun}</span>
        </div>
      </div>
      ${w.schedule ? `<div class="wf-schedule"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/></svg>${w.schedule}</div>` : ''}
      <div class="wf-footer">${renderFooterButtons(w)}</div>
    </div>
  `).join('');
}

document.getElementById('search-input').addEventListener('input', e => {
  searchQuery = e.target.value;
  renderGrid();
});

// ════════════════════════════════════════
// EDITOR — templates khởi tạo & rendering
// ════════════════════════════════════════
const ICONS = {
  play:    '<polygon points="6 3 20 12 6 21 6 3"/>',
  globe:   '<circle cx="12" cy="12" r="9"/><line x1="3" y1="12" x2="21" y2="12"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18"/>',
  doc:     '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
  chat:    '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  robot:   '<rect x="4" y="7" width="16" height="13" rx="2"/><path d="M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3"/><line x1="9" y1="13" x2="9" y2="14"/><line x1="15" y1="13" x2="15" y2="14"/><line x1="9" y1="17" x2="15" y2="17"/>',
  branch:  '<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="12" r="2.5"/><path d="M8.2 7.2 15.8 10.8"/><path d="M8.2 16.8 15.8 13.2"/>',
  image:   '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
  person:  '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/>',
  stop:    '<rect x="5" y="5" width="14" height="14" rx="2"/>',
  filter:  '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
  db:      '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5"/><path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3"/>',
  code:    '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
  layers:  '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
  box:     '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
  clock:   '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>',
  octagon: '<polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
  book:    '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  api:     '<path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/><path d="M12 3v14"/><path d="M6 9l6-6 6 6"/>',
  x:       '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  shuffle: '<polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/>',
  sliders: '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
  link:    '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  external:'<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
  trash:   '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
};

function svgIcon(inner, filled) {
  return `<svg viewBox="0 0 24 24" fill="${filled ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;
}

const PALETTE_AUTOMATION = [
  { name: 'AI', items: [
    { name: 'Nhân viên AI', desc: 'Giao việc cho nhân viên AI thực hiện', color: '#3b82f6', icon: ICONS.robot },
    { name: 'Biến Đổi AI', desc: 'Chuyển đổi dữ liệu với AI', color: '#3b82f6', icon: ICONS.shuffle },
    { name: 'Tóm Tắt', desc: 'Tóm tắt nội dung dài', color: 'var(--cyan)', icon: ICONS.doc },
    { name: 'Trích Xuất Thông Tin', desc: 'Trích xuất thông tin dạng cấu trúc', color: 'var(--cyan)', icon: ICONS.layers },
    { name: 'Phân Tích Cảm Xúc', desc: 'Phân tích cảm xúc văn bản', color: 'var(--cyan)', icon: ICONS.chat },
  ]},
  { name: 'Dữ liệu', items: [
    { name: 'Đặt / Sửa Dữ Liệu', desc: 'Tạo hoặc cập nhật dữ liệu', color: '#f59e0b', icon: ICONS.db },
    { name: 'Lọc', desc: 'Lọc dữ liệu theo điều kiện', color: '#22c55e', icon: ICONS.filter },
    { name: 'Code (JS)', desc: 'Chạy mã JavaScript', color: '#8892a4', icon: ICONS.code },
  ]},
  { name: 'Luồng', items: [
    { name: 'Nếu / Thì', desc: 'Rẽ nhánh theo điều kiện', color: 'var(--purple)', icon: ICONS.branch },
    { name: 'Lệnh Thêm', desc: 'Thực hiện nhiều nhánh', color: 'var(--purple)', icon: ICONS.layers },
    { name: 'Chờ', desc: 'Tạm dừng trong khoảng thời gian', color: '#f59e0b', icon: ICONS.clock },
    { name: 'Dừng & Báo Lỗi', desc: 'Dừng workflow và báo lỗi', color: '#ef4444', icon: ICONS.octagon },
  ]},
  { name: 'Công cụ', items: [
    { name: 'Tra Cứu Web', desc: 'Tìm kiếm thông tin trên web', color: '#3b82f6', icon: ICONS.globe },
    { name: 'Tạo Ảnh AI', desc: 'Tạo ảnh bằng AI', color: '#ec4899', icon: ICONS.image },
    { name: 'Tri Thức (RAG)', desc: 'Truy vấn tri thức nội bộ', color: 'var(--cyan)', icon: ICONS.book },
    { name: 'Gọi API (HTTP)', desc: 'Gọi API bên ngoài', color: '#8892a4', icon: ICONS.api },
    { name: 'Không Làm Gì', desc: 'Bỏ qua bước này', color: '#8892a4', icon: ICONS.x },
  ]},
  { name: 'Duyệt', items: [
    { name: 'Cổng Duyệt', desc: 'Popup cho CEO xem/sửa nội dung bước trước — duyệt để đi tiếp, từ chối để chạy lại bước trước', color: '#f59e0b', icon: ICONS.person },
  ]},
  { name: 'Khung', items: [
    { name: 'Bắt Đầu', desc: 'Điểm bắt đầu workflow', color: '#22c55e', icon: ICONS.play },
    { name: 'Kết Thúc', desc: 'Kết thúc workflow', color: '#ef4444', icon: ICONS.stop },
  ]},
];

const PALETTE_COMPANY = [
  { name: 'Hành động', items: [
    { name: 'Soạn thảo văn bản', desc: 'Tạo tài liệu, hợp đồng, tờ trình', color: '#3b82f6', icon: ICONS.doc },
    { name: 'Thẩm định hồ sơ', desc: 'Kiểm tra, đối chiếu thông tin pháp lý/tài chính', color: 'var(--purple)', icon: ICONS.sliders },
    { name: 'Phê duyệt / Ký nhận', desc: 'Popup cho người duyệt xem/sửa nội dung bước trước — duyệt để đi tiếp, từ chối để chạy lại bước trước', color: '#f59e0b', icon: ICONS.person },
    { name: 'Gửi thông báo', desc: 'Gửi email hoặc tin nhắn SMS cho KH/đối tác', color: 'var(--cyan)', icon: ICONS.api },
    { name: 'Điều chỉnh yêu cầu', desc: 'Yêu cầu phòng ban soạn lại hồ sơ', color: '#ef4444', icon: ICONS.x },
  ]},
  { name: 'Luồng Quy trình', items: [
    { name: 'Điểm Bắt đầu', desc: 'Sự kiện khởi đầu quy trình', color: '#22c55e', icon: ICONS.play },
    { name: 'Cổng rẽ nhánh', desc: 'Rẽ nhánh công việc theo kết quả phê duyệt', color: 'var(--purple)', icon: ICONS.branch },
    { name: 'Chờ phản hồi', desc: 'Tạm dừng chờ phản hồi từ khách hàng hoặc SLA', color: '#64748b', icon: ICONS.clock },
    { name: 'Tác vụ', desc: 'Gọi một quy trình/tác vụ tự động khác đã có', color: '#3b82f6', icon: ICONS.box },
    { name: 'Điểm Kết thúc', desc: 'Hoàn thành và đóng quy trình', color: '#ef4444', icon: ICONS.stop },
  ]},
];

let EDITOR_NODES = [];
let EDITOR_EDGES = [];
let currentWorkflowId = null;
let currentWorkflowRecord = null;
let workflowProjects = [];
let builderAgents = [];
let builderSkills = [];
let builderTools = [];
let builderWorkflows = [];
let workflowSocket = null;
let activeRunId = null;
let activeNodeId = null;
let _openTriggerRow = null;

const NODE_META = {
  trigger: {title:'Bắt đầu', desc:'Điểm khởi động — chọn cách kích hoạt quy trình', color:'#22c55e', icon:ICONS.play, kind:'start'},
  agent: {title:'Nhân viên AI', desc:'Nhân viên AI xử lý nội dung ở bước này', color:'#3b82f6', icon:ICONS.robot},
  condition: {title:'Điều kiện', desc:'Kiểm tra dữ liệu và chọn nhánh tiếp theo', color:'var(--purple)', icon:ICONS.branch, kind:'branch'},
  workflow_call: {title:'Tác vụ', desc:'Gọi một quy trình hoặc tác vụ tự động khác', color:'#3b82f6', icon:ICONS.box},
  tool_call: {title:'Gọi công cụ', desc:'Gọi công cụ với các tham số đã cấu hình', color:'#8892a4', icon:ICONS.api},
  set_data: {title:'Đặt / Sửa dữ liệu', desc:'Đặt hoặc ghi đè dữ liệu của lần chạy', color:'#f59e0b', icon:ICONS.db},
  delay: {title:'Chờ', desc:'Tạm dừng trước khi đi tiếp', color:'#f59e0b', icon:ICONS.clock},
  stop_error: {title:'Dừng & Báo lỗi', desc:'Dừng quy trình và trả thông báo lỗi', color:'#ef4444', icon:ICONS.octagon},
  approval_gate: {title:'Cổng duyệt', desc:'Chờ người phụ trách xem và duyệt nội dung', color:'#f59e0b', icon:ICONS.person},
  noop: {title:'Không làm gì', desc:'Cho dữ liệu đi qua mà không thay đổi', color:'#8892a4', icon:ICONS.x},
  end: {title:'Kết thúc', desc:'Điểm kết thúc của quy trình', color:'#ef4444', icon:ICONS.stop, kind:'end'},
};

const NODE_IO = {
  trigger:{in:'Bước mở đầu — dữ liệu do người dùng hoặc lịch/trigger đưa vào.',out:'Dữ liệu/yêu cầu mở đầu quy trình'},
  agent:{in:'Kết quả của bước liền trước.',out:'Nội dung do nhân viên AI tạo ra'},
  tool_call:{in:'Tham số lấy từ bước trước hoặc điền tay.',out:'Kết quả trả về từ công cụ'},
  condition:{in:'Dữ liệu cần kiểm tra.',out:'Rẽ nhánh Đúng / Sai'},
  set_data:{in:'Dữ liệu hiện có của lần chạy.',out:'Dữ liệu đã được đặt/ghi đè'},
  delay:{in:'Dữ liệu đi qua nguyên vẹn.',out:'Dữ liệu giữ nguyên sau khi chờ'},
  workflow_call:{in:'Dữ liệu gửi sang tác vụ được gọi.',out:'Kết quả tác vụ con trả về'},
  approval_gate:{in:'Nội dung từ bước liền trước để người duyệt xem/sửa.',out:'Nội dung đã duyệt (có thể đã chỉnh sửa)'},
  stop_error:{in:'Dữ liệu tại thời điểm dừng.',out:'Không có — quy trình dừng tại đây'},
  noop:{in:'Dữ liệu đi qua nguyên vẹn.',out:'Dữ liệu giữ nguyên'},
  end:{in:'Kết quả cuối của quy trình.',out:'Không có — quy trình kết thúc'},
};

function inferNodeType(node) {
  if (node.type) return node.type;
  if (node.kind === 'start') return 'trigger';
  if (node.kind === 'end') return 'end';
  if (node.kind === 'branch') return 'condition';
  return 'agent';
}

function graphNodeToEditor(node, index = 0) {
  const type = inferNodeType(node);
  const data = node.data && typeof node.data === 'object' ? {...node.data} : {};
  const meta = NODE_META[type] || NODE_META.noop;
  return {
    ...node,
    type,
    data,
    x: Number.isFinite(Number(node.x)) ? Number(node.x) : 60 + index * 230,
    y: Number.isFinite(Number(node.y)) ? Number(node.y) : 80,
    title: node.title || data.label || data.agent_name || meta.title,
    sub: node.sub || data.instructions || data.tool_name || '',
    color: node.color || meta.color,
    icon: node.icon || meta.icon,
    kind: node.kind || meta.kind,
  };
}

function refreshNodePresentation(node) {
  const type = inferNodeType(node), data = node.data || {};
  const meta = NODE_META[type] || NODE_META.noop;
  node.type = type; node.kind = meta.kind || type; node.icon = node.icon || meta.icon; node.color = node.color || meta.color;
  node.title = data.label || meta.title;
  if (type === 'agent') {
    const agent = builderAgents.find(a => String(a.id) === String(data.agent_id));
    const effectiveIds = data.skill_ids?.length ? data.skill_ids : (agent?.skills || []);
    const skills = effectiveIds.map(id => builderSkills.find(s => String(s.id) === String(id))?.name).filter(Boolean);
    node.sub = `${agent?.name || 'Chưa chọn nhân viên AI'}${skills.length ? ` · ${skills.join(', ')}` : ' · Không có kỹ năng'}`;
  } else if (type === 'tool_call') node.sub = data.tool_name || 'Chưa chọn công cụ';
  else if (type === 'workflow_call') {
    const target = builderWorkflows.find(w => String(w.id) === String(data.target_task_id));
    node.sub = target ? target.name : 'Chưa chọn tác vụ';
  }
  else if (type === 'delay') node.sub = `${Number(data.seconds || 0)} giây`;
  else if (type === 'approval_gate') node.sub = `Chờ ${data.approver || 'CEO'} duyệt`;
  else if (type === 'condition') node.sub = `${data.field || 'last_output'} ${data.mode || 'contains'} ${data.value || ''}`;
  else node.sub = data.instructions || data.message || '';
}

function graphEdgeToEditor(edge) {
  if (Array.isArray(edge)) return edge;
  const label = edge.branch === 'true' ? 'Đúng' : edge.branch === 'false' ? 'Sai' : (edge.label || '');
  return [edge.from, edge.to, label, edge.color || ''];
}

function editorNodeToGraph(node) {
  const type = inferNodeType(node);
  const data = {...(node.data || {})};
  if (!data.label && node.title && node.title !== NODE_META[type]?.title) data.label = node.title;
  if (type === 'agent' && node.sub && !data.instructions) data.instructions = node.sub;
  return {id: node.id, type, x: Math.round(node.x || 0), y: Math.round(node.y || 0), data};
}

function editorEdgeToGraph(edge) {
  if (!Array.isArray(edge)) return edge;
  const [from, to, label, color] = edge;
  const branch = label === 'Đúng' ? 'true' : label === 'Sai' ? 'false' : null;
  return {from, to, branch, ...(color ? {color} : {})};
}

let currentZoom = 100;
let _inspSecId = 0;

function slugify(str) {
  return String(str).toLowerCase()
    .normalize('NFD').replace(/\p{Mn}/gu, '')
    .replace(/đ/g, 'd').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function findWorkflow(idOrSlug) {
  return REAL_TASKS.find(w => String(w.id) === String(idOrSlug))
      || REAL_TASKS.find(w => slugify(w.name) === String(idOrSlug));
}

async function runnerApi(method, path, body) {
  const response = await fetch('/api' + path, {
    method,
    credentials: 'same-origin',
    headers: body === undefined ? {} : {'Content-Type': 'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { detail = (await response.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function loadWorkflowSettings(id) {
  currentWorkflowId = Number(id) || null;
  currentWorkflowRecord = null;
  if (!currentWorkflowId) return;
  try {
    const [task, projectsData, agentsData, skillsData, toolsData, workflowsData] = await Promise.all([
      runnerApi('GET', `/workflow/tasks/${currentWorkflowId}`),
      runnerApi('GET', '/projects/'),
      runnerApi('GET', '/agent-configs/'),
      runnerApi('GET', '/skills/'),
      runnerApi('GET', '/tools/'),
      runnerApi('GET', '/workflow/tasks'),
    ]);
    currentWorkflowRecord = task;
    workflowProjects = projectsData.projects || [];
    builderAgents = agentsData.agents || [];
    builderSkills = skillsData.skills || [];
    builderTools = toolsData.tools || [];
    builderWorkflows = workflowsData.tasks || [];
  } catch {
    // Một số card hiện vẫn là dữ liệu demo và chưa có workflow_tasks tương ứng.
    currentWorkflowRecord = null;
    workflowProjects = [];
    builderAgents = [];
    builderSkills = [];
    builderTools = [];
    builderWorkflows = [];
  }
}

function normalizeTriggers(record) {
  let cfg = {};
  try { cfg = JSON.parse(record?.trigger_config_json || '{}'); } catch {}
  if (cfg.triggers && typeof cfg.triggers === 'object') {
    return {
      manual:{enabled:false,...cfg.triggers.manual},
      schedule:{enabled:false,cron:record?.schedule_cron || '',...cfg.triggers.schedule},
      webhook:{enabled:false,webhook_token:cfg.webhook_token || '',...cfg.triggers.webhook},
      workflow_complete:{enabled:false,source_task_id:cfg.source_task_id ?? '',...cfg.triggers.workflow_complete},
      meeting_decision:{enabled:false,project_id:cfg.project_id ?? '',...cfg.triggers.meeting_decision},
    };
  }
  const type = record?.trigger_type || (record?.schedule_enabled ? 'schedule' : 'manual');
  return {
    manual:{enabled:type === 'manual'},
    schedule:{enabled:!!record?.schedule_enabled || type === 'schedule',cron:record?.schedule_cron || ''},
    webhook:{enabled:type === 'webhook',webhook_token:cfg.webhook_token || ''},
    workflow_complete:{enabled:type === 'workflow_complete',source_task_id:cfg.source_task_id ?? ''},
    meeting_decision:{enabled:type === 'meeting_decision',project_id:cfg.project_id ?? ''},
  };
}

// Node bắt đầu nhận mọi hình thức kích hoạt cùng lúc — không bật/tắt thủ công.
// Hình thức nào được điền cấu hình thì tự bật; chạy tay và webhook luôn sẵn sàng.
function deriveTriggerEnabled(triggers) {
  const t = {...triggers};
  t.manual = {...(t.manual || {}), enabled: true};
  t.webhook = {...(t.webhook || {}), enabled: true};
  t.schedule = {...(t.schedule || {}), enabled: !!String(t.schedule?.cron || '').trim()};
  t.workflow_complete = {...(t.workflow_complete || {}), enabled: !!t.workflow_complete?.source_task_id};
  t.meeting_decision = {...(t.meeting_decision || {}), enabled: !!t.meeting_decision?.project_id};
  return t;
}

// Cột trigger_type chỉ là "hình thức chính" để tương thích ngược; việc điều phối
// thật sự dựa trên cờ enabled trong trigger_config_json nên mọi hình thức vẫn chạy.
function primaryTriggerType(triggers) {
  const t = deriveTriggerEnabled(triggers);
  return ['meeting_decision','workflow_complete','schedule'].find(key => t[key]?.enabled) || 'manual';
}

function activeTriggerLabels(triggers) {
  const t = deriveTriggerEnabled(triggers);
  return SIMPLE_TRIGGER_KEYS.filter(key => t[key]?.enabled).map(key => SIMPLE_TRIGGER_LABEL[key]);
}

function buildTriggerConfig(triggers) {
  const clean = {
    manual:{enabled:!!triggers.manual?.enabled},
    schedule:{enabled:!!triggers.schedule?.enabled,cron:triggers.schedule?.cron || ''},
    webhook:{enabled:!!triggers.webhook?.enabled,webhook_token:triggers.webhook?.webhook_token || ''},
    workflow_complete:{enabled:!!triggers.workflow_complete?.enabled,source_task_id:triggers.workflow_complete?.source_task_id || null},
    meeting_decision:{enabled:!!triggers.meeting_decision?.enabled,project_id:triggers.meeting_decision?.project_id || null},
  };
  return {
    triggers:clean,
    webhook_token:clean.webhook.webhook_token || '',
    project_id:clean.meeting_decision.project_id,
    source_task_id:clean.workflow_complete.source_task_id,
  };
}

function openTriggerInspector() {
  const triggerNode = EDITOR_NODES.find(node => inferNodeType(node) === 'trigger');
  if (!triggerNode) return showToast('Sơ đồ chưa có node Bắt đầu.', 'error');
  if (currentEditorMode === 'simple') {
    currentEditorMode = 'advanced';
    localStorage.setItem('taskrunner_editor_mode', currentEditorMode);
    updateEditorViewMode();
  }
  _openTriggerRow = _openTriggerRow || 'manual';
  selectNode(triggerNode.id);
}

async function saveGraph({silent = false} = {}) {
  if (!currentWorkflowRecord) {
    showToast('Quy trình này chưa có bản ghi thật trong hệ thống.', 'error');
    return false;
  }
  const graph = {
    nodes: EDITOR_NODES.map(editorNodeToGraph),
    edges: EDITOR_EDGES.map(editorEdgeToGraph),
  };
  const name = document.getElementById('editor-title').textContent.trim() || currentWorkflowRecord.name;
  const triggerNode = graph.nodes.find(node => node.type === 'trigger');
  // Hình thức nào có cấu hình thì tự bật — không cần người dùng tích chọn.
  const triggers = deriveTriggerEnabled(
    triggerNode?.data?.triggers || normalizeTriggers(currentWorkflowRecord),
  );
  if (triggerNode) triggerNode.data.triggers = triggers;
  const body = {
    name,
    graph_json: JSON.stringify(graph),
    trigger_type: primaryTriggerType(triggers),
    trigger_config_json: JSON.stringify(buildTriggerConfig(triggers)),
    schedule_enabled: !!triggers.schedule?.enabled,
    schedule_cron: triggers.schedule?.cron || '',
  };
  currentWorkflowRecord = await runnerApi(
    'PATCH', `/workflow/tasks/${currentWorkflowRecord.id}`, body,
  );
  const savedTriggers = normalizeTriggers(currentWorkflowRecord);
  const editorTrigger = EDITOR_NODES.find(node => inferNodeType(node) === 'trigger');
  if (editorTrigger) editorTrigger.data.triggers = savedTriggers;
  // Sau khi lưu, server có thể vừa sinh webhook_token → vẽ lại để hiện URL.
  if (currentEditorMode === 'simple') renderSimpleWorkflow();
  if (!silent) showToast('Đã lưu đồ thị quy trình.', 'success');
  return true;
}

// Trạng thái chạy của từng node được giữ trong JS chứ không chỉ trên DOM: mỗi lần
// renderCanvas()/renderSimpleWorkflow() vẽ lại (đổi chế độ, thêm/xoá node, chọn
// node...) là DOM cũ bị thay, nên phải sơn lại từ NODE_RUN_STATE.
const RUN_STATE_CLASSES = ['node-running', 'node-done', 'node-error', 'node-paused'];
let NODE_RUN_STATE = {};

function resetNodeRunStates() {
  NODE_RUN_STATE = {};
  document.querySelectorAll('.flow-node, .se-card').forEach(node => {
    node.classList.remove(...RUN_STATE_CLASSES);
    node.removeAttribute('title');
  });
}

function paintNodeRunState(nodeId, state, detail) {
  [document.getElementById('node-' + nodeId), document.getElementById('se-node-' + nodeId)]
    .filter(Boolean)
    .forEach(el => {
      el.classList.remove(...RUN_STATE_CLASSES);
      if (state) el.classList.add('node-' + state);
      if (detail) el.title = detail;
    });
}

/** Sơn lại toàn bộ trạng thái chạy — gọi sau mỗi lần vẽ lại sơ đồ/danh sách bước. */
function applyNodeRunStates() {
  Object.entries(NODE_RUN_STATE).forEach(([nodeId, {state, detail}]) => {
    paintNodeRunState(nodeId, state, detail);
  });
}

/** Run kết thúc: node nào còn kẹt "đang chạy" (thiếu event done) thì chốt lại. */
function settleRunningNodes(finalState) {
  Object.entries(NODE_RUN_STATE).forEach(([nodeId, entry]) => {
    if (entry.state !== 'running') return;
    if (finalState) NODE_RUN_STATE[nodeId] = {...entry, state: finalState};
    else delete NODE_RUN_STATE[nodeId];
    paintNodeRunState(nodeId, finalState, entry.detail);
  });
  activeNodeId = null;
}

function setNodeRunState(nodeId, state, detail = '') {
  if (!nodeId) return;
  NODE_RUN_STATE[nodeId] = {state, detail: detail || NODE_RUN_STATE[nodeId]?.detail || ''};
  paintNodeRunState(nodeId, state, NODE_RUN_STATE[nodeId].detail);
}

function handleWorkflowEvent(message) {
  if (message.type === 'attach_failed') {
    // Run đã kết thúc từ lâu và server không còn giữ lịch sử — bỏ theo dõi.
    activeRunId = null;
    forgetActiveRun();
    setRunningUI(false);
    return;
  }
  if (message.type === 'attached') {
    // Sắp phát lại toàn bộ diễn biến từ đầu → xoá trạng thái cũ trên canvas.
    resetNodeRunStates();
    _approvalQueue = [];
    _activeApproval = null;
    document.getElementById('approval-modal').style.display = 'none';
    return;
  }
  if (message.run_id) {
    activeRunId = message.run_id;
    if (message.type === 'run_started') rememberActiveRun(message.run_id);
  }
  const nodeId = message.node_id || activeNodeId;
  if (['node_start', 'agent_start', 'tool_call_start', 'delay_start'].includes(message.type)) {
    activeNodeId = message.node_id;
    setNodeRunState(message.node_id, 'running', message.agent_name || message.tool_name || 'Đang chạy');
  } else if (message.type === 'agent_chunk' && nodeId) {
    setNodeRunState(nodeId, 'running', ((NODE_RUN_STATE[nodeId]?.detail || '') + message.content).slice(-500));
  } else if (['agent_done', 'tool_call_done', 'data_set', 'delay_done', 'condition_result', 'node_done', 'approval_resumed'].includes(message.type)) {
    setNodeRunState(nodeId, 'done', message.result || 'Đã hoàn thành');
    if (activeNodeId === nodeId) activeNodeId = null;
  } else if (message.type === 'run_paused_for_approval') {
    setNodeRunState(message.node_id, 'paused', `Đang chờ ${message.approver || 'CEO'} duyệt`);
    openApprovalModal(message);
  } else if (message.type === 'approval_rejected') {
    showToast(`${document.getElementById('approval-modal-title').dataset.approver || 'CEO'} đã từ chối — đang chạy lại bước trước (lần ${message.attempt})...`, 'info');
  } else if (['agent_error', 'tool_call_error', 'run_failed'].includes(message.type)) {
    setNodeRunState(nodeId, 'error', message.content || 'Thất bại');
  }
  if (['run_done', 'run_cancelled', 'run_error', 'run_failed'].includes(message.type)) {
    settleRunningNodes(message.type === 'run_done' ? 'done'
      : message.type === 'run_cancelled' ? null : 'error');
    activeRunId = null;
    forgetActiveRun();
    setRunningUI(false);
    if (message.type === 'run_done') showToast('Quy trình đã hoàn thành.', 'success');
    if (message.type === 'run_error' || message.type === 'run_failed') showToast(message.content || 'Quy trình thất bại.', 'error');
  }
}

// ── Chạy ngầm ────────────────────────────────────────────────────────────────
// Quy trình chạy trên server độc lập với tab này. Đóng tab / mất mạng / chuyển
// tab chỉ ngắt kết nối xem, luồng vẫn chạy tiếp. Ta ghi nhớ run_id đang chạy để
// khi quay lại thì nối lại (action 'attach') và phát lại toàn bộ diễn biến.

function _runKey(taskId) { return 'xanax_active_run_' + taskId; }

function rememberActiveRun(runId) {
  if (currentWorkflowRecord?.id && runId) {
    localStorage.setItem(_runKey(currentWorkflowRecord.id), String(runId));
  }
}

function forgetActiveRun() {
  if (currentWorkflowRecord?.id) localStorage.removeItem(_runKey(currentWorkflowRecord.id));
}

function setRunningUI(running) {
  document.getElementById('run-workflow-btn').style.display = running ? 'none' : '';
  document.getElementById('cancel-workflow-btn').style.display = running ? '' : 'none';
}

let _wsReconnectTimer = null;

function connectWorkflowSocket(onOpen) {
  if (workflowSocket && workflowSocket.readyState === WebSocket.OPEN) {
    onOpen?.();
    return workflowSocket;
  }
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  workflowSocket = new WebSocket(`${protocol}//${location.host}/ws/workflow`);
  workflowSocket.onopen = () => onOpen?.();
  workflowSocket.onmessage = event => {
    try { handleWorkflowEvent(JSON.parse(event.data)); } catch {}
  };
  workflowSocket.onclose = () => {
    // Mất kết nối trong lúc đang chạy: thử nối lại và xem tiếp — run vẫn sống.
    if (activeRunId && !_wsReconnectTimer) {
      _wsReconnectTimer = setTimeout(() => {
        _wsReconnectTimer = null;
        attachToRun(activeRunId);
      }, 2000);
    }
  };
  workflowSocket.onerror = () => {
    if (!activeRunId) {
      setRunningUI(false);
      showToast('Không thể kết nối tới engine quy trình.', 'error');
    }
  };
  return workflowSocket;
}

function attachToRun(runId) {
  connectWorkflowSocket(() => workflowSocket.send(JSON.stringify({action: 'attach', run_id: Number(runId)})));
}

/** Gọi khi mở editor: nếu quy trình này còn một lần chạy ngầm thì xem tiếp. */
function resumeBackgroundRun() {
  const stored = currentWorkflowRecord?.id && localStorage.getItem(_runKey(currentWorkflowRecord.id));
  if (!stored) return;
  activeRunId = Number(stored);
  setRunningUI(true);
  attachToRun(activeRunId);
}

async function runWorkflow(isTest = false) {
  if (!(await saveGraph({silent: true}))) return;
  resetNodeRunStates();
  _approvalQueue = [];
  _activeApproval = null;
  document.getElementById('approval-modal').style.display = 'none';
  const userInput = await requestWorkflowInput(isTest);
  if (userInput === null) return;
  if (workflowSocket) { workflowSocket.onclose = null; workflowSocket.close(); workflowSocket = null; }
  activeRunId = null;
  activeNodeId = null;
  forgetActiveRun();
  setRunningUI(true);
  connectWorkflowSocket(() => workflowSocket.send(JSON.stringify({
    action: 'run',
    task_id: currentWorkflowRecord.id,
    input: isTest ? `[CHẠY THỬ]\n${userInput}` : userInput,
    project_id: currentWorkflowRecord.project_id || null,
  })));
}

function cancelWorkflowRun() {
  if (!activeRunId) return;
  const runId = activeRunId;
  connectWorkflowSocket(() => workflowSocket.send(JSON.stringify({action: 'cancel', run_id: runId})));
}

function _embedQuery() {
  const embed = new URLSearchParams(location.search).get('embed') === '1' ? 'embed=1' : '';
  const tab = new URLSearchParams(location.search).get('tab') || currentMainTab;
  return '?' + [embed, 'tab=' + tab].filter(Boolean).join('&');
}

function _workflowIdFromOwnPath() {
  const seg = location.pathname.split('/').filter(Boolean); // ['taskrunner','id']
  return seg[0] === 'taskrunner' && seg[1] ? decodeURIComponent(seg[1]) : null;
}

function openEditor(id) {
  if (window.top !== window) {
    const parentTab = currentMainTab === 'company' ? 'company-runner' : 'auto-runner';
    window.top.history.pushState({ tab: parentTab }, '', `/hub/${parentTab}/` + id);
  }
  location.href = '/taskrunner/' + id + _embedQuery();
}

function closeEditor() {
  if (window.top !== window) {
    const parentTab = currentMainTab === 'company' ? 'company-runner' : 'auto-runner';
    window.top.history.pushState({ tab: parentTab }, '', `/hub/${parentTab}`);
  }
  location.href = '/taskrunner' + _embedQuery();
}

function renameWorkflow() {
  const el = document.getElementById('editor-title');
  const editing = el.getAttribute('contenteditable') === 'true';
  if (!editing) {
    el.setAttribute('contenteditable', 'true');
    el.focus();
    document.execCommand('selectAll', false, null);
  } else {
    el.removeAttribute('contenteditable');
  }
}

function toggleCat(i) {
  document.querySelector(`.palette-cat[data-cat="${i}"]`)?.classList.toggle('collapsed');
}

function paletteNodeSpec(item) {
  const text = `${item.name} ${item.desc}`.toLowerCase();
  let type = 'noop', data = { label: item.name };
  if (/bắt đầu|khởi đầu|khởi chạy|start|trigger/.test(text)) { type = 'trigger'; data.trigger_type = 'manual'; }
  else if (/điều kiện|if|nhánh/.test(text)) type = 'condition';
  else if (/chờ|delay/.test(text)) { type = 'delay'; data.seconds = 5; }
  else if (/dừng|lỗi/.test(text)) { type = 'stop_error'; data.message = item.name; }
  else if (/duyệt|approval/.test(text)) { type = 'approval_gate'; data.approver = 'CEO'; data.max_retries = 3; }
  else if (/workflow con|quy trình con/.test(text) || item.name === 'Tác vụ') type = 'workflow_call';
  else if (/đặt dữ liệu|set data/.test(text)) { type = 'set_data'; data.assignments = {}; }
  else if (/web|tìm kiếm/.test(text)) { type = 'tool_call'; data.tool_name = 'web_search'; data.args = {}; }
  else if (/http|api/.test(text)) { type = 'tool_call'; data.tool_name = 'http_get'; data.args = {}; }
  else if (/python|javascript|mã|code/.test(text)) { type = 'tool_call'; data.tool_name = 'run_python'; data.args = {}; }
  else if (/ảnh|image/.test(text)) {
    type = 'tool_call';
    data.tool_name = builderTools.find(t => /image|ảnh/i.test(`${t.name} ${t.description || ''}`))?.name || '';
    data.args = {};
  }
  else if (/lệnh thêm|song song/.test(text)) { type = 'noop'; data.parallel_out = true; }
  else if (/ai|agent|phòng ban|nhân viên/.test(text)) { type = 'agent'; data.skill_ids = []; }
  else if (/kết thúc|hoàn tất/.test(text)) type = 'end';
  return { type, data, title: item.name, icon: item.icon, color: item.color };
}

function renderPalette() {
  const wrap = document.getElementById('palette-categories');
  const activePalette = currentWorkflowType === 'company' ? PALETTE_COMPANY : PALETTE_AUTOMATION;
  wrap.innerHTML = activePalette.map((cat, ci) => `
    <div class="palette-cat" data-cat="${ci}">
      <div class="palette-cat-header" onclick="toggleCat(${ci})">
        ${cat.name}
        <svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
      <div class="palette-cat-items">
        ${cat.items.map((it, ii) => `
          <div class="palette-node-item" draggable="true" data-cat="${ci}" data-item="${ii}" title="Kéo thả vào sơ đồ">
            <div class="node-icon" style="background:${it.color}">${svgIcon(it.icon)}</div>
            <div class="node-text">
              <span class="node-name">${it.name}</span>
              <span class="node-desc">${it.desc}</span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
  wrap.querySelectorAll('.palette-node-item').forEach(el => {
    el.addEventListener('dragstart', e => {
      const cat = activePalette[Number(el.dataset.cat)];
      const item = cat?.items[Number(el.dataset.item)];
      if (item) e.dataTransfer.setData('application/x-workflow-node', JSON.stringify(paletteNodeSpec(item)));
    });
  });
}

document.getElementById('node-search-input')?.addEventListener('input', e => {
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll('.palette-node-item').forEach(el => {
    const name = el.querySelector('.node-name').textContent.toLowerCase();
    el.style.display = !q || name.includes(q) ? '' : 'none';
  });
});

function renderCanvas() {
  const nodesWrap = document.getElementById('canvas-nodes');
  nodesWrap.innerHTML = EDITOR_NODES.map(n => `
    <div class="flow-node" id="node-${n.id}" style="left:${n.x}px;top:${n.y}px">
      <div class="node-icon" style="background:${n.color}">${svgIcon(n.icon, n.kind === 'start')}</div>
      <div class="node-body">
        <div class="node-title">${n.title}</div>
        ${n.sub ? `<div class="node-sub">${n.sub}</div>` : ''}
      </div>
      ${n.kind !== 'start' ? '<div class="node-port in"></div>' : ''}
      ${n.kind === 'end' ? '' : n.kind === 'branch'
        ? '<div class="node-port out yes" style="top:35%"></div><div class="node-port out no" style="top:65%"></div>'
        : '<div class="node-port out"></div>'}
    </div>
  `).join('');
  renderLines();
  renderMinimap();
  applyNodeRunStates();
}

function renderLines() {
  const svg = document.getElementById('canvas-lines');
  let pathsHtml = `<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="var(--text3)"/></marker></defs>`;
  let labelsHtml = '';
  EDITOR_EDGES.forEach((edge, idx) => {
    const [fromId, toId, label, color] = edge;
    const fromEl = document.getElementById('node-' + fromId);
    const toEl = document.getElementById('node-' + toId);
    if (!fromEl || !toEl) return;
    let y1;
    if (label === 'Sai') y1 = fromEl.offsetTop + fromEl.offsetHeight * 0.65;
    else if (label === 'Đúng') y1 = fromEl.offsetTop + fromEl.offsetHeight * 0.35;
    else y1 = fromEl.offsetTop + fromEl.offsetHeight / 2;
    const x1 = fromEl.offsetLeft + fromEl.offsetWidth;
    const x2 = toEl.offsetLeft;
    const y2 = toEl.offsetTop + toEl.offsetHeight / 2;
    const midX = (x1 + x2) / 2;
    const strokeColor = color || 'var(--border2)';
    const d = `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`;
    pathsHtml += `<path class="edge-hit" d="${d}" onclick="confirmDeleteEdge(${idx})"><title>Bấm để xoá kết nối</title></path>`;
    pathsHtml += `<path class="edge-line" d="${d}" stroke="${strokeColor}" marker-end="url(#arrow)"/>`;
    if (label) {
      labelsHtml += `<div class="branch-label" style="left:${midX - 14}px;top:${(y1 + y2) / 2 - 9}px;color:${color}">${label}</div>`;
    }
  });
  svg.innerHTML = pathsHtml;
  document.querySelectorAll('.branch-label').forEach(el => el.remove());
  document.getElementById('canvas-nodes').insertAdjacentHTML('beforeend', labelsHtml);
}

// ── Xoá kết nối — có popup xác nhận trước khi xoá ─────────────────────────
async function confirmDeleteEdge(idx) {
  const edge = EDITOR_EDGES[idx];
  if (!edge) return;
  const fromNode = EDITOR_NODES.find(n => n.id === edge[0]);
  const toNode = EDITOR_NODES.find(n => n.id === edge[1]);
  const accepted = await showConfirm(
    `Bạn có chắc muốn xoá kết nối từ "${fromNode ? fromNode.title : edge[0]}" đến "${toNode ? toNode.title : edge[1]}"? Hành động này không thể hoàn tác.`,
    {title: 'Xoá kết nối?', confirmLabel: 'Xoá kết nối'}
  );
  if (!accepted) return;
  EDITOR_EDGES.splice(idx, 1);
  renderLines();
  renderMinimap();
}

window.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeConfirmModal();
    closeWorkflowInputModal();
  }
});

// ── Pan & zoom (kéo canvas như n8n) ───────────────────────────────────────
let panX = 0, panY = 0;
let isPanning = false, canvasLocked = false;
let _panStart = { x: 0, y: 0, panX: 0, panY: 0 };
let _minimapMeta = null;

function applyCanvasTransform() {
  const vp = document.getElementById('canvas-viewport');
  if (vp) vp.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom / 100})`;
  renderMinimapViewport();
}

function getNodesBBox() {
  const els = document.querySelectorAll('.flow-node');
  if (!els.length) return { minX: 0, minY: 0, maxX: 1000, maxY: 600 };
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  els.forEach(el => {
    const x = el.offsetLeft, y = el.offsetTop, w = el.offsetWidth, h = el.offsetHeight;
    minX = Math.min(minX, x); minY = Math.min(minY, y);
    maxX = Math.max(maxX, x + w); maxY = Math.max(maxY, y + h);
  });
  return { minX, minY, maxX, maxY };
}

function fitView() {
  const wrap = document.getElementById('canvas-wrap');
  const bbox = getNodesBBox();
  const bw = Math.max(1, bbox.maxX - bbox.minX);
  const bh = Math.max(1, bbox.maxY - bbox.minY);
  const pad = 80;
  const scale = Math.min(1.25, Math.max(0.4, Math.min((wrap.clientWidth - pad) / bw, (wrap.clientHeight - pad) / bh)));
  currentZoom = Math.round(scale * 100);
  panX = (wrap.clientWidth - bw * scale) / 2 - bbox.minX * scale;
  panY = (wrap.clientHeight - bh * scale) / 2 - bbox.minY * scale;
  applyCanvasTransform();
  const sel = document.getElementById('zoom-select');
  if (sel) sel.value = [50, 75, 100, 125, 150].includes(currentZoom) ? currentZoom : 100;
}

function setZoom(val) {
  currentZoom = parseInt(val, 10) || 100;
  applyCanvasTransform();
  const sel = document.getElementById('zoom-select');
  if (sel) sel.value = [50, 75, 100, 125, 150].includes(currentZoom) ? currentZoom : 100;
}

function zoomBy(delta) {
  setZoom(Math.min(150, Math.max(50, currentZoom + delta)));
}

function toggleLockCanvas() {
  canvasLocked = !canvasLocked;
  document.getElementById('lock-canvas-btn')?.classList.toggle('active', canvasLocked);
}

function initCanvasPanning() {
  const canvas = document.getElementById('editor-canvas');
  if (!canvas) return;
  canvas.addEventListener('mousedown', e => {
    if (canvasLocked || e.button !== 0 || e.target.closest('.flow-node')) return;
    isPanning = true;
    _panStart = { x: e.clientX, y: e.clientY, panX, panY };
    canvas.classList.add('panning');
    e.preventDefault();
  });
  window.addEventListener('mousemove', e => {
    if (!isPanning) return;
    panX = _panStart.panX + (e.clientX - _panStart.x);
    panY = _panStart.panY + (e.clientY - _panStart.y);
    applyCanvasTransform();
  });
  window.addEventListener('mouseup', () => {
    isPanning = false;
    canvas.classList.remove('panning');
  });
  canvas.addEventListener('wheel', e => {
    if (canvasLocked) return;
    e.preventDefault();
    zoomBy(e.deltaY < 0 ? 10 : -10);
  }, { passive: false });
  canvas.addEventListener('dragover', e => e.preventDefault());
  canvas.addEventListener('drop', e => {
    e.preventDefault();
    const raw = e.dataTransfer.getData('application/x-workflow-node');
    if (!raw || canvasLocked) return;
    const spec = JSON.parse(raw);
    const rect = canvas.getBoundingClientRect();
    const scale = currentZoom / 100;
    const node = {
      id: `node_${Date.now()}`, kind: spec.type === 'condition' ? 'branch' : spec.type,
      type: spec.type, title: spec.title, sub: '', icon: spec.icon, color: spec.color,
      x: Math.round((e.clientX - rect.left - panX) / scale),
      y: Math.round((e.clientY - rect.top - panY) / scale), data: spec.data || {}
    };
    refreshNodePresentation(node);
    EDITOR_NODES.push(node);
    renderCanvas();
    selectNode(node.id);
  });
}

// ── Kéo thả node tự do trong vùng thiết kế ────────────────────────────────
let dragNode = null, dragMoved = false;
let _dragStart = { x: 0, y: 0, nodeX: 0, nodeY: 0 };

// ── Kéo dây nối từ port ra ra bất kỳ đâu trên node đích (dễ trúng hơn nhiều
// so với việc phải bấm đúng chấm tròn nhỏ ở cạnh node) ────────────────────
let connectDrag = null; // { fromId, label, color }

function _canvasLocalPoint(e) {
  const rect = document.getElementById('editor-canvas').getBoundingClientRect();
  const scale = currentZoom / 100;
  return {
    x: (e.clientX - rect.left - panX) / scale,
    y: (e.clientY - rect.top - panY) / scale,
  };
}

function _portAnchor(nodeId, label) {
  const el = document.getElementById('node-' + nodeId);
  if (!el) return null;
  const y = label === 'Sai' ? el.offsetTop + el.offsetHeight * 0.65
    : label === 'Đúng' ? el.offsetTop + el.offsetHeight * 0.35
    : el.offsetTop + el.offsetHeight / 2;
  return { x: el.offsetLeft + el.offsetWidth, y };
}

function _drawTempConnectLine(toX, toY) {
  const svg = document.getElementById('canvas-lines');
  let temp = svg.querySelector('.temp-connect-line');
  const from = _portAnchor(connectDrag.fromId, connectDrag.label);
  if (!from) return;
  const midX = (from.x + toX) / 2;
  const d = `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${toY}, ${toX} ${toY}`;
  if (!temp) {
    temp = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    temp.setAttribute('class', 'temp-connect-line');
    svg.appendChild(temp);
  }
  temp.setAttribute('d', d);
}

function _endConnectDrag() {
  document.querySelector('.temp-connect-line')?.remove();
  document.querySelectorAll('.flow-node.connect-target').forEach(el => el.classList.remove('connect-target'));
  if (connectDrag) document.getElementById('node-' + connectDrag.fromId)?.classList.remove('connect-source');
  document.getElementById('canvas-nodes')?.classList.remove('connecting');
  connectDrag = null;
}

function initNodeDragging() {
  const nodesWrap = document.getElementById('canvas-nodes');
  if (!nodesWrap) return;
  nodesWrap.addEventListener('mousedown', e => {
    if (canvasLocked) return;
    const port = e.target.closest('.node-port.out');
    const nodeEl = e.target.closest('.flow-node');
    if (port && nodeEl) {
      connectDrag = {
        fromId: nodeEl.id.replace('node-', ''),
        label: port.classList.contains('yes') ? 'Đúng' : port.classList.contains('no') ? 'Sai' : '',
        color: port.classList.contains('yes') ? '#22c55e' : port.classList.contains('no') ? '#ef4444' : '',
      };
      nodesWrap.classList.add('connecting');
      nodeEl.classList.add('connect-source');
      e.stopPropagation();
      e.preventDefault();
      return;
    }
    if (e.target.closest('.node-port')) return;
    if (!nodeEl) return;
    const id = nodeEl.id.replace('node-', '');
    const nodeData = EDITOR_NODES.find(n => n.id === id);
    if (!nodeData) return;
    dragNode = nodeData;
    dragMoved = false;
    _dragStart = { x: e.clientX, y: e.clientY, nodeX: nodeData.x, nodeY: nodeData.y };
    e.stopPropagation();
    e.preventDefault();
  });
  window.addEventListener('mousemove', e => {
    if (connectDrag) {
      const pt = _canvasLocalPoint(e);
      _drawTempConnectLine(pt.x, pt.y);
      const overEl = document.elementFromPoint(e.clientX, e.clientY);
      const overNode = overEl?.closest('.flow-node');
      document.querySelectorAll('.flow-node.connect-target').forEach(el => el.classList.remove('connect-target'));
      if (overNode && overNode.id !== 'node-' + connectDrag.fromId) overNode.classList.add('connect-target');
      return;
    }
    if (!dragNode) return;
    const scale = currentZoom / 100;
    const dx = (e.clientX - _dragStart.x) / scale;
    const dy = (e.clientY - _dragStart.y) / scale;
    if (!dragMoved && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) {
      dragMoved = true;
      document.getElementById('node-' + dragNode.id)?.classList.add('dragging');
    }
    if (!dragMoved) return;
    dragNode.x = Math.round(_dragStart.nodeX + dx);
    dragNode.y = Math.round(_dragStart.nodeY + dy);
    const el = document.getElementById('node-' + dragNode.id);
    if (el) { el.style.left = dragNode.x + 'px'; el.style.top = dragNode.y + 'px'; }
    renderLines();
    renderMinimap();
  });
  window.addEventListener('mouseup', e => {
    if (connectDrag) {
      const overEl = document.elementFromPoint(e.clientX, e.clientY);
      const toId = overEl?.closest('.flow-node')?.id.replace('node-', '');
      if (toId && toId !== connectDrag.fromId) {
        const dup = EDITOR_EDGES.some(([f, t, l]) => f === connectDrag.fromId && t === toId && (l || '') === connectDrag.label);
        if (!dup) {
          EDITOR_EDGES.push([connectDrag.fromId, toId, connectDrag.label, connectDrag.color]);
          renderLines();
          renderMinimap();
        }
      }
      _endConnectDrag();
      return;
    }
    if (!dragNode) return;
    document.getElementById('node-' + dragNode.id)?.classList.remove('dragging');
    if (!dragMoved) selectNode(dragNode.id);
    dragNode = null;
    dragMoved = false;
  });
}
initCanvasPanning();
initNodeDragging();

window.addEventListener('keydown', e => {
  if (e.key === 'Escape' && connectDrag) _endConnectDrag();
});

// ── Minimap — mapping đúng theo bố cục flow, có khung viewport hiện tại ──
function renderMinimap() {
  const mmW = 220, mmH = 130, pad = 10;
  const bbox = getNodesBBox();
  const bw = Math.max(1, bbox.maxX - bbox.minX);
  const bh = Math.max(1, bbox.maxY - bbox.minY);
  const scale = Math.min((mmW - pad * 2) / bw, (mmH - pad * 2) / bh);
  const offX = (mmW - bw * scale) / 2 - bbox.minX * scale;
  const offY = (mmH - bh * scale) / 2 - bbox.minY * scale;
  _minimapMeta = { scale, offX, offY };

  const nodesHtml = EDITOR_NODES.map(n => {
    const el = document.getElementById('node-' + n.id);
    const w = el ? el.offsetWidth : 170, h = el ? el.offsetHeight : 60;
    return `<div class="minimap-node" style="left:${n.x * scale + offX}px;top:${n.y * scale + offY}px;width:${w * scale}px;height:${h * scale}px;background:${n.color}"></div>`;
  }).join('');
  document.getElementById('minimap-content').innerHTML = nodesHtml + '<div id="minimap-viewport"></div>';
  renderMinimapViewport();
}

function renderMinimapViewport() {
  const meta = _minimapMeta;
  const vpEl = document.getElementById('minimap-viewport');
  const wrap = document.getElementById('canvas-wrap');
  if (!meta || !vpEl || !wrap) return;
  const scaleZoom = currentZoom / 100;
  const visX = -panX / scaleZoom;
  const visY = -panY / scaleZoom;
  const visW = wrap.clientWidth / scaleZoom;
  const visH = wrap.clientHeight / scaleZoom;
  vpEl.style.left = (visX * meta.scale + meta.offX) + 'px';
  vpEl.style.top = (visY * meta.scale + meta.offY) + 'px';
  vpEl.style.width = (visW * meta.scale) + 'px';
  vpEl.style.height = (visH * meta.scale) + 'px';
}

function inspectorSection(iconKey, title, expanded, bodyHtml, options = {}) {
  const id = 'insp-sec-' + (_inspSecId++);
  const iconSvg = ICONS[iconKey] ? `<svg class="sec-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[iconKey]}</svg>` : '';
  const click = options.triggerKey
    ? `toggleTriggerRow('${options.triggerKey}','${id}')`
    : `document.getElementById('${id}').classList.toggle('collapsed')`;
  return `
    <div class="inspector-section ${expanded ? '' : 'collapsed'}" id="${id}">
      <div class="inspector-section-header" onclick="${click}">
        ${iconSvg}<span class="inspector-section-title">${title}</span>
        ${options.headerExtra || ''}
        <svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
      <div class="inspector-section-body">${bodyHtml}</div>
    </div>
  `;
}

function toggleTriggerRow(key, sectionId) {
  const section = document.getElementById(sectionId);
  if (!section) return;
  const opening = section.classList.contains('collapsed');
  document.querySelectorAll('.inspector-section[data-trigger-row]').forEach(el => el.classList.add('collapsed'));
  section.classList.toggle('collapsed', !opening);
  _openTriggerRow = opening ? key : null;
}

function handleTriggerDetailsToggle(row, key) {
  if (row.open) {
    _openTriggerRow = key;
    document.querySelectorAll('.trigger-config-row[open]').forEach(other => {
      if (other !== row) other.open = false;
    });
  } else if (_openTriggerRow === key) {
    _openTriggerRow = null;
  }
}

function ioInBlock(type) {
  const info = NODE_IO[type] || NODE_IO.noop;
  return `<div class="io-block io-in"><div class="io-label">Đầu vào</div>${esc(info.in)}</div>`;
}

function ioOutBlock(node, type) {
  const info = NODE_IO[type] || NODE_IO.noop;
  const terminal = type === 'end' || type === 'stop_error';
  const targets = EDITOR_EDGES
    .filter(edge => edge[0] === node.id)
    .map(edge => EDITOR_NODES.find(item => item.id === edge[1]))
    .filter(Boolean);
  const links = targets.length
    ? targets.map(target => `<a class="io-link" onclick="selectNode('${esc(target.id)}')">${esc(target.title)}</a>`).join(', ')
    : '<span class="io-muted">chưa nối bước nào</span>';
  return `<div class="io-block io-out"><div class="io-label">Đầu ra</div>
    <div><strong>Tạo ra:</strong> ${esc(info.out)}</div>
    ${terminal ? '' : `<div><strong>Đưa sang:</strong> ${links}</div>`}
  </div>`;
}

function updateTriggerConfig(nodeId, key, patch, openKey = key) {
  const node = EDITOR_NODES.find(item => item.id === nodeId);
  if (!node) return;
  node.data = node.data || {};
  node.data.triggers = node.data.triggers || normalizeTriggers(currentWorkflowRecord);
  node.data.triggers[key] = {...(node.data.triggers[key] || {}),...patch};
  _openTriggerRow = openKey;
  renderCanvas();
  selectNode(nodeId);
}

function setSchedulePreset(nodeId, value) {
  if (value !== 'custom') updateTriggerConfig(nodeId, 'schedule', {cron:value});
}

async function copyWebhookUrl(value) {
  try { await navigator.clipboard.writeText(value); showToast('Đã sao chép URL webhook.', 'success'); }
  catch { showToast('Không thể sao chép tự động.', 'error'); }
}

function renderTriggerConfig(node) {
  const id = esc(node.id);
  const triggers = node.data.triggers || normalizeTriggers(currentWorkflowRecord);
  const status = currentWorkflowRecord?.status || 'draft';
  const label = STATUS_LABEL[status] || status;
  const statusHtml = status === 'active'
    ? `<div class="trigger-status"><strong>Trạng thái: ${esc(label)}</strong> — các kích hoạt tự động đang chạy.</div>`
    : `<div class="trigger-status"><strong>Trạng thái: ${esc(label)}</strong> — phải BẬT ${wfNoun()} thì hẹn giờ/webhook mới hoạt động. Chạy tay vẫn được.
       <br><button class="inspector-btn-mini" onclick="toggleTaskStatus(${currentWorkflowRecord.id},'active')">Bật ngay</button></div>`;
  const derived = deriveTriggerEnabled(triggers);
  const enabledHeader = key => derived[key]?.enabled
    ? '<span class="trigger-row-badge on">Đang bật</span>'
    : '<span class="trigger-row-badge">Chưa cấu hình</span>';
  const lockedHeader = '<span class="trigger-row-badge">Sắp có</span>';
  const section = (key, icon, title, body, headerExtra = enabledHeader(key)) => {
    const iconSvg = ICONS[icon]
      ? `<svg class="trigger-config-row-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[icon]}</svg>`
      : '';
    return `<details class="trigger-config-row" data-trigger-row="${key}" ${_openTriggerRow === key ? 'open' : ''} ontoggle="handleTriggerDetailsToggle(this,'${key}')">
      <summary>
        ${iconSvg}
        <span class="trigger-config-row-title">${title}</span>
        ${headerExtra || ''}
        <svg class="trigger-config-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
      </summary>
      <div class="trigger-config-row-body">${body}</div>
    </details>`;
  };
  const scheduleCron = triggers.schedule?.cron || '';
  const presets = ['0 * * * *','0 8 * * *','0 8 * * 1'];
  const webhookToken = triggers.webhook?.webhook_token || '';
  const webhookUrl = webhookToken ? `${location.origin}/api/workflow/hooks/${webhookToken}` : '';
  return `<div class="insp-group-label">Cách kích hoạt quy trình này</div>
    ${statusHtml}
    <div class="se-empty-hint">Điểm bắt đầu nhận mọi hình thức kích hoạt — điền cấu hình cho hình thức nào thì hình thức đó tự bật, và nhiều hình thức có thể kích hoạt đồng thời.</div>
    ${section('manual','play','Chạy tay',`<div class="se-empty-hint">Khởi chạy từ nút Chạy thử hoặc Chạy ngay.</div><button class="inspector-btn-mini wide" onclick="runWorkflow(true)">${svgIcon(ICONS.play)} Chạy thử</button>`)}
    ${section('chat_mention','chat','Khi chat nhắc tới',`<input disabled placeholder="Từ khoá (sắp có)"><div class="se-empty-hint">Kích hoạt từ hội thoại sẽ được bổ sung sau.</div>`,lockedHeader)}
    ${section('schedule','clock','Hẹn giờ tự chạy',`
      <label class="se-field-label">Lịch mẫu</label>
      <select onchange="setSchedulePreset('${id}',this.value)">
        <option value="custom" ${presets.includes(scheduleCron) ? '' : 'selected'}>Tuỳ chỉnh</option>
        <option value="0 * * * *" ${scheduleCron === '0 * * * *' ? 'selected' : ''}>Mỗi giờ</option>
        <option value="0 8 * * *" ${scheduleCron === '0 8 * * *' ? 'selected' : ''}>8h sáng hằng ngày</option>
        <option value="0 8 * * 1" ${scheduleCron === '0 8 * * 1' ? 'selected' : ''}>Thứ 2 hằng tuần</option>
      </select>
      <label class="se-field-label">Cron</label>
      <input value="${esc(scheduleCron)}" placeholder="0 8 * * *" onchange="updateTriggerConfig('${id}','schedule',{cron:this.value})">
      <div class="se-empty-hint">Cron đang lưu: ${esc(scheduleCron || 'chưa thiết lập')}</div>`)}
    ${section('webhook','globe','Hệ thống khác gọi vào (Webhook)',webhookUrl
      ? `<label class="se-field-label">URL nhận POST</label><div class="inspector-inline"><input readonly value="${esc(webhookUrl)}"><button class="inspector-btn-mini" onclick="copyWebhookUrl('${esc(webhookUrl)}')">Copy</button></div>`
      : '<div class="se-empty-hint">Lưu quy trình để sinh URL webhook.</div>')}
    ${section('form','doc','Form cho mọi người điền','<div class="se-empty-hint">Form công khai sẽ được bổ sung sau.</div>',lockedHeader)}
    ${section('workflow_complete','box','Được quy trình khác gọi',`
      <label class="se-field-label">Quy trình nguồn</label>
      <select onchange="updateTriggerConfig('${id}','workflow_complete',{source_task_id:Number(this.value)||null})">
        <option value="">— Chọn quy trình nguồn —</option>
        ${builderWorkflows.filter(item => String(item.id) !== String(currentWorkflowId)).map(item => `<option value="${item.id}" ${String(item.id) === String(triggers.workflow_complete?.source_task_id) ? 'selected' : ''}>${esc(item.name)}</option>`).join('')}
      </select>`)}
    ${section('meeting_decision','people','Khi cuộc họp chốt biên bản',`
      <label class="se-field-label">Dự án áp dụng</label>
      <select onchange="updateTriggerConfig('${id}','meeting_decision',{project_id:Number(this.value)||null})">
        <option value="">— Chọn dự án —</option>
        ${workflowProjects.map(project => `<option value="${project.id}" ${String(project.id) === String(triggers.meeting_decision?.project_id) ? 'selected' : ''}>${esc(project.name)}</option>`).join('')}
      </select>`)}
  `;
}

function selectNode(id) {
  document.querySelectorAll('.flow-node').forEach(el => el.classList.remove('selected'));
  document.getElementById('node-' + id)?.classList.add('selected');
  renderInspector(EDITOR_NODES.find(n => n.id === id));
}

function updateRealNode(id, key, value) {
  const node = EDITOR_NODES.find(n => n.id === id);
  if (!node) return;
  node.data = node.data || {};
  node.data[key] = value;
  if (key === 'agent_id') {
    const agent = builderAgents.find(a => String(a.id) === String(value));
    node.data.skill_ids = [...(agent?.skills || [])];
  }
  if (key === 'tool_name') node.data.args = {};
  refreshNodePresentation(node);
  // Vẽ lại đúng chế độ đang mở — cả hai đều đọc từ node.data nên luôn khớp nhau.
  if (currentEditorMode === 'simple') {
    renderSimpleWorkflow();
  } else {
    renderCanvas();
    selectNode(id);
  }
}

function updateRealNodeJson(id, key, value) {
  try {
    updateRealNode(id, key, value.trim() ? JSON.parse(value) : {});
  } catch (_) {
    showToast('JSON chưa hợp lệ. Vui lòng kiểm tra dấu ngoặc và dấu phẩy.', 'error');
  }
}

function updateToolArg(id, key, value, valueType) {
  const node = EDITOR_NODES.find(n => n.id === id);
  if (!node) return;
  const args = {...(node.data?.args || {})};
  if (valueType === 'number') value = Number(value);
  if (valueType === 'boolean') value = value === true || value === 'true';
  args[key] = value;
  updateRealNode(id, 'args', args);
}

function toggleRealNodeSkill(id, skillId, checked) {
  const node = EDITOR_NODES.find(n => n.id === id);
  if (!node) return;
  const agent = builderAgents.find(a => String(a.id) === String(node.data?.agent_id));
  const initialIds = node.data?.skill_ids?.length ? node.data.skill_ids : (agent?.skills || []);
  const ids = new Set(initialIds.map(String));
  checked ? ids.add(String(skillId)) : ids.delete(String(skillId));
  updateRealNode(id, 'skill_ids', [...ids].map(v => Number.isNaN(Number(v)) ? v : Number(v)));
}

async function deleteEditorNode(id) {
  const node = EDITOR_NODES.find(n => n.id === id);
  if (!node || inferNodeType(node) === 'trigger') return showToast('Không thể xoá node bắt đầu.', 'error');
  if (!(await showConfirm(
    `Xoá node "${node.title}" và các kết nối liên quan?`,
    {title: 'Xoá node?', confirmLabel: 'Xoá node'}
  ))) return;
  EDITOR_NODES = EDITOR_NODES.filter(n => n.id !== id);
  EDITOR_EDGES = EDITOR_EDGES.filter(e => e[0] !== id && e[1] !== id);
  renderInspector(null);
  renderCanvas();
}

/** Dựng các ô cấu hình thật của một node, đọc/ghi thẳng vào node.data.
 *  Dùng chung cho inspector (chế độ Đồ thị) và thẻ bước (chế độ Đơn giản),
 *  nhờ vậy hai chế độ luôn hiện cùng một dữ liệu. */
function realNodeFieldsHtml(node) {
  const type = inferNodeType(node), data = node.data || {};
  const id = esc(node.id);
  const field = (label, html) => `<div class="real-node-field"><div class="se-field-label">${label}</div>${html}</div>`;
  const input = (key, value, inputType = 'text') =>
    `<input type="${inputType}" value="${esc(value ?? '')}" onchange="updateRealNode('${id}','${key}',this.type==='number'?Number(this.value):this.value)">`;
  let body = field('Tên hiển thị', input('label', data.label || node.title));

  if (type === 'agent') {
    const selectedAgent = builderAgents.find(a => String(a.id) === String(data.agent_id));
    const allowedSkillIds = new Set((selectedAgent?.skills || []).map(String));
    const assignedSkills = selectedAgent ? builderSkills.filter(s => allowedSkillIds.has(String(s.id))) : [];
    const effectiveSkillIds = data.skill_ids?.length ? data.skill_ids.map(String) : [...allowedSkillIds];
    body += field('Nhân viên AI', `<select onchange="updateRealNode('${id}','agent_id',Number(this.value))">
      <option value="">-- Chọn nhân viên AI --</option>${builderAgents.map(a => `<option value="${a.id}" ${String(a.id) === String(data.agent_id) ? 'selected' : ''}>${esc(a.name)}</option>`).join('')}</select>`);
    body += field('Chỉ dẫn', `<textarea rows="4" onchange="updateRealNode('${id}','instructions',this.value)">${esc(data.instructions || '')}</textarea>`);
    body += field('Kỹ năng được phép dùng', `<div class="se-check-list">${assignedSkills.map(s => {
      const checked = effectiveSkillIds.includes(String(s.id));
      return `<label class="se-check-row"><input type="checkbox" ${checked ? 'checked' : ''} onchange="toggleRealNodeSkill('${id}','${s.id}',this.checked)"> <span>${esc(s.name)} <small class="se-skill-type">(${esc(s.skill_type || s.type || 'custom')})</small></span></label>`;
    }).join('') || '<small class="se-empty-hint">Nhân viên AI này chưa được gán kỹ năng.</small>'}</div>`);
  } else if (type === 'tool_call') {
    body += field('Công cụ', `<select onchange="updateRealNode('${id}','tool_name',this.value)"><option value="">-- Chọn công cụ --</option>${builderTools.map(t => `<option value="${esc(t.name)}" ${t.name === data.tool_name ? 'selected' : ''}>${esc(t.name)} — ${esc(t.description || '')}</option>`).join('')}</select>`);
    const tool = builderTools.find(t => t.name === data.tool_name);
    const props = tool?.parameters?.properties || {};
    body += Object.entries(props).map(([key, schema]) => field(
      `${key}${(tool.parameters.required || []).includes(key) ? ' *' : ''}`,
      schema.type === 'boolean'
        ? `<select onchange="updateToolArg('${id}','${esc(key)}',this.value,'boolean')"><option value="false">false</option><option value="true" ${data.args?.[key] === true ? 'selected' : ''}>true</option></select>`
        : `<input type="${schema.type === 'number' || schema.type === 'integer' ? 'number' : 'text'}" placeholder="${esc(schema.description || '')}" value="${esc(data.args?.[key] ?? schema.default ?? '')}" onchange="updateToolArg('${id}','${esc(key)}',this.value,'${schema.type || 'string'}')">`
    )).join('') || field('Tham số (JSON)', `<textarea rows="6" onchange="updateRealNodeJson('${id}','args',this.value)">${esc(JSON.stringify(data.args || {}, null, 2))}</textarea>`);
  } else if (type === 'condition') {
    body += field('Nguồn dữ liệu', input('field', data.field || 'last_output'));
    body += field('Phép so sánh', `<select onchange="updateRealNode('${id}','mode',this.value)">${['contains','equals','not_contains','regex'].map(v => `<option ${v === (data.mode || 'contains') ? 'selected' : ''}>${v}</option>`).join('')}</select>`);
    body += field('Giá trị', input('value', data.value || ''));
  } else if (type === 'set_data') {
    body += field('Dữ liệu cần đặt (JSON)', `<textarea rows="8" onchange="updateRealNodeJson('${id}','assignments',this.value)">${esc(JSON.stringify(data.assignments || {}, null, 2))}</textarea>`);
  } else if (type === 'delay') {
    body += field('Số giây chờ (tối đa 300)', input('seconds', data.seconds || 0, 'number'));
  } else if (type === 'stop_error') {
    body += field('Thông báo lỗi', input('message', data.message || 'Quy trình đã dừng'));
  } else if (type === 'workflow_call') {
    body += field('Tác vụ', `<select onchange="updateRealNode('${id}','target_task_id',Number(this.value))"><option value="">-- Chọn tác vụ --</option>${builderWorkflows.filter(w => String(w.id) !== String(currentWorkflowId)).map(w => `<option value="${w.id}" ${String(w.id) === String(data.target_task_id) ? 'selected' : ''}>${esc(w.name)}</option>`).join('')}</select>`);
    body += `<label class="se-check-row"><input type="checkbox" ${data.wait !== false ? 'checked' : ''} onchange="updateRealNode('${id}','wait',this.checked)"> <span>Chờ tác vụ chạy xong rồi lấy kết quả về bước tiếp theo</span></label>`;
    if (data.wait === false) {
      body += `<div class="se-empty-hint">Đang tắt chờ kết quả — tác vụ sẽ chạy nền, quy trình đi tiếp ngay và không nhận được kết quả trả về.</div>`;
    }
  } else if (type === 'approval_gate') {
    body += field('Người duyệt', input('approver', data.approver || 'CEO'));
    body += field('Lời nhắn cho người duyệt (tuỳ chọn)', `<textarea rows="3" onchange="updateRealNode('${id}','note',this.value)">${esc(data.note || '')}</textarea>`);
    body += field('Số lần thử lại tối đa khi bị từ chối', input('max_retries', data.max_retries || 3, 'number'));
    body += field('Hết hạn chờ duyệt (phút — 0 = chờ mãi)', input('timeout_minutes', data.timeout_minutes || 0, 'number'));
    body += field('Khi hết hạn thì', `<select onchange="updateRealNode('${id}','on_timeout',this.value)">
      ${[['fail','Dừng quy trình và báo lỗi'],['approve','Tự duyệt và đi tiếp'],['reject','Coi như từ chối, chạy lại bước trước']]
        .map(([value, label]) => `<option value="${value}" ${value === (data.on_timeout || 'fail') ? 'selected' : ''}>${label}</option>`).join('')}
    </select>`);
    body += `<div class="se-empty-hint">Khi chạy, popup sẽ hiện nội dung từ bước ngay trước node này để ${esc(data.approver || 'CEO')} xem/sửa. Duyệt → nội dung (đã sửa nếu có) đi tiếp bước sau. Không duyệt → bước trước chạy lại rồi hỏi duyệt lần nữa.</div>`;
    body += `<div class="se-empty-hint">Chạy nền (hẹn giờ / webhook / cuộc họp): không có popup, yêu cầu duyệt được gửi vào nhật ký dự án và vào cuộc họp đã kích hoạt quy trình.</div>`;
  } else if (type === 'noop') {
    body += `<label class="se-check-row"><input type="checkbox" ${data.parallel_out ? 'checked' : ''} onchange="updateRealNode('${id}','parallel_out',this.checked)"> <span>Chạy song song các nhánh đi ra</span></label>`;
  }
  return body;
}

function renderRealNodeInspector(node, insp, closeBtn) {
  const type = inferNodeType(node);
  const id = esc(node.id);
  const body = realNodeFieldsHtml(node);
  const meta = NODE_META[type] || NODE_META.noop;
  const triggerConfig = type === 'trigger' ? renderTriggerConfig(node) : '';
  const deleteDisabled = type === 'trigger'
    ? 'disabled title="Không thể xoá node bắt đầu"'
    : `onclick="deleteEditorNode('${id}')"`;
  insp.innerHTML = `<div class="inspector-header"><div class="node-icon" style="background:${node.color}">${svgIcon(node.icon)}</div><div><div class="inspector-title">${esc(node.title)}</div><div class="inspector-desc">${esc(meta.desc)}</div></div>${closeBtn}</div>
    ${ioInBlock(type)}
    <div class="insp-group-label">Cấu hình</div>
    <div class="inspector-section-body real-node-fields">${body}</div>
    ${triggerConfig}
    ${ioOutBlock(node,type)}
    <button class="inspector-delete-btn" ${deleteDisabled}>${svgIcon(ICONS.trash)} Xoá node</button>`;
}

function renderInspector(node) {
  const insp = document.getElementById('node-inspector');
  if (!node) {
    insp.classList.remove('open');
    document.querySelectorAll('.flow-node').forEach(el => el.classList.remove('selected'));
    setTimeout(() => { if (!insp.classList.contains('open')) insp.innerHTML = ''; renderMinimapViewport(); }, 220);
    return;
  }
  insp.classList.add('open');
  setTimeout(renderMinimapViewport, 220);

  const closeBtn = `<button class="inspector-close" onclick="renderInspector(null)">${svgIcon(ICONS.x)}</button>`;
  const deleteBtn = `<button class="inspector-delete-btn" onclick="showToast('Thao tác này chỉ khả dụng với quy trình đã lưu.','info')">${svgIcon(ICONS.trash)} Xoá node</button>`;
  if (currentWorkflowRecord) {
    renderRealNodeInspector(node, insp, closeBtn);
    return;
  }

  if (currentWorkflowType === 'company') {
    if (node.kind === 'start') {
      insp.innerHTML = `
        <div class="inspector-header">
          <div class="node-icon" style="background:${node.color}">${svgIcon(node.icon, true)}</div>
          <div>
            <div class="inspector-title">${node.title}</div>
            <div class="inspector-desc">${node.sub || 'Khởi chạy quy trình công ty'}</div>
          </div>
          ${closeBtn}
        </div>
        <div class="inspector-row">
          <span>Kích hoạt quy trình</span>
          <span>Trạng thái: <span class="status-pill">Đang chạy</span></span>
        </div>
        ${inspectorSection('play', 'Sự kiện kích hoạt', true, `
          <select>
            <option>Khách hàng gửi yêu cầu / Liên hệ</option>
            <option selected>Nhân viên tạo đề xuất thủ công</option>
            <option>Nhận hồ sơ mới từ cổng Web/Form</option>
            <option>Webhook từ phần mềm ERP/CRM bên ngoài</option>
          </select>
        `)}
        ${inspectorSection('doc', 'Hồ sơ đầu vào bắt buộc', true, `
          <div style="display:flex; flex-direction:column; gap:6px;">
            <label class="se-check-row">
              <input type="checkbox" checked /> <span>Thông tin liên hệ Khách hàng</span>
            </label>
            <label class="se-check-row">
              <input type="checkbox" checked /> <span>File đính kèm (Yêu cầu, Bản vẽ,...)</span>
            </label>
          </div>
        `)}
        ${deleteBtn}
      `;
    } else if (node.kind === 'end') {
      insp.innerHTML = `
        <div class="inspector-header">
          <div class="node-icon" style="background:${node.color}">${svgIcon(node.icon, true)}</div>
          <div>
            <div class="inspector-title">${node.title}</div>
            <div class="inspector-desc">${node.sub || 'Quy trình hoàn thành'}</div>
          </div>
          ${closeBtn}
        </div>
        ${inspectorSection('stop', 'Lưu trữ & Báo cáo', true, `
          <div style="font-size:11.5px;color:var(--text3)">
            Tất cả lịch sử ký duyệt và văn bản sẽ được lưu trữ tự động vào Kho lưu trữ số của công ty.
          </div>
        `)}
        ${inspectorSection('api', 'Hành động khi hoàn thành', true, `
          <div style="display:flex; flex-direction:column; gap:6px;">
            <label class="se-check-row">
              <input type="checkbox" checked /> <span>Gửi email báo cáo cho người khởi tạo</span>
            </label>
            <label class="se-check-row">
              <input type="checkbox" checked /> <span>Thông báo cho phòng ban liên quan</span>
            </label>
            <label class="se-check-row">
              <input type="checkbox" /> <span>Đồng bộ trạng thái sang ERP</span>
            </label>
          </div>
        `)}
        ${deleteBtn}
      `;
    } else {
      insp.innerHTML = `
        <div class="inspector-header">
          <div class="node-icon" style="background:${node.color}">${svgIcon(node.icon)}</div>
          <div>
            <div class="inspector-title">${node.title}</div>
            <div class="inspector-desc">${node.sub || 'Nhiệm vụ phòng ban'}</div>
          </div>
          ${closeBtn}
        </div>
        
        ${inspectorSection('person', 'Nhân sự phụ trách', true, `
          <div style="display:flex; flex-direction:column; gap:6px;">
            <div class="se-field-label" style="margin:0; font-size:10px;">Người duyệt / xử lý chính</div>
            <select style="background:var(--surface2); color:var(--text); border:1px solid var(--border);">
              <option>-- Chọn nhân sự duyệt --</option>
              <option selected>Nguyễn Văn A (Trưởng bộ phận)</option>
              <option>Trần Thị B (Chuyên viên phụ trách)</option>
              <option>Lê Hoàng C (Phó phòng)</option>
              <option>Tự động phân bổ theo khu vực</option>
            </select>
            <div class="se-field-label" style="margin:6px 0 0; font-size:10px;">Thời hạn xử lý (SLA)</div>
            <input type="text" value="24 giờ" placeholder="Ví dụ: 4 giờ, 2 ngày..." style="background:var(--surface2); color:var(--text); border:1px solid var(--border);" />
          </div>
        `)}

        ${inspectorSection('doc', 'Văn bản cần xử lý', true, `
          <div style="display:flex; flex-direction:column; gap:6px;">
            <label class="se-check-row">
              <input type="checkbox" checked /> <span>Ký số đóng dấu điện tử</span>
            </label>
            <label class="se-check-row">
              <input type="checkbox" checked /> <span>Yêu cầu đính kèm Tờ trình ngân sách</span>
            </label>
            <label class="se-check-row">
              <input type="checkbox" /> <span>Yêu cầu đính kèm File hợp đồng gốc</span>
            </label>
          </div>
        `)}

        ${inspectorSection('shuffle', 'Hành động chuyển giao', true, `
          <div style="display:flex; flex-direction:column; gap:6px;">
            <div class="se-field-label" style="margin:0; font-size:10px;">Khi hoàn thành/đạt, gửi tiếp cho</div>
            <select style="background:var(--surface2); color:var(--text); border:1px solid var(--border);">
              <option>-- Chọn bộ phận tiếp theo --</option>
              <option selected>Ban Giám đốc</option>
              <option>Phòng Kế toán</option>
              <option>Phòng Nhân sự</option>
              <option>Khách hàng (Kết thúc)</option>
            </select>
            
            <div class="se-field-label" style="margin:6px 0 0; font-size:10px;">Phương thức thông báo</div>
            <div style="display:flex; flex-direction:column; gap:4px;">
              <label class="se-check-row">
                <input type="checkbox" checked /> <span>Gửi thông báo email + SMS</span>
              </label>
              <label class="se-check-row">
                <input type="checkbox" checked /> <span>Đẩy thông báo qua hệ thống nội bộ</span>
              </label>
            </div>
          </div>
        `)}
        ${deleteBtn}
      `;
    }
  } else {
    if (node.kind === 'start') {
      insp.innerHTML = `
        <div class="inspector-header">
          <div class="node-icon" style="background:${node.color}">${svgIcon(node.icon, true)}</div>
          <div>
            <div class="inspector-title">Bắt Đầu</div>
            <div class="inspector-desc">Điểm khởi động — chọn cách kích hoạt quy trình</div>
          </div>
          ${closeBtn}
        </div>
        <div class="inspector-row">
          <span>Cách kích hoạt quy trình này</span>
          <span>Trạng thái: <span class="status-pill">Đang bật</span></span>
        </div>
        ${inspectorSection('play', 'Chạy tay', true, `<div style="font-size:11.5px;color:var(--text3)">Bấm nút "Chạy" ở góc trên để kích hoạt thủ công.</div>`)}
        ${inspectorSection('chat', 'Khi chat nhắc tới', true, `
          <div class="inspector-inline">
            <input type="text" id="trigger-keywords" value="tư vấn, đồ uống, món nào" />
            <button class="inspector-btn-mini" onclick="showToast('Tính năng này đang được phát triển.','info')">Lưu</button>
          </div>
        `)}
        ${inspectorSection('clock', 'Hẹn giờ tự chạy', true, `
          <select>
            <option>Hằng ngày 7:00 sáng</option>
            <option>Hằng tuần thứ Hai 8:00</option>
            <option>Không hẹn giờ</option>
          </select>
        `)}
        ${inspectorSection('globe', 'Hệ thống khác gọi vào (Webhook)', true, `
          <button class="inspector-btn-mini wide" onclick="showToast('Tính năng này đang được phát triển.','info')">${svgIcon(ICONS.link)} Sao chép địa chỉ</button>
        `)}
        ${inspectorSection('doc', 'Form cho mọi người điền', true, `
          <div class="inspector-inline">
            <button class="inspector-btn-mini wide" onclick="showToast('Tính năng này đang được phát triển.','info')">${svgIcon(ICONS.link)} Sao chép link</button>
            <button class="inspector-btn-mini wide" onclick="showToast('Tính năng này đang được phát triển.','info')">${svgIcon(ICONS.external)} Mở thử</button>
          </div>
        `)}
        ${inspectorSection('box', 'Được quy trình khác gọi', false, `
          <div style="font-size:11.5px;color:var(--text3)">Chưa có quy trình nào gọi tới bước này.</div>
        `)}
        ${deleteBtn}
      `;
    } else {
      insp.innerHTML = `
        <div class="inspector-header">
          <div class="node-icon" style="background:${node.color}">${svgIcon(node.icon)}</div>
          <div>
            <div class="inspector-title">${node.title}</div>
            <div class="inspector-desc">${node.sub || 'Cấu hình chi tiết cho bước này'}</div>
          </div>
          ${closeBtn}
        </div>
        ${inspectorSection('sliders', 'Cấu hình bước', true, `
          <div style="font-size:11.5px;color:var(--text3)">Giao diện mẫu — sẽ nối API cấu hình thật sau.</div>
        `)}
        ${deleteBtn}
      `;
    }
  }
}

function showListView() {
  document.getElementById('page-wrap').style.display = '';
  document.getElementById('view-editor').style.display = 'none';
  renderFilterTabs();
  renderGrid();
}

async function showEditorView(idOrSlug) {
  document.getElementById('page-wrap').style.display = 'none';
  document.getElementById('view-editor').style.display = 'flex';
  const w = findWorkflow(idOrSlug);
  await loadWorkflowSettings(idOrSlug);
  
  // Xác định loại quy trình: company hay automation
  currentWorkflowType = currentWorkflowRecord?.kind || w?.kind || currentMainTab;
  
  let savedGraph = null;
  try { savedGraph = JSON.parse(currentWorkflowRecord?.graph_json || 'null'); } catch {}
  if (savedGraph?.nodes?.length) {
    EDITOR_NODES = savedGraph.nodes.map(graphNodeToEditor);
    const triggerNode = EDITOR_NODES.find(node => inferNodeType(node) === 'trigger');
    if (triggerNode) triggerNode.data.triggers = normalizeTriggers(currentWorkflowRecord);
    EDITOR_NODES.forEach(refreshNodePresentation);
    EDITOR_EDGES = (savedGraph.edges || []).map(graphEdgeToEditor);
  } else {
    // Quy trình/tác vụ mới tạo — canvas trống, không kèm mẫu dựng sẵn.
    EDITOR_NODES = [];
    EDITOR_EDGES = [];
  }

  document.getElementById('editor-title').textContent = currentWorkflowRecord?.name || (w ? w.name : ('Quy trình #' + idOrSlug));
  renderPalette();
  renderCanvas();
  fitView();
  renderInspector(null);
  updateEditorViewMode();
  resumeBackgroundRun();
}

let currentEditorMode = localStorage.getItem('taskrunner_editor_mode') || 'simple';

function updateEditorViewMode() {
  const isSimple = currentEditorMode === 'simple';
  const palette = document.getElementById('node-palette');
  const canvasWrap = document.getElementById('canvas-wrap');
  const inspector = document.getElementById('node-inspector');
  const simpleContainer = document.getElementById('simple-editor-container');
  const modeBtn = document.getElementById('editor-mode-btn');

  if (isSimple) {
    if (palette) palette.style.display = 'none';
    if (canvasWrap) canvasWrap.style.display = 'none';
    if (inspector) inspector.style.display = 'none';
    if (simpleContainer) {
      simpleContainer.style.display = 'flex';
      renderSimpleWorkflow();
    }
    if (modeBtn) modeBtn.innerHTML = 'Chế độ: Đơn giản';
  } else {
    if (palette) palette.style.display = 'flex';
    if (canvasWrap) canvasWrap.style.display = 'block';
    if (inspector) inspector.style.display = '';
    if (simpleContainer) simpleContainer.style.display = 'none';
    if (modeBtn) modeBtn.innerHTML = 'Chế độ: Đồ thị';
    renderCanvas();
    renderInspector(null);
  }
  // Đổi chế độ không đụng tới run đang chạy trên server — đồng bộ lại nút Chạy/Huỷ.
  setRunningUI(!!activeRunId);
}

function toggleEditorMode() {
  currentEditorMode = currentEditorMode === 'simple' ? 'advanced' : 'simple';
  localStorage.setItem('taskrunner_editor_mode', currentEditorMode);
  updateEditorViewMode();
}

function updateSimpleNodeField(nodeId, field, value) {
  const node = EDITOR_NODES.find(n => n.id === nodeId);
  if (!node) return;
  if (field === 'title') {
    node.title = value;
    const titleEl = document.querySelector('#se-node-' + nodeId + ' .se-card-title');
    if (titleEl) titleEl.textContent = (EDITOR_NODES.indexOf(node) + 1) + '. ' + value;
  } else if (field === 'instructions') {
    node.sub = value;
    const subEl = document.querySelector('#se-node-' + nodeId + ' .se-card-subtitle');
    if (subEl) subEl.textContent = value;
  } else if (field === 'model') {
    node.model = value;
  } else if (field === 'rag') {
    node.rag = value;
  }
}

// ── Node "Điểm bắt đầu" trong chế độ Đơn giản ──────────────────────────────
// Dùng chung cấu hình kích hoạt thật (node.data.triggers) với chế độ Đồ thị,
// nhờ vậy thông tin điền ở đây được saveGraph() lưu xuống server.
const SIMPLE_TRIGGER_KEYS = ['manual', 'schedule', 'webhook', 'workflow_complete', 'meeting_decision'];

const SIMPLE_TRIGGER_LABEL = {
  manual: 'Chạy tay bằng nút bấm',
  schedule: 'Hẹn giờ tự động chạy',
  webhook: 'Hệ thống khác gọi vào (Webhook)',
  workflow_complete: 'Khi quy trình khác chạy xong',
  meeting_decision: 'Khi cuộc họp chốt biên bản',
};

function ensureNodeTriggers(node) {
  node.data = node.data || {};
  if (!node.data.triggers) node.data.triggers = normalizeTriggers(currentWorkflowRecord);
  return node.data.triggers;
}

function updateSimpleTriggerField(nodeId, key, patch, rerender = false) {
  const node = EDITOR_NODES.find(n => n.id === nodeId);
  if (!node) return;
  const triggers = ensureNodeTriggers(node);
  triggers[key] = {...(triggers[key] || {}), ...patch};
  if (rerender) renderSimpleWorkflow();
}

function renderSimpleStartBody(node) {
  const id = esc(node.id);
  const triggers = ensureNodeTriggers(node);
  const cron = triggers.schedule?.cron || '';
  const presets = ['0 * * * *', '0 8 * * *', '0 8 * * 1'];
  const token = triggers.webhook?.webhook_token || '';
  const webhookUrl = token ? `${location.origin}/api/workflow/hooks/${token}` : '';
  const isCompany = currentWorkflowType === 'company';

  const status = currentWorkflowRecord?.status || 'draft';
  const statusHint = status === 'active'
    ? ''
    : `<div class="se-empty-hint">Đang ở trạng thái "${esc(STATUS_LABEL[status] || status)}" — phải BẬT ${wfNoun()} thì các hình thức tự động mới chạy. Chạy tay vẫn được.</div>`;

  return `
    <div class="se-empty-hint">Điểm bắt đầu nhận mọi hình thức kích hoạt — điền cấu hình cho hình thức nào thì hình thức đó tự bật, và nhiều hình thức có thể kích hoạt đồng thời.</div>

    <div class="form-group">
      <div class="se-field-label">${isCompany ? 'Nhân viên bấm chạy tay' : 'Chạy tay bằng nút bấm'} — luôn sẵn sàng</div>
      <div class="se-empty-hint">Bấm "Chạy" hoặc "Chạy Thử" ở thanh trên để khởi chạy ngay.</div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div class="form-group">
        <div class="se-field-label">Hẹn giờ — lịch mẫu</div>
        <select class="se-input" onchange="if(this.value!=='custom')updateSimpleTriggerField('${id}','schedule',{cron:this.value},true)">
          <option value="custom" ${presets.includes(cron) ? '' : 'selected'}>Tuỳ chỉnh</option>
          <option value="0 * * * *" ${cron === '0 * * * *' ? 'selected' : ''}>Mỗi giờ</option>
          <option value="0 8 * * *" ${cron === '0 8 * * *' ? 'selected' : ''}>8h sáng hằng ngày</option>
          <option value="0 8 * * 1" ${cron === '0 8 * * 1' ? 'selected' : ''}>Thứ 2 hằng tuần</option>
        </select>
      </div>
      <div class="form-group">
        <div class="se-field-label">Biểu thức cron (để trống nếu không hẹn giờ)</div>
        <input class="se-input" value="${esc(cron)}" placeholder="0 8 * * *"
               onchange="updateSimpleTriggerField('${id}','schedule',{cron:this.value},true)">
      </div>
    </div>

    <div class="form-group">
      <div class="se-field-label">Hệ thống khác gọi vào (Webhook)</div>
      ${webhookUrl
        ? `<div style="display:flex;gap:8px;align-items:center;">
             <input class="se-input" readonly value="${esc(webhookUrl)}">
             <button class="inspector-btn-mini" onclick="copyWebhookUrl('${esc(webhookUrl)}')">Copy</button>
           </div>`
        : `<div class="se-empty-hint">Bấm Lưu để hệ thống sinh URL webhook cho ${wfNoun()} này.</div>`}
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div class="form-group">
        <div class="se-field-label">Khi quy trình khác chạy xong</div>
        <select class="se-input" onchange="updateSimpleTriggerField('${id}','workflow_complete',{source_task_id:Number(this.value)||null},true)">
          <option value="">— Không dùng —</option>
          ${builderWorkflows.filter(item => String(item.id) !== String(currentWorkflowId))
            .map(item => `<option value="${item.id}" ${String(item.id) === String(triggers.workflow_complete?.source_task_id) ? 'selected' : ''}>${esc(item.name)}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <div class="se-field-label">Khi cuộc họp chốt biên bản</div>
        <select class="se-input" onchange="updateSimpleTriggerField('${id}','meeting_decision',{project_id:Number(this.value)||null},true)">
          <option value="">— Không dùng —</option>
          ${workflowProjects.map(project => `<option value="${project.id}" ${String(project.id) === String(triggers.meeting_decision?.project_id) ? 'selected' : ''}>${esc(project.name)}</option>`).join('')}
        </select>
      </div>
    </div>
    ${statusHint}
  `;
}

// ── Đọc sơ đồ thành danh sách tuyến tính cho chế độ Đơn giản ───────────────
// Node Điều kiện không cắt danh sách thành nhiều nhánh song song: hai nhánh
// Đúng/Sai được gom vào bên trong chính thẻ của nó, nên danh sách ngoài luôn
// thẳng. Các bước sau điểm hợp nhánh lại chạy tiếp ở cấp ngoài.

function simpleNodeById(id) {
  return EDITOR_NODES.find(node => node.id === id) || null;
}

function simpleOutEdges(id) {
  return EDITOR_EDGES.filter(edge => edge[0] === id);
}

function simpleNext(id, label = '') {
  const edge = simpleOutEdges(id).find(item => (item[2] || '') === label);
  return edge ? edge[1] : null;
}

function simpleReachable(startId) {
  const seen = new Set();
  const stack = startId ? [startId] : [];
  while (stack.length) {
    const id = stack.pop();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    simpleOutEdges(id).forEach(edge => stack.push(edge[1]));
  }
  return seen;
}

/** Điểm hai nhánh gặp lại nhau — bước đầu tiên đi tới được từ cả hai phía. */
function simpleMergePoint(trueStart, falseStart, fallback) {
  if (!trueStart || !falseStart) return fallback || null;
  const fromFalse = simpleReachable(falseStart);
  const seen = new Set();
  const queue = [trueStart];
  while (queue.length) {
    const id = queue.shift();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    if (fromFalse.has(id)) return id;
    simpleOutEdges(id).forEach(edge => queue.push(edge[1]));
  }
  return fallback || null;
}

function buildSimpleChain(startId, stopId, visited) {
  const chain = [];
  let current = startId;
  while (current && current !== stopId && !visited.has(current)) {
    const node = simpleNodeById(current);
    if (!node) break;
    visited.add(current);
    if (inferNodeType(node) === 'condition') {
      const trueStart = simpleNext(current, 'Đúng');
      const falseStart = simpleNext(current, 'Sai');
      const merge = simpleMergePoint(trueStart, falseStart, stopId);
      chain.push({
        node,
        branches: {
          'Đúng': buildSimpleChain(trueStart, merge, visited),
          'Sai': buildSimpleChain(falseStart, merge, visited),
        },
      });
      current = merge;
    } else {
      chain.push({node});
      current = simpleNext(current, '');
    }
  }
  return chain;
}

/** Toàn bộ sơ đồ dưới dạng chuỗi entry. Node rời rạc vẫn được liệt kê ở cuối
 *  để không có bước nào biến mất khỏi giao diện. */
function buildSimpleSequence() {
  const visited = new Set();
  const start = EDITOR_NODES.find(node => inferNodeType(node) === 'trigger') || EDITOR_NODES[0];
  const chain = start ? buildSimpleChain(start.id, null, visited) : [];
  const orphans = EDITOR_NODES
    .filter(node => !visited.has(node.id))
    .map(node => ({node, orphan: true}));
  return chain.concat(orphans);
}

/** Xếp lại toạ độ cho khớp thứ tự đang hiện ở chế độ Đơn giản. Chỉ đụng x/y —
 *  các liên kết do thao tác thêm/xoá tự giữ đúng, không dựng lại tuyến tính. */
function relayoutSimpleNodes() {
  let column = 0;
  const place = (entries, y) => {
    entries.forEach(entry => {
      entry.node.x = 40 + column * 250;
      entry.node.y = y;
      column += 1;
      if (!entry.branches) return;
      const branchStart = column;
      let widest = column;
      ['Đúng', 'Sai'].forEach((label, index) => {
        column = branchStart;
        place(entry.branches[label], y + (index === 0 ? -150 : 150));
        widest = Math.max(widest, column);
      });
      column = widest;
    });
  };
  place(buildSimpleSequence(), 70);
}

// ── Bảng chọn loại bước khi chèn ───────────────────────────────────────────
// Dùng chung danh sách với palette của chế độ Đồ thị (qua paletteNodeSpec) nên
// hai chế độ luôn chèn ra cùng một loại node.
let _pendingInsert = null;

function simpleInsertablePalette() {
  const palette = currentWorkflowType === 'company' ? PALETTE_COMPANY : PALETTE_AUTOMATION;
  return palette
    .map(category => ({
      name: category.name,
      items: category.items.filter(item => paletteNodeSpec(item).type !== 'trigger'),
    }))
    .filter(category => category.items.length);
}

/** Mở bảng chọn; nhớ chỗ cần chèn để dùng lại khi người dùng chọn xong. */
function addSimpleStepAfter(nodeId, branchLabel = '') {
  if (!simpleNodeById(nodeId)) return;
  _pendingInsert = {nodeId, branchLabel};
  const source = simpleNodeById(nodeId);
  document.getElementById('pick-node-desc').textContent = branchLabel
    ? `Bước mới sẽ được chèn vào nhánh "${branchLabel}" của "${source.title}".`
    : `Bước mới sẽ được chèn ngay sau "${source.title}".`;
  document.getElementById('pick-node-list').innerHTML = simpleInsertablePalette().map((category, ci) => `
    <div>
      <div class="se-field-label" style="margin-bottom:8px">${esc(category.name)}</div>
      <div class="pick-node-grid">
        ${category.items.map((item, ii) => `
          <button class="pick-node-item" onclick="chooseSimpleStep(${ci},${ii})">
            <div class="node-icon" style="background:${item.color}">${svgIcon(item.icon)}</div>
            <div class="node-text">
              <span class="node-name">${esc(item.name)}</span>
              <span class="node-desc">${esc(item.desc)}</span>
            </div>
          </button>`).join('')}
      </div>
    </div>`).join('');
  document.getElementById('pick-node-modal').style.display = 'flex';
}

function closePickNodeModal() {
  document.getElementById('pick-node-modal').style.display = 'none';
  _pendingInsert = null;
}

function chooseSimpleStep(categoryIndex, itemIndex) {
  const item = simpleInsertablePalette()[categoryIndex]?.items[itemIndex];
  if (!item || !_pendingInsert) return closePickNodeModal();
  const {nodeId, branchLabel} = _pendingInsert;
  closePickNodeModal();
  insertSimpleStep(nodeId, branchLabel, paletteNodeSpec(item));
}

/** Chèn node theo spec ngay sau node cho trước. branchLabel = 'Đúng'/'Sai' khi
 *  chèn vào trong một nhánh của node Điều kiện. */
function insertSimpleStep(nodeId, branchLabel, spec) {
  if (!simpleNodeById(nodeId)) return;
  const newNode = {
    id: 'step_' + Date.now(),
    type: spec.type,
    kind: spec.type === 'condition' ? 'branch' : spec.type,
    title: spec.title,
    sub: '',
    color: spec.color,
    icon: spec.icon,
    data: {...(spec.data || {})},
  };
  refreshNodePresentation(newNode);
  const at = EDITOR_NODES.findIndex(node => node.id === nodeId);
  EDITOR_NODES.splice(at + 1, 0, newNode);
  // Đích cũ của cạnh này chuyển sang nối từ bước mới → chèn vào giữa, không đứt luồng.
  // Nếu bước mới là Điều kiện thì phần còn lại của luồng đi vào nhánh Đúng,
  // nhánh Sai để trống cho người dùng bổ sung.
  const carryLabel = inferNodeType(newNode) === 'condition' ? 'Đúng' : '';
  EDITOR_EDGES
    .filter(edge => edge[0] === nodeId && (edge[2] || '') === branchLabel)
    .forEach(edge => { edge[0] = newNode.id; edge[2] = carryLabel; });
  EDITOR_EDGES.push([nodeId, newNode.id, branchLabel, '']);
  relayoutSimpleNodes();
  renderSimpleWorkflow();
}

function deleteSimpleNode(nodeId) {
  const index = EDITOR_NODES.findIndex(node => node.id === nodeId);
  if (index === -1) return;
  const incoming = EDITOR_EDGES.filter(edge => edge[1] === nodeId);
  const outgoing = EDITOR_EDGES.filter(edge => edge[0] === nodeId);
  EDITOR_NODES.splice(index, 1);
  EDITOR_EDGES = EDITOR_EDGES.filter(edge => edge[0] !== nodeId && edge[1] !== nodeId);
  // Nối liền vết cắt: bước trước trỏ thẳng sang bước sau, giữ nguyên nhãn nhánh.
  const successor = outgoing[0]?.[1];
  if (successor) {
    incoming.forEach(([from, , label, color]) => {
      const duplicated = from === successor
        || EDITOR_EDGES.some(edge => edge[0] === from && edge[1] === successor && (edge[2] || '') === (label || ''));
      if (!duplicated) EDITOR_EDGES.push([from, successor, label || '', color || '']);
    });
  }
  relayoutSimpleNodes();
  renderSimpleWorkflow();
}

function addSimpleStartNode() {
  if (EDITOR_NODES.some(node => inferNodeType(node) === 'trigger')) return;
  const meta = NODE_META.trigger;
  const node = {
    id: 'node_' + Date.now(),
    type: 'trigger',
    kind: 'start',
    title: meta.title,
    sub: SIMPLE_TRIGGER_LABEL.manual,
    color: meta.color,
    icon: meta.icon,
    data: {triggers: normalizeTriggers(currentWorkflowRecord)},
  };
  const firstOrphan = EDITOR_NODES.find(item => !EDITOR_EDGES.some(edge => edge[1] === item.id));
  EDITOR_NODES.unshift(node);
  if (firstOrphan) EDITOR_EDGES.push([node.id, firstOrphan.id, '', '']);
  relayoutSimpleNodes();
  renderSimpleWorkflow();
}

// ── Vẽ danh sách bước ──────────────────────────────────────────────────────

function simpleNodeBodyHtml(node) {
  if (node.kind === 'start') return renderSimpleStartBody(node);
  if (node.kind === 'end') {
    return `<div style="font-size:12px;color:var(--text2);font-style:italic;">
      Quy trình sẽ dừng và lưu trữ báo cáo công việc tại đây.
    </div>`;
  }
  if (currentWorkflowRecord) {
    // Quy trình thật: dùng đúng bộ field của chế độ Đồ thị, ghi thẳng vào node.data
    return `<div class="real-node-fields">${realNodeFieldsHtml(node)}</div>`;
  }
  if (currentWorkflowType === 'company') {
    return `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="form-group">
          <div class="se-field-label">Tên bộ phận thực hiện</div>
          <input class="se-input" value="${esc(node.title)}" oninput="updateSimpleNodeField('${node.id}', 'title', this.value)" placeholder="Tên hiển thị phòng ban...">
        </div>
        <div class="form-group">
          <div class="se-field-label">Nhân sự duyệt chính</div>
          <select class="se-input">
            <option selected>Nguyễn Văn A (Trưởng bộ phận)</option>
            <option>Trần Thị B (Chuyên viên phụ trách)</option>
            <option>Lê Hoàng C (Phó phòng)</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <div class="se-field-label">Mô tả công việc cần xử lý ở bước này</div>
        <textarea class="se-textarea" oninput="updateSimpleNodeField('${node.id}', 'instructions', this.value)" placeholder="Mô tả công việc cần xử lý...">${esc(node.sub || '')}</textarea>
      </div>`;
  }
  return `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div class="form-group">
        <div class="se-field-label">Tên bước thực hiện</div>
        <input class="se-input" value="${esc(node.title)}" oninput="updateSimpleNodeField('${node.id}', 'title', this.value)" placeholder="Tên hiển thị bước...">
      </div>
      <div class="form-group">
        <div class="se-field-label">Bộ não AI xử lý</div>
        <select class="se-input" onchange="updateSimpleNodeField('${node.id}', 'model', this.value)">
          <option value="default" ${node.model === 'default' ? 'selected' : ''}>Tiêu chuẩn (Khuyên dùng)</option>
          <option value="fast" ${node.model === 'fast' ? 'selected' : ''}>Siêu nhanh & Tiết kiệm</option>
          <option value="creative" ${node.model === 'creative' ? 'selected' : ''}>Chuyên sâu & Sáng tạo</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <div class="se-field-label">Nhiệm vụ chi tiết (Yêu cầu nhân viên AI)</div>
      <textarea class="se-textarea" oninput="updateSimpleNodeField('${node.id}', 'instructions', this.value)" placeholder="Mô tả công việc cần xử lý ở bước này...">${esc(node.sub || '')}</textarea>
    </div>
    <div class="form-group">
      <label class="se-check-row">
        <input type="checkbox" ${node.rag ? 'checked' : ''} onchange="updateSimpleNodeField('${node.id}', 'rag', this.checked)">
        <span>Dùng thư viện Tri thức hỗ trợ (RAG)</span>
      </label>
    </div>`;
}

function simpleArrowHtml(nodeId, branchLabel, withTail) {
  return `
    <div class="se-arrow-wrap">
      <div class="se-arrow-icon">${icon('arrowDown')}</div>
      <button class="se-add-btn" onclick="addSimpleStepAfter('${nodeId}','${branchLabel}')">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Chèn bước mới
      </button>
      ${withTail ? `<div class="se-arrow-icon">${icon('arrowDown')}</div>` : ''}
    </div>`;
}

function simpleBranchHtml(node, label, chain, counter) {
  const isTrue = label === 'Đúng';
  const inner = chain.length
    ? renderSimpleChain(chain, counter)
    : `<div class="se-empty-hint">Chưa có bước nào cho nhánh này.</div>
       ${simpleArrowHtml(node.id, label, false)}`;
  return `
    <div class="se-branch ${isTrue ? 'is-true' : 'is-false'}">
      <div class="se-branch-head">${isTrue ? 'Nếu ĐÚNG' : 'Nếu SAI'}</div>
      <div class="se-branch-body">${inner}</div>
    </div>`;
}

function renderSimpleCard(entry, counter) {
  const node = entry.node;
  const isStart = node.kind === 'start';
  const isEnd = node.kind === 'end';
  const index = ++counter.value;

  let bodyHtml = simpleNodeBodyHtml(node);
  if (entry.branches) {
    bodyHtml += `<div class="se-branch-wrap">
      ${simpleBranchHtml(node, 'Đúng', entry.branches['Đúng'], counter)}
      ${simpleBranchHtml(node, 'Sai', entry.branches['Sai'], counter)}
    </div>`;
  }

  const deleteBtn = (!isStart && !isEnd)
    ? `<button class="se-card-delete" onclick="deleteSimpleNode('${node.id}')" title="Xóa bước này">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
       </button>`
    : '';

  const subtitle = isStart
    ? esc(activeTriggerLabels(ensureNodeTriggers(node)).join(' · ') || 'Khởi chạy quy trình')
    : isEnd ? 'Lưu trữ kết quả'
    : entry.orphan ? 'Chưa nối vào luồng nào'
    : esc(node.sub || 'Mô tả công việc');

  return `
    <div class="se-card${entry.orphan ? ' is-orphan' : ''}" id="se-node-${node.id}">
      <div class="se-card-header">
        <div class="se-card-icon" style="background:${node.color}">${svgIcon(node.icon, isStart)}</div>
        <div class="se-card-title-wrap">
          <div class="se-card-title">${index}. ${isStart ? 'Điểm Khởi Đầu' : isEnd ? 'Kết Thúc' : esc(node.title)}</div>
          <div class="se-card-subtitle">${subtitle}</div>
        </div>
        ${deleteBtn}
      </div>
      <div class="se-card-body">${bodyHtml}</div>
    </div>`;
}

/** Vẽ một chuỗi bước liên tiếp, kèm nút chèn giữa các bước và ở cuối chuỗi. */
function renderSimpleChain(chain, counter) {
  return chain.map((entry, index) => {
    const isLast = index === chain.length - 1;
    const noArrow = entry.orphan || entry.node.kind === 'end';
    const arrow = noArrow ? '' : simpleArrowHtml(entry.node.id, '', !isLast);
    return renderSimpleCard(entry, counter) + arrow;
  }).join('');
}

function renderSimpleWorkflow() {
  const container = document.getElementById('simple-editor-container');
  if (!container) return;

  const sequence = buildSimpleSequence();
  let html = renderSimpleChain(sequence, {value: 0});

  if (!EDITOR_NODES.length) {
    html = `
      <div class="se-card" style="text-align:center;padding:28px 20px;">
        <div class="se-card-title" style="margin-bottom:6px;">Chưa có bước nào</div>
        <div class="se-card-subtitle" style="margin-bottom:14px;">Thêm điểm bắt đầu để chọn cách kích hoạt ${wfNoun()} này.</div>
        <button class="se-add-btn" onclick="addSimpleStartNode()">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Thêm điểm bắt đầu
        </button>
      </div>`;
  }

  container.innerHTML = html;
  applyNodeRunStates();
}

function esc(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function openCreateWorkflowModal() {
  document.getElementById('create-workflow-title').textContent = `Tạo ${wfNoun()} mới`;
  document.getElementById('create-workflow-name-label').textContent = `Tên ${wfNoun()} *`;
  document.getElementById('create-workflow-kind-label').textContent =
    currentMainTab === 'company' ? 'Quy trình phối hợp công ty' : 'Tác vụ tự động';
  document.getElementById('create-workflow-name').value = '';
  document.getElementById('create-workflow-description').value = '';
  const select = document.getElementById('create-workflow-project');
  select.innerHTML = '<option value="">— Không gắn dự án —</option>';
  try {
    const data = await runnerApi('GET', '/projects/');
    select.insertAdjacentHTML('beforeend', (data.projects || []).map(
      project => `<option value="${project.id}">${esc(project.name)}</option>`
    ).join(''));
  } catch {}
  document.getElementById('create-workflow-modal').style.display = 'flex';
  setTimeout(() => document.getElementById('create-workflow-name').focus(), 0);
}

function closeCreateWorkflowModal() {
  document.getElementById('create-workflow-modal').style.display = 'none';
}

async function createWorkflowTask() {
  const name = document.getElementById('create-workflow-name').value.trim();
  if (!name) return showToast(`Vui lòng nhập tên ${wfNoun()}.`, 'error');
  const button = document.getElementById('create-workflow-submit');
  button.disabled = true;
  try {
    const projectId = document.getElementById('create-workflow-project').value;
    const task = await runnerApi('POST', '/workflow/tasks', {
      name,
      description: document.getElementById('create-workflow-description').value.trim(),
      project_id: projectId ? Number(projectId) : null,
      kind: currentMainTab,
    });
    closeCreateWorkflowModal();
    showToast(`Đã tạo ${wfNoun()} mới.`, 'success');
    openEditor(task.id);
  } catch (error) {
    showToast(`Không thể tạo ${wfNoun()}: ${error.message}`, 'error');
  } finally {
    button.disabled = false;
  }
}

function runTaskFromCard(taskId) {
  sessionStorage.setItem('xanax-run-workflow-on-open', String(taskId));
  openEditor(taskId);
}

async function toggleTaskStatus(taskId, status) {
  try {
    const updated = await runnerApi('PATCH', `/workflow/tasks/${taskId}`, {status});
    const task = REAL_TASKS.find(item => item.id === taskId);
    if (task) task.status = updated.status;
    if (currentWorkflowRecord && String(currentWorkflowRecord.id) === String(taskId)) {
      currentWorkflowRecord.status = updated.status;
      const selected = document.querySelector('.flow-node.selected')?.id?.replace(/^node-/, '');
      if (selected) selectNode(selected);
    }
    renderFilterTabs();
    renderGrid();
    showToast(status === 'active' ? `Đã bật ${wfNoun()}.` : `Đã tạm dừng ${wfNoun()}.`, 'success');
  } catch (error) {
    showToast(`Không thể cập nhật trạng thái: ${error.message}`, 'error');
  }
}

async function openRunHistory(taskId) {
  const task = REAL_TASKS.find(item => item.id === taskId);
  document.getElementById('run-history-title').textContent = `Lịch sử — ${task?.name || wfNoun(true)}`;
  const content = document.getElementById('run-history-content');
  content.innerHTML = '<div class="modal-desc">Đang tải...</div>';
  document.getElementById('run-history-modal').style.display = 'flex';
  try {
    const data = await runnerApi('GET', `/workflow/runs?task_id=${taskId}&limit=50`);
    const runs = data.runs || [];
    content.innerHTML = runs.length ? runs.map(run => `
      <div style="display:grid;grid-template-columns:1fr auto;gap:8px;padding:11px 0;border-bottom:1px solid var(--border)">
        <div><strong>#${run.id}</strong> · ${esc(run.triggered_by || 'manual')}<div style="font-size:11px;color:var(--text3);margin-top:3px">${relativeWorkflowTime(run.created_at)}</div></div>
        <span class="wf-status ${run.status === 'completed' ? 'active' : run.status === 'failed' ? 'failed' : 'paused'}"><span class="dot"></span>${esc(run.status)}</span>
      </div>`).join('') : `<div class="modal-desc">${wfNoun(true)} này chưa được chạy lần nào.</div>`;
  } catch (error) {
    content.innerHTML = `<div class="modal-desc">Không thể tải lịch sử: ${esc(error.message)}</div>`;
  }
}

function closeRunHistory() {
  document.getElementById('run-history-modal').style.display = 'none';
}

async function deleteWorkflowTask(taskId) {
  const task = REAL_TASKS.find(item => item.id === taskId);
  if (!(await showConfirm(
    `Xoá vĩnh viễn ${wfNoun()} "${task?.name || taskId}"?`,
    {title: `Xoá ${wfNoun()}?`, confirmLabel: `Xoá ${wfNoun(true)}`}
  ))) return;
  try {
    await runnerApi('DELETE', `/workflow/tasks/${taskId}`);
    REAL_TASKS = REAL_TASKS.filter(item => item.id !== taskId);
    renderFilterTabs();
    renderGrid();
    showToast(`Đã xoá ${wfNoun()}.`, 'success');
  } catch (error) {
    showToast(`Không thể xoá ${wfNoun()}: ${error.message}`, 'error');
  }
}

function relativeWorkflowTime(value) {
  if (!value) return 'Chưa chạy';
  const date = new Date(String(value).replace(' ', 'T') + (String(value).includes('Z') ? '' : 'Z'));
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return 'Vừa xong';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} phút trước`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} giờ trước`;
  if (seconds < 2592000) return `${Math.floor(seconds / 86400)} ngày trước`;
  return date.toLocaleDateString('vi-VN');
}

function graphNodesToFlowDots(graphJson) {
  let graph = null;
  try { graph = JSON.parse(graphJson || 'null'); } catch {}
  const nodes = graph?.nodes;
  if (!Array.isArray(nodes) || !nodes.length) return [];
  return [...nodes]
    .sort((a, b) => Number(a.x || 0) - Number(b.x || 0))
    .map(node => {
      const type = inferNodeType(node);
      const meta = NODE_META[type] || NODE_META.noop;
      return { title: node.data?.label || meta.title, color: node.color || meta.color };
    });
}

function legacyAgentsToFlowDots(agentsJson) {
  let agents = [];
  try { agents = JSON.parse(agentsJson || '[]'); } catch {}
  if (!Array.isArray(agents) || !agents.length) return [];
  return [
    { title: NODE_META.trigger.title, color: NODE_META.trigger.color },
    ...agents
      .sort((a, b) => (a.order || 0) - (b.order || 0))
      .map(a => ({ title: a.agent_name || NODE_META.agent.title, color: NODE_META.agent.color })),
  ];
}

async function loadWorkflowList() {
  try {
    const data = await runnerApi('GET', `/workflow/tasks?kind=${encodeURIComponent(currentMainTab)}`);
    REAL_TASKS = await Promise.all((data.tasks || []).map(async task => {
      let runs = [];
      try {
        const runData = await runnerApi('GET', `/workflow/runs?task_id=${task.id}&limit=10000`);
        runs = runData.runs || [];
      } catch {}
      const completed = runs.filter(run => run.status === 'completed').length;
      return {
        id: task.id,
        name: task.name,
        desc: task.description || 'Chưa có mô tả.',
        status: ['active', 'paused', 'draft', 'failed'].includes(task.status) ? task.status : 'active',
        successRate: runs.length ? Math.round(completed / runs.length * 1000) / 10 : 0,
        totalRuns: runs.length,
        lastRun: relativeWorkflowTime(runs[0]?.created_at),
        flow: (() => { const dots = graphNodesToFlowDots(task.graph_json); return dots.length ? dots : legacyAgentsToFlowDots(task.agents_json); })(),
        schedule: task.schedule_enabled ? task.schedule_cron : '',
        kind: task.kind,
        runs,
      };
    }));
  } catch (error) {
    REAL_TASKS = [];
    console.error('Không thể tải danh sách quy trình:', error);
  }
  renderFilterTabs();
  renderGrid();
}

async function init() {
  updateMainTabLabels();
  await loadWorkflowList();
  const wfId = _workflowIdFromOwnPath();
  if (wfId) {
    await showEditorView(wfId);
    if (sessionStorage.getItem('xanax-run-workflow-on-open') === String(currentWorkflowId)) {
      sessionStorage.removeItem('xanax-run-workflow-on-open');
      setTimeout(() => runWorkflow(false), 150);
    }
  } else {
    showListView();
  }
}
init();

// Ẩn topbar và main-tabs khi được nhúng vào hub qua iframe (tránh lồng 2 topbar)
if (new URLSearchParams(location.search).get('embed') === '1') {
  document.getElementById('topbar').style.display = 'none';
  const mainTabs = document.querySelector('.main-tabs');
  if (mainTabs) mainTabs.style.display = 'none';
}

// ── Theme sync với hub (light/dark) ───────────────────────────────────────
function _applyTheme(theme) {
  document.body.classList.toggle('light', theme === 'light');
}
_applyTheme(localStorage.getItem('hub_theme') || 'light');
window.addEventListener('storage', e => {
  if (e.key === 'hub_theme') _applyTheme(e.newValue || 'light');
});
