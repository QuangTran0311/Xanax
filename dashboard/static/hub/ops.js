import { agentById, agentDeptBadgeHtml, agentDeptSuffix, agents } from './agents.js';
import { api } from './api.js';
import { DEFAULT_AVATAR, avatarHtml } from './avatar.js';
import { icon } from './icons.js';
import { showToast } from './modals.js';
import { currentProjectId, currentProjectSubTab, projects, switchProjectSubTab } from './projects.js';
import { esc, renderOutputContent } from './utils.js';

// AI COMPANY PROJECT OPERATIONS DASHBOARD
// Một công ty có nhiều dự án; mỗi dự án có nhiều quy trình (workflow); mỗi quy trình
// tạo ra các đầu ra (output) khác nhau. Xanax đóng vai trò giám sát/điều phối, còn
// nhân viên AI (cấu hình ở tab Nhân sự) thực thi theo vai trò đã chọn khi dựng quy
// trình. CEO xem xét & duyệt đầu ra trước khi chuyển sang quy trình/hàng đợi kế tiếp.
// Dữ liệu lấy từ API thật /api/ops/* (xem api/routes/ops.py) — mỗi "item" ứng với
// 1 workflow_outputs thật, opsRuns/opsHistory chỉ là cache phía client cho lần render hiện tại.
// ════════════════════════════════════════
const OPS_STATUS = {
  pending:        { label: 'Chờ xử lý',      color: 'var(--muted)', bg: 'rgba(100,116,139,0.15)' },
  in_progress:    { label: 'Đang thực hiện', color: 'var(--blue)',  bg: 'rgba(var(--blue-rgb),0.15)'  },
  waiting_review: { label: 'Chờ CEO duyệt',  color: 'var(--amber)', bg: 'rgba(var(--amber-rgb),0.15)'  },
  needs_revision: { label: 'Cần chỉnh sửa',  color: '#f97316',      bg: 'rgba(249,115,22,0.15)'  },
  approved:       { label: 'Đã duyệt',       color: 'var(--cyan)',  bg: 'rgba(var(--cyan-rgb),0.15)'   },
  completed:      { label: 'Hoàn thành',     color: 'var(--green)', bg: 'rgba(var(--green-rgb),0.15)'   },
  failed:         { label: 'Thất bại',       color: 'var(--red)',   bg: 'rgba(var(--red-rgb),0.15)'   },
  test:           { label: 'Thử luồng',      color: 'var(--purple)', bg: 'rgba(var(--purple-rgb),0.15)' },
};
const OPS_KANBAN_COLS = ['pending', 'in_progress', 'waiting_review', 'needs_revision', 'approved', 'completed', 'failed', 'test'];
const OPS_OUTPUT_TYPES = { text: 'Văn bản', image: 'Hình ảnh', code: 'Code', report: 'Báo cáo' };
const OPS_PRIORITY_BADGE = { low: 'badge-muted', medium: 'badge-blue', high: 'badge-amber' };
function opsHistoryIcon(type) {
  const map = { run_completed: 'check', run_failed: 'close', run_started: 'bolt', approved: 'check', rejected: 'close', revision_requested: 'edit', queue_transition: 'sync' };
  return icon(map[type] || 'clock');
}

let opsRuns = [];
let opsHistory = [];
let opsFeedbackCtx = null; // { runId, action, isTest } đang chờ CEO nhập phản hồi trong modal

// SQLite lưu datetime dạng UTC "YYYY-MM-DD HH:MM:SS" (không có 'Z') — chuyển sang
// ISO trước khi parse để Date hiểu đúng là giờ UTC thay vì giờ local.
function opsFmtTime(ts) { return ts ? new Date(ts.replace(' ', 'T') + 'Z').toLocaleString('vi-VN') : '—'; }
function opsTimeValue(ts) { return ts ? Date.parse(ts.replace(' ', 'T') + 'Z') || 0 : 0; }
function opsProjectRuns(pid) { return opsRuns.filter(r => r.projectId === pid); }
function opsAgentSummary(r) {
  if (!r.agentCount) return 'Chưa có bước AI';
  if (r.agentCount === 1) return r.agentName || 'Nhân viên AI';
  return `${r.agentCount} nhân viên AI`;
}
function opsAgentListText(r) {
  const names = (r.agents || []).map(a => a.agentName).filter(Boolean);
  if (!names.length) return 'Chưa có bước AI';
  return names.join(', ');
}
function opsAgentDisplayHtml(r, opts = {}) {
  const label = esc(opsAgentSummary(r));
  const title = esc(opsAgentListText(r));
  if (!r.agentCount) return `<span title="${title}">${label}</span>`;
  if (r.agentCount > 1) return `<span title="${title}">${label}</span>`;
  const avatar = avatarHtml(r.agentColor || DEFAULT_AVATAR, r.agentName, 'avatar-sm');
  const dept = agentDeptBadgeHtml(agents.find(a => a.name === r.agentName));
  return `<span title="${title}" style="display:inline-flex;align-items:center;gap:6px;vertical-align:middle;">${avatar}<span>${label}</span>${dept}</span>`;
}

async function opsLoad(pid) {
  const [itemsData, historyData] = await Promise.all([
    api('GET', `/ops/items?project_id=${pid}`),
    api('GET', `/ops/history?project_id=${pid}`),
  ]);
  opsRuns = itemsData.items || [];
  opsHistory = historyData.history || [];
}

// Điểm điều phối chung: nạp lại dữ liệu thật từ server rồi render đúng sub-tab đang active.
export async function opsRenderSubTab(tab) {
  if (!currentProjectId) return;
  try {
    await opsLoad(currentProjectId);
  } catch (e) {
    showToast('Không tải được dữ liệu vận hành dự án: ' + e.message, 'error');
    return;
  }
  opsUpdateReviewBadge(currentProjectId);
  if (tab === 'overview') renderOpsOverview(currentProjectId);
  else if (tab === 'runs') renderOpsRuns(currentProjectId);
  else if (tab === 'review') renderOpsReview(currentProjectId);
  else if (tab === 'kanban') renderOpsKanban(currentProjectId);
  else if (tab === 'history') renderOpsHistory(currentProjectId);
}

function opsUpdateReviewBadge(pid) {
  const n = opsProjectRuns(pid).filter(r => r.status === 'waiting_review').length;
  const b = document.getElementById('ops-review-count');
  if (!b) return;
  if (n > 0) { b.textContent = n; b.style.display = 'inline-flex'; } else { b.style.display = 'none'; }
}

// ── Tổng quan ──
function renderOpsOverview(pid) {
  const el = document.getElementById('ops-overview-area');
  if (!el) return;
  const proj = projects.find(p => p.id === pid);
  const runs = opsProjectRuns(pid);
  const workflows = [...new Set(runs.map(r => r.workflowName))];
  const active = runs.filter(r => r.status === 'in_progress').length;
  const pendingApproval = runs.filter(r => r.status === 'waiting_review').length;
  const completed = runs.filter(r => r.status === 'completed').length;
  const failed = runs.filter(r => r.status === 'failed').length;
  const needsRevision = runs.filter(r => r.status === 'needs_revision').length;
  const readyRuns = runs.filter(r => r.readyForNext);
  const nextAction = pendingApproval > 0
    ? `Duyệt ${pendingApproval} kết quả đang chờ ở Hàng chờ duyệt`
    : needsRevision > 0
    ? `Theo dõi ${needsRevision} kết quả đang chờ nhân viên AI chỉnh sửa lại`
    : readyRuns.length > 0
    ? `${readyRuns.length} kết quả đã sẵn sàng chuyển sang bước kế tiếp — chuyển tiếp giúp đội nhé`
    : 'Đội của bạn không có việc gì cần duyệt ngay lúc này — thảnh thơi chút đi';

  el.innerHTML = `
    <div class="ops-grid">
      <div class="ops-card ops-card-wide">
        <div class="ops-card-label">Mục tiêu dự án</div>
        <div style="font-size:14px;font-weight:500;">${esc(proj?.description || 'Chưa có mô tả mục tiêu.')}</div>
        <div style="margin-top:10px;"><span class="badge ${proj ? 'badge-green' : 'badge-muted'}">${proj ? '<span class="sdot on" style="margin-right:5px;"></span>Đang hoạt động' : '—'}</span></div>
      </div>
      <div class="ops-card ops-card-wide" style="border-color:rgba(var(--amber-rgb),0.35);">
        <div class="ops-card-label">Việc bạn cần làm tiếp theo</div>
        <div style="font-size:13px;font-weight:600;margin-top:4px;">${esc(nextAction)}</div>
        ${pendingApproval > 0 ? `<button class="btn btn-primary btn-sm" style="margin-top:8px;" onclick="switchProjectSubTab('review')">Đến Hàng chờ duyệt →</button>` : ''}
      </div>
      <div class="ops-card"><div class="ops-card-label">Quy trình</div><div class="ops-card-value">${workflows.length}</div></div>
      <div class="ops-card"><div class="ops-card-label">Đang thực hiện</div><div class="ops-card-value" style="color:var(--blue)">${active}</div></div>
      <div class="ops-card"><div class="ops-card-label">Chờ CEO duyệt</div><div class="ops-card-value" style="color:var(--amber)">${pendingApproval}</div></div>
      <div class="ops-card">
        <div class="ops-card-label">Hoàn thành / Thất bại</div>
        <div class="ops-card-value"><span style="color:var(--green)">${completed}</span><span style="color:var(--muted);font-size:14px;"> / </span><span style="color:var(--red)">${failed}</span></div>
      </div>
      <div class="ops-card ops-card-wide ops-xanax-card">
        <div style="display:flex;align-items:center;gap:10px;">
          <div class="avatar" style="background:var(--gold-soft);color:var(--gold);">${icon('bot')}</div>
          <div>
            <div style="font-weight:700;font-size:14px;">Xanax — Giám sát &amp; Điều phối</div>
            <div style="font-size:11px;color:var(--muted);">Theo dõi toàn bộ quy trình, điều phối nhân viên AI theo vai trò đã cấu hình ở tab Nhân sự, chờ CEO duyệt trước khi chuyển bước tiếp theo.</div>
          </div>
        </div>
        <div style="display:flex;gap:18px;margin-top:12px;font-size:12px;color:var(--text);">
          <span>${icon('sync')} ${runs.length} lượt chạy</span>
          <span>${icon('people')} ${new Set(runs.flatMap(r => (r.agents || []).map(a => a.agentId || a.agentName))).size} nhân viên AI tham gia</span>
          <span>⏳ ${pendingApproval} chờ duyệt</span>
        </div>
      </div>
    </div>`;
}

// ── Lượt chạy ──
function renderOpsRuns(pid) {
  const tbody = document.getElementById('ops-runs-tbody');
  if (!tbody) return;
  const runs = opsProjectRuns(pid).slice().sort((a, b) => opsTimeValue(b.startedAt || b.finishedAt) - opsTimeValue(a.startedAt || a.finishedAt));
  if (!runs.length) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:30px;">Chưa có lượt chạy nào</td></tr>`;
    return;
  }
  tbody.innerHTML = runs.map(r => {
    const st = OPS_STATUS[r.status];
    return `<tr>
      <td>${esc(r.workflowName)}</td>
      <td>${OPS_OUTPUT_TYPES[r.outputType] || r.outputType}</td>
      <td>${opsAgentDisplayHtml(r, { withName: true })}</td>
      <td><span class="badge" style="background:${st.bg};color:${st.color};">${st.label}</span></td>
      <td style="font-size:11px;color:var(--muted);">${opsFmtTime(r.startedAt)}</td>
      <td style="font-size:11px;color:var(--muted);">${opsFmtTime(r.finishedAt)}</td>
      <td style="max-width:220px;font-size:12px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(r.summary)}</td>
      <td><button class="btn btn-ghost btn-sm" onclick="openOpsDetails(${r.id})">Xem</button></td>
    </tr>`;
  }).join('');
}

// ── Hàng chờ duyệt (CEO review) ──
function renderOpsReview(pid) {
  const el = document.getElementById('ops-review-list');
  if (!el) return;
  const items = opsProjectRuns(pid).filter(r => r.status === 'waiting_review').sort((a, b) => opsTimeValue(a.startedAt) - opsTimeValue(b.startedAt));
  if (!items.length) {
    el.innerHTML = `<div class="empty-state" style="margin-top:60px;"><div class="empty-state-icon">${icon('check')}</div><div class="empty-state-text">Không có kết quả nào đang chờ duyệt</div></div>`;
    return;
  }
  el.innerHTML = items.map(r => `
    <div class="ops-review-card">
      <div class="ops-review-card-head">
        <div>
          <div style="font-weight:600;font-size:13px;">${esc(r.workflowName)} <span style="color:var(--muted);font-weight:400;">· ${OPS_OUTPUT_TYPES[r.outputType] || r.outputType}</span></div>
          <div style="font-size:11px;color:var(--muted);margin-top:2px;display:flex;align-items:center;gap:5px;">
            ${opsAgentDisplayHtml(r)} <span>· ${opsFmtTime(r.startedAt)}</span>
          </div>
        </div>
        <span class="badge ${OPS_PRIORITY_BADGE[r.priority] || 'badge-muted'}">${esc(r.priority)}</span>
      </div>
      <div class="ops-review-card-summary">${esc(r.summary)}</div>
      <div class="ops-review-card-actions">
        <button class="btn btn-sm btn-pass" onclick="opsApprove(${r.id})">${icon('check')} Duyệt</button>
        <button class="btn btn-sm btn-fail" onclick="opsOpenFeedback(${r.id},'failed')">${icon('close')} Không đạt</button>
        <button class="btn btn-sm btn-ghost" onclick="opsOpenFeedback(${r.id},'needs_revision')">${icon('edit')} Yêu cầu sửa</button>
        <button class="btn btn-sm ops-btn-test" onclick="opsApprove(${r.id}, true)" title="Chỉ thử luồng quy trình — không ghi lịch sử/bộ nhớ Xanax">${icon('flask')} Thử luồng</button>
        <button class="btn btn-sm btn-ghost" onclick="openOpsDetails(${r.id})">Chi tiết</button>
      </div>
    </div>`).join('');
}

// isTest: true khi bấm nút "Thử luồng" kế bên Duyệt/Không đạt — chỉ để CEO thử luồng
// quy trình, KHÔNG phải quyết định duyệt thật nên server chuyển item sang trạng thái
// riêng "test" (khác Đã duyệt/Chờ xử lý), vẫn hiển thị bình thường trên Kanban/Runs,
// chỉ ra khỏi hàng chờ duyệt vì đã được xử lý. Không ghi lịch sử/bộ nhớ Xanax.
export async function opsApprove(runId, isTest) {
  try {
    await api('POST', `/ops/items/${runId}/approve`, { is_test: !!isTest });
    await opsRenderSubTab(currentProjectSubTab);
    showToast(isTest ? 'Đã chuyển sang chế độ thử luồng.' : 'Đã duyệt kết quả.', 'success');
  } catch (e) { showToast('Lỗi: ' + e.message, 'error'); }
}

export function opsOpenFeedback(runId, action, isTest) {
  const r = opsRuns.find(x => x.id === runId);
  if (!r) return;
  opsFeedbackCtx = { runId, action, isTest: !!isTest };
  document.getElementById('ops-feedback-title').textContent = action === 'failed' ? 'Đánh dấu Không đạt' : 'Yêu cầu chỉnh sửa';
  document.getElementById('ops-feedback-run-name').textContent = `${r.workflowName} · ${opsAgentSummary(r)}` + (isTest ? ' · chế độ thử luồng' : '');
  document.getElementById('ops-feedback-text').value = '';
  document.getElementById('ops-feedback-modal').classList.remove('hidden');
}

export async function opsSaveFeedback() {
  if (!opsFeedbackCtx) return;
  const { runId, action, isTest } = opsFeedbackCtx;
  const text = document.getElementById('ops-feedback-text').value.trim();
  if (!text) { showToast('Vui lòng nhập phản hồi cho nhân viên AI.', 'error'); return; }
  try {
    await api('POST', `/ops/items/${runId}/feedback`, { action, text, is_test: !!isTest });
    document.getElementById('ops-feedback-modal').classList.add('hidden');
    opsFeedbackCtx = null;
    await opsRenderSubTab(currentProjectSubTab);
    showToast(isTest ? 'Đã chuyển sang chế độ thử luồng.' : 'Đã lưu phản hồi.', 'success');
  } catch (e) { showToast('Lỗi: ' + e.message, 'error'); }
}

// ── Chi tiết 1 lượt chạy ──
export async function openOpsDetails(runId) {
  const r = opsRuns.find(x => x.id === runId);
  if (!r) return;
  const st = OPS_STATUS[r.status];
  document.getElementById('ops-details-title').textContent = r.workflowName;
  document.getElementById('ops-details-body').innerHTML = `<div style="color:var(--muted);font-size:12px;">Đang tải chi tiết lượt chạy...</div>`;
  document.getElementById('ops-details-modal').classList.remove('hidden');
  try {
    const run = await api('GET', `/workflow/runs/${runId}`);
    const outputs = run.outputs || [];
    const stepHtml = outputs.length
      ? outputs.map(o => `
        <div style="border:1px solid var(--border);border-radius: 0;padding:10px 12px;background:var(--bg3);margin-top:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:6px;">
              ${avatarHtml(agentById(o.agent_id)?.avatar_color || r.agentColor || DEFAULT_AVATAR, o.agent_name || 'Nhân viên AI', 'avatar-sm')}
              <span style="font-size:13px;font-weight:600;">Bước ${o.step_order || 0} · ${esc(o.agent_name || 'Nhân viên AI')}${agentDeptSuffix(agentById(o.agent_id))}</span>
            </div>
            <span style="font-size:11px;color:var(--muted);">${opsFmtTime(o.finished_at || o.created_at)}</span>
          </div>
          <div class="output-content">${renderOutputContent(o.edited_content || o.output_content) || '(chưa có nội dung)'}</div>
        </div>`).join('')
      : `<div class="output-content">${renderOutputContent(r.outputPreview)}</div>`;

    document.getElementById('ops-details-body').innerHTML = `
      <div class="form-group"><label class="form-label">Nhân viên AI tham gia</label>
        <div style="font-size:13px;">${esc(opsAgentListText(r))}</div>
      </div>
      <div class="form-group"><label class="form-label">Trạng thái</label>
        <span class="badge" style="background:${st.bg};color:${st.color};">${st.label}</span>
        ${r.readyForNext ? `<span class="badge badge-green" style="margin-left:6px;">${icon('arrowRight')} Sẵn sàng bước kế tiếp</span>` : ''}
      </div>
      <div class="form-group"><label class="form-label">Loại đầu ra</label><div>${OPS_OUTPUT_TYPES[r.outputType] || r.outputType}</div></div>
      <div class="form-group"><label class="form-label">Số bước AI</label><div>${outputs.length || r.outputCount || 0}</div></div>
      <div class="form-group"><label class="form-label">Thời gian</label>
        <div style="font-size:12px;color:var(--muted);">Bắt đầu: ${opsFmtTime(r.startedAt)} · Kết thúc: ${opsFmtTime(r.finishedAt)}</div>
      </div>
      <div class="form-group"><label class="form-label">Tóm tắt</label><div style="font-size:13px;">${esc(r.summary)}</div></div>
      <div class="form-group"><label class="form-label">Chi tiết từng bước</label>${stepHtml}</div>
      ${r.feedback ? `<div class="form-group"><label class="form-label">Phản hồi CEO</label><div style="font-size:13px;color:var(--amber);">${esc(r.feedback)}</div></div>` : ''}
    `;
  } catch (e) {
    document.getElementById('ops-details-body').innerHTML = `<div style="color:var(--red);font-size:12px;">Không tải được chi tiết: ${esc(e.message || 'Lỗi không xác định')}</div>`;
  }
}

// ── Kanban (theo trạng thái lượt chạy) ──
function renderOpsKanban(pid) {
  const board = document.getElementById('ops-kanban-board');
  if (!board) return;
  const runs = opsProjectRuns(pid);
  board.innerHTML = OPS_KANBAN_COLS.map(status => {
    const colRuns = runs.filter(r => r.status === status);
    const st = OPS_STATUS[status];
    return `
      <div class="kanban-col">
        <div class="kanban-col-header">
          <span class="kanban-col-title" style="color:${st.color};">${st.label}</span>
          <span class="kanban-col-count">${colRuns.length}</span>
        </div>
        <div class="kanban-cards" id="ops-col-${status}" ondragover="opsColDragOver(event)" ondragleave="opsColDragLeave(event)" ondrop="opsColDrop(event,'${status}')">
          ${colRuns.map(r => opsRenderKanbanCard(r)).join('')}
        </div>
      </div>`;
  }).join('');
}

function opsRenderKanbanCard(r) {
  const priClass = OPS_PRIORITY_BADGE[r.priority] || 'badge-muted';
  const shortSummary = r.summary.length > 60 ? r.summary.slice(0, 60) + '…' : r.summary;
  const quick = r.status === 'waiting_review' ? `
      <div class="kanban-card-meta" style="margin-top:6px;">
        <button class="btn btn-sm btn-pass" onclick="event.stopPropagation();opsApprove(${r.id})">${icon('check')} Duyệt</button>
        <button class="btn btn-sm btn-fail" onclick="event.stopPropagation();opsOpenFeedback(${r.id},'failed')" title="Không đạt">${icon('close')}</button>
        <button class="btn btn-sm ops-btn-test" onclick="event.stopPropagation();opsApprove(${r.id}, true)" title="Chỉ thử luồng quy trình — không ghi lịch sử/bộ nhớ Xanax">${icon('flask')} Thử luồng</button>
      </div>` : '';
  const readyBadge = r.readyForNext
    ? `<span class="badge badge-green" title="Sẵn sàng chuyển sang quy trình/bước kế tiếp">${icon('arrowRight')} Sẵn sàng bước kế tiếp</span>` : '';
  return `
    <div class="kanban-card" draggable="true" ondragstart="opsCardDragStart(event,${r.id})" onclick="openOpsDetails(${r.id})">
      <div class="kanban-card-title">${esc(r.workflowName)}</div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px;">${OPS_OUTPUT_TYPES[r.outputType] || r.outputType} · ${esc(shortSummary)}</div>
      <div class="kanban-card-meta">
        <span class="badge ${priClass}">${esc(r.priority)}</span>
        <span style="font-size:11px;color:var(--muted);">${opsAgentDisplayHtml(r)}</span>
        ${readyBadge}
      </div>
      <div style="font-size:10px;color:var(--muted);margin-top:6px;">${opsFmtTime(r.startedAt)}</div>
      ${quick}
    </div>`;
}

function opsCardDragStart(e, runId) {
  e.dataTransfer.setData('text/plain', String(runId));
  e.dataTransfer.effectAllowed = 'move';
}
function opsColDragOver(e) { e.preventDefault(); e.currentTarget.classList.add('drag-over'); }
function opsColDragLeave(e) { e.currentTarget.classList.remove('drag-over'); }
function opsColDrop(e, status) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const runId = e.dataTransfer.getData('text/plain');
  opsMoveRun(runId, status);
}

// Kéo-thả đổi cột = gọi API thật cập nhật review_status (PATCH /ops/items/{id}).
// Kéo vào "waiting_review" sẽ tự xuất hiện ở tab Hàng chờ duyệt vì cùng đọc từ /ops/items.
async function opsMoveRun(runId, status) {
  const id = Number(runId);
  const r = opsRuns.find(x => x.id === id);
  if (!r || r.status === status) return;
  try {
    await api('PATCH', `/ops/items/${id}`, { status });
    await opsRenderSubTab(currentProjectSubTab);
  } catch (e) { showToast('Lỗi: ' + e.message, 'error'); }
}

// ── Lịch sử ──
function renderOpsHistory(pid) {
  const el = document.getElementById('ops-history-area');
  if (!el) return;
  const items = opsHistory.filter(h => opsRuns.find(r => r.id === h.runId)?.projectId === pid);
  if (!items.length) {
    el.innerHTML = `<div class="empty-state" style="margin-top:60px;"><div class="empty-state-icon">${icon('clock')}</div><div class="empty-state-text">Chưa có lịch sử nào</div></div>`;
    return;
  }
  el.innerHTML = items.map(h => `
    <div class="history-row">
      <span>${opsHistoryIcon(h.type)}</span>
      <span style="flex:1;font-size:13px;">${esc(h.text)}</span>
      <span style="font-size:11px;color:var(--muted);">${opsFmtTime(h.ts)}</span>
    </div>`).join('');
}

// Gom kết quả hoàn thành/thất bại + phản hồi CEO thành dữ liệu học cho Xanax —
// archivePayload đã được server chuẩn bị sẵn (xem api/routes/ops.py _archive_payload),
// hàm này chỉ gom lại phía client để chuẩn bị gọi API ghi vào SOUL.md sau này.
function opsBuildLearningMemoryEntries(pid) {
  return opsProjectRuns(pid)
    .filter(r => r.archivePayload || r.feedback)
    .map(r => r.archivePayload || {
      workflow: r.workflowName, agent: opsAgentSummary(r), status: r.status,
      summary: r.summary, feedback: r.feedback, finishedAt: r.finishedAt,
    });
}

// ════════════════════════════════════════
