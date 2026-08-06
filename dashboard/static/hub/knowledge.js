import { agentById, agentDeptBadgeHtml, agentDeptSuffix, agents } from './agents.js';
import { api } from './api.js';
import { DEFAULT_AVATAR, avatarHtml } from './avatar.js';
import { icon } from './icons.js';
import { closeModal, showConfirm, showToast } from './modals.js';
import { closeProjectDetail, currentProjectId, loadProjects, projects } from './projects.js';
import { t } from './ui.js';
import { esc, jattr, renderOutputContent } from './utils.js';

// KNOWLEDGE DOCUMENTS (RAG "phòng tư liệu")
// ════════════════════════════════════════
let knowledgeDocs = [];

async function loadKnowledgeDocs(pid) {
  const el = document.getElementById('knowledge-list');
  if (!el) return;
  const data = await api('GET', `/knowledge?project_id=${pid}`).catch(() => ({ documents: [] }));
  knowledgeDocs = data.documents || [];
  if (!knowledgeDocs.length) {
    el.innerHTML = `<div class="empty-state" style="margin-top:40px;"><div class="empty-state-icon">${icon('book')}</div><div class="empty-state-text">Chưa có tài liệu nào cho dự án này</div></div>`;
    return;
  }
  el.innerHTML = knowledgeDocs.map(d => `
    <div style="border:1px solid var(--border);border-radius: 0;padding:12px 14px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
        <div style="font-weight:600;font-size:13px;">${esc(d.title)}</div>
        <div style="display:flex;gap:6px;flex-shrink:0;">
          <button class="btn btn-ghost btn-sm" data-click="openKnowledgeModal" data-click-args='${jattr(d.id)}'>Sửa</button>
          <button class="btn btn-danger btn-sm" data-click="deleteKnowledgeDoc" data-click-args='${jattr(d.id)}'>Xoá</button>
        </div>
      </div>
      ${d.tags ? `<div style="font-size:11px;color:var(--muted);margin-top:3px;">${icon('tag')} ${esc(d.tags)}</div>` : ''}
      <div style="font-size:12px;color:var(--muted);margin-top:6px;white-space:pre-wrap;max-height:80px;overflow:hidden;">${esc((d.content||'').slice(0,300))}</div>
    </div>`).join('');
}

export function openKnowledgeModal(id) {
  const doc = id ? knowledgeDocs.find(d => d.id === id) : null;
  const title = prompt('Tiêu đề tài liệu:', doc?.title || '');
  if (title === null) return;
  if (!title.trim()) { showToast('Tiêu đề không được để trống', 'error'); return; }
  const tags = prompt('Tags (phân cách bởi dấu phẩy, tuỳ chọn):', doc?.tags || '') || '';
  const content = prompt('Nội dung tài liệu:', doc?.content || '');
  if (content === null) return;
  saveKnowledgeDoc(id, title.trim(), content, tags.trim());
}

async function saveKnowledgeDoc(id, title, content, tags) {
  const body = { title, content, tags, project_id: currentProjectId };
  if (id) await api('PATCH', `/knowledge/${id}`, body);
  else await api('POST', '/knowledge', body);
  await loadKnowledgeDocs(currentProjectId);
}

export async function deleteKnowledgeDoc(id) {
  if (!(await showConfirm('Xoá tài liệu này?'))) return;
  await api('DELETE', `/knowledge/${id}`);
  await loadKnowledgeDocs(currentProjectId);
}

async function loadProject() {
  if (!currentProjectId) { renderKanban(null); return; }
  const [itemsData, alertsData] = await Promise.all([
    api('GET', `/projects/${currentProjectId}/items`),
    api('GET', '/projects/items/alerts').catch(() => ({ count: 0, alerts: [] })),
  ]);
  renderKanban(itemsData.items || []);
  updateAlertBanner(alertsData.count || 0);
}

async function loadProjectResults(pid) {
  const area = document.getElementById('proj-results-area');
  area.innerHTML = '<div style="color:var(--muted);font-size:12px;padding:20px;">Đang tải...</div>';
  try {
    const data = await api('GET', `/workflow/runs?project_id=${pid}&limit=50`);
    const runs = (data.runs || []).filter(r => r.status !== 'running' && r.status !== 'pending');
    if (!runs.length) {
      area.innerHTML = `<div class="empty-state" style="margin-top:60px;"><div class="empty-state-icon">${icon('chart')}</div><div class="empty-state-text">Chưa có kết quả nào cho dự án này</div></div>`;
      return;
    }
    area.innerHTML = '<div style="color:var(--muted);font-size:12px;padding:8px 0 16px;">Đang tải chi tiết...</div>';
    const SC = {completed:'var(--green)',failed:'var(--red)',cancelled:'var(--muted)'};
    const SL = {completed:'Hoàn thành',failed:'Thất bại',cancelled:'Đã huỷ'};
    const groups = await Promise.all(runs.map(r => api('GET', `/workflow/runs/${r.id}`).catch(() => null)));
    area.innerHTML = '';
    for (const runData of groups) {
      if (!runData) continue;
      const outputs = runData.outputs || [];
      if (!outputs.length) continue;
      const sc = SC[runData.status] || 'var(--muted)';
      const sl = SL[runData.status] || runData.status;
      const time = runData.started_at ? new Date(runData.started_at + 'Z').toLocaleString('vi-VN') : '—';
      const g = document.createElement('div');
      g.className = 'run-group';
      g.innerHTML = `
        <div class="run-group-header">
          <span>${icon('sync')}</span>
          <span class="run-group-title">${esc(runData.task_name||'Quy trình')}</span>
          <span style="font-size:11px;color:${sc};">${sl}</span>
          <span style="font-size:11px;color:var(--muted);">${time}</span>
        </div>
        <div class="run-group-body">${outputs.map(o => renderOutputItem(o)).join('')}</div>`;
      area.appendChild(g);
    }
  } catch {
    area.innerHTML = '<div style="color:var(--red);font-size:12px;padding:20px;">Không tải được kết quả.</div>';
  }
}

function renderOutputItem(o) {
  const content = renderOutputContent(o.edited_content || o.output_content);
  const pf = o.pass_fail;
  const pfBadge = pf === 'pass'
    ? '<span class="badge" style="background:rgba(var(--green-rgb),0.15);color:var(--green);">' + icon('check') + ' Đạt</span>'
    : pf === 'fail'
    ? '<span class="badge" style="background:rgba(var(--red-rgb),0.15);color:var(--red);">' + icon('close') + ' Không đạt</span>'
    : '';
  return `<div class="output-item" id="oi-${o.id}">
    <div class="output-header">
      <span class="output-agent">Bước ${o.step_order} · ${esc(o.agent_name)}${agentDeptSuffix(agents.find(a => a.name === o.agent_name))}</span>
      ${pfBadge}
    </div>
    <div class="output-content" id="oc-${o.id}" contenteditable="false">${content}</div>
    <div class="output-actions">
      <button class="btn btn-sm btn-pass${pf==='pass'?' selected':''}" ${pf?'disabled':''} ${pf&&pf!=='pass'?'style="display:none"':''} data-click="setOutputPF" data-click-args='${jattr(o.id, "pass", "$el")}'>${icon('check')} Đạt</button>
      <button class="btn btn-sm btn-fail${pf==='fail'?' selected':''}" ${pf?'disabled':''} ${pf&&pf!=='fail'?'style="display:none"':''} data-click="setOutputPF" data-click-args='${jattr(o.id, "fail", "$el")}'>${icon('close')} Không đạt</button>
      <button class="btn btn-sm btn-ghost" data-click="toggleOutputEdit" data-click-args='${jattr(o.id, "$el")}'>${icon('edit')} Sửa</button>
      <button class="btn btn-sm btn-ghost" data-click="copyOutput" data-click-args='${jattr(o.id)}' title="Sao chép">${icon('document')}</button>
    </div>
    <textarea class="output-notes" placeholder="Ghi chú / phản hồi..." data-change="saveOutputNotes" data-change-args='${jattr(o.id, "$value")}'>${esc(o.notes||'')}</textarea>
  </div>`;
}

export async function setOutputPF(outputId, value, btn) {
  const newVal = btn.classList.contains('selected') ? null : value;
  await api('PATCH', `/workflow/outputs/${outputId}`, { pass_fail: newVal });
  loadProjectResults(currentProjectId);
}

export function toggleOutputEdit(outputId, btn) {
  const el = document.getElementById('oc-' + outputId);
  if (el.contentEditable === 'true') {
    el.contentEditable = 'false';
    btn.innerHTML = icon('edit') + ' Sửa';
    api('PATCH', `/workflow/outputs/${outputId}`, { edited_content: el.textContent });
  } else {
    el.contentEditable = 'true';
    el.focus();
    btn.innerHTML = icon('save') + ' Lưu';
  }
}

export function copyOutput(outputId) {
  navigator.clipboard.writeText(document.getElementById('oc-' + outputId)?.textContent || '');
}

export async function saveOutputNotes(outputId, notes) {
  await api('PATCH', `/workflow/outputs/${outputId}`, { notes });
}

async function loadProjectHistory(pid) {
  const area = document.getElementById('proj-history-area');
  area.innerHTML = '<div style="color:var(--muted);font-size:12px;padding:20px;">Đang tải...</div>';
  try {
    const data = await api('GET', `/workflow/runs?project_id=${pid}&limit=50`);
    const runs = data.runs || [];
    if (!runs.length) {
      area.innerHTML = `<div class="empty-state" style="margin-top:60px;"><div class="empty-state-icon">${icon('clock')}</div><div class="empty-state-text">Chưa có lịch sử chạy nào</div></div>`;
      return;
    }
    const SC = {completed:'var(--green)',failed:'var(--red)',running:'var(--cyan)',cancelled:'var(--muted)',pending:'var(--amber)'};
    const SL = {completed:'Hoàn thành',failed:'Thất bại',running:'Đang chạy',cancelled:'Đã huỷ',pending:'Chờ xử lý'};
    area.innerHTML = runs.map(r => {
      const sc = SC[r.status]||'var(--muted)', sl = SL[r.status]||r.status;
      const time = r.started_at ? new Date(r.started_at+'Z').toLocaleString('vi-VN') : '—';
      const trigger = r.triggered_by === 'scheduled' ? icon('clock') + ' Tự động' : icon('people') + ' Thủ công';
      return `<div class="history-row">
        <span>${icon('sync')}</span>
        <span style="flex:1;font-size:13px;font-weight:500;">${esc(r.task_name||'Quy trình')}</span>
        <span style="font-size:11px;color:${sc};">${sl}</span>
        <span style="font-size:11px;color:var(--muted);">${time}</span>
        <span style="font-size:11px;color:var(--muted);">${trigger}</span>
      </div>`;
    }).join('');
  } catch {
    area.innerHTML = '<div style="color:var(--red);font-size:12px;padding:20px;">Không tải được lịch sử.</div>';
  }
}

function renderKanban(items) {
  const board = document.getElementById('kanban-board');
  if (!items) {
    board.innerHTML = `<div class="empty-state" style="width:100%;display:flex;align-items:center;justify-content:center;flex-direction:column;"><div class="empty-state-icon">${icon('document')}</div><div class="empty-state-text">${t('tasks.empty')}</div></div>`;
    return;
  }
  const cols = [
    { key: 'backlog',     label: t('col.backlog'),     color: 'var(--muted)' },
    { key: 'in_progress', label: t('col.in_progress'), color: 'var(--amber)' },
    { key: 'review',      label: t('col.review'),      color: 'var(--blue)' },
    { key: 'done',        label: t('col.done'),        color: 'var(--green)' },
  ];
  board.innerHTML = cols.map(col => {
    const colItems = items.filter(i => i.status === col.key);
    return `
      <div class="kanban-col">
        <div class="kanban-col-header">
          <span class="kanban-col-title" style="color:${col.color};">${col.label}</span>
          <span class="kanban-col-count">${colItems.length}</span>
        </div>
        <div class="kanban-cards" id="col-${col.key}">
          ${colItems.map(i => renderCard(i)).join('')}
        </div>
        <button class="kanban-add-btn" data-click="openCardModal" data-click-args='${jattr(null, col.key)}'>${t('tasks.add_item')}</button>
      </div>`;
  }).join('');
}

function renderCard(item) {
  const priClass = { low:'badge-muted', medium:'badge-blue', high:'badge-amber', critical:'badge-red' }[item.priority] || 'badge-muted';
  const assignedAgent = item.assigned_agent_id ? agentById(item.assigned_agent_id) : null;
  const agentHtml = item.agent_name
    ? `<span style="display:inline-flex;align-items:center;gap:4px;">${avatarHtml(item.agent_color || DEFAULT_AVATAR, item.agent_name, 'avatar-sm')}${agentDeptBadgeHtml(assignedAgent)}</span>`
    : '';
  const needsAssign = !item.assigned_agent_id && item.status !== 'done';
  const alertBadge = needsAssign
    ? `<span class="badge badge-amber" title="${t('tasks.unassigned_tip')}">${icon('warning')} ${t('tasks.unassigned')}</span>`
    : '';
  return `
    <div class="kanban-card${needsAssign ? ' kanban-card-unassigned' : ''}" data-click="openCardModal" data-click-args='${jattr(item.id)}'>
      <div class="kanban-card-title">${esc(item.title)}</div>
      <div class="kanban-card-meta">
        <span class="badge ${priClass}">${item.priority}</span>
        ${agentHtml}
        ${alertBadge}
      </div>
    </div>`;
}

export function openProjectModal(editId) {
  document.getElementById('project-modal-title').textContent = editId ? t('modal.project.edit') : t('modal.project.new');
  document.getElementById('project-modal-id').value = editId || '';
  if (editId) {
    const p = projects.find(x => x.id === editId);
    document.getElementById('project-modal-name').value = p?.name || '';
    document.getElementById('project-modal-desc').value = p?.description || '';
  } else {
    document.getElementById('project-modal-name').value = '';
    document.getElementById('project-modal-desc').value = '';
  }
  document.getElementById('project-modal').classList.remove('hidden');
}

export async function saveProject() {
  const id = document.getElementById('project-modal-id').value;
  const body = {
    name: document.getElementById('project-modal-name').value.trim(),
    description: document.getElementById('project-modal-desc').value.trim(),
  };
  if (!body.name) return showToast(t('js.project_required'), 'error');
  if (id) {
    await api('PATCH', `/projects/${id}`, body);
  } else {
    await api('POST', '/projects/', body);
  }
  await loadProjects();
  closeModal('project-modal');
  // Update detail header if still viewing that project
  if (id && currentProjectId == id) {
    document.getElementById('proj-detail-name').textContent = body.name;
    document.getElementById('proj-detail-desc').textContent = body.description;
  }
}

export async function deleteProject() {
  if (!currentProjectId) return;
  if (!(await showConfirm(t('js.del_project')))) return;
  await api('DELETE', `/projects/${currentProjectId}`);
  await loadProjects();
  closeProjectDetail();
}

export function renderCardAgentSelect() {
  const sel = document.getElementById('card-agent');
  sel.innerHTML = `<option value="">${t('js.unassigned')}</option>` +
    agents.map(a => `<option value="${a.id}">${esc(a.name)} — ${esc(a.role)}${agentDeptSuffix(a)}</option>`).join('');
}

export function openCardModal(itemId, defaultStatus) {
  document.getElementById('card-modal-id').value = itemId || '';
  document.getElementById('card-modal-project').value = currentProjectId || '';
  document.getElementById('card-delete-btn').style.display = itemId ? '' : 'none';
  renderCardAgentSelect();
  clearMatchSection();
  if (itemId) {
    document.getElementById('card-modal-title').textContent = 'Edit Item';
    api('GET', `/projects/${currentProjectId}/items`).then(data => {
      const item = (data.items||[]).find(i => i.id === itemId);
      if (!item) return;
      document.getElementById('card-title').value = item.title;
      document.getElementById('card-desc').value = item.description;
      document.getElementById('card-status').value = item.status;
      document.getElementById('card-priority').value = item.priority;
      document.getElementById('card-agent').value = item.assigned_agent_id || '';
      if (!item.assigned_agent_id) runMatchPreview();
    });
  } else {
    document.getElementById('card-modal-title').textContent = 'New Item';
    document.getElementById('card-title').value = '';
    document.getElementById('card-desc').value = '';
    document.getElementById('card-status').value = defaultStatus || 'backlog';
    document.getElementById('card-priority').value = 'medium';
    document.getElementById('card-agent').value = '';
  }
  document.getElementById('card-modal').classList.remove('hidden');
}

export async function saveCard() {
  const id = document.getElementById('card-modal-id').value;
  const pid = document.getElementById('card-modal-project').value;
  const body = {
    title: document.getElementById('card-title').value.trim(),
    description: document.getElementById('card-desc').value.trim(),
    status: document.getElementById('card-status').value,
    priority: document.getElementById('card-priority').value,
    assigned_agent_id: document.getElementById('card-agent').value ? parseInt(document.getElementById('card-agent').value) : null,
  };
  if (!body.title) return showToast('Title is required', 'error');
  if (id) { await api('PATCH', `/projects/items/${id}`, body); }
  else { await api('POST', `/projects/${pid}/items`, body); }
  closeModal('card-modal');
  clearMatchSection();
  await loadProject();
}

export async function deleteCard() {
  const id = document.getElementById('card-modal-id').value;
  if (!id) return;
  if (!(await showConfirm('Delete this item?'))) return;
  await api('DELETE', `/projects/items/${id}`);
  closeModal('card-modal');
  clearMatchSection();
  await loadProject();
}

// ── Smart Matching ──────────────────────
let _matchDebounce = null;

function clearMatchSection() {
  document.getElementById('card-match-section').style.display = 'none';
  document.getElementById('card-match-list').innerHTML = '';
}

export function runMatchPreview() {
  clearTimeout(_matchDebounce);
  _matchDebounce = setTimeout(async () => {
    const title = document.getElementById('card-title').value.trim();
    const desc  = document.getElementById('card-desc').value.trim();
    if (!title && !desc) { clearMatchSection(); return; }
    try {
      const result = await api('POST', '/projects/items/match', { title, description: desc });
      renderMatchSection(result);
    } catch (_) { clearMatchSection(); }
  }, 350);
}

function renderMatchSection(result) {
  const section = document.getElementById('card-match-section');
  const list    = document.getElementById('card-match-list');
  const suggestions = result?.suggestions || [];
  if (!suggestions.length) { clearMatchSection(); return; }
  list.innerHTML = suggestions.map(c => `
    <div class="match-candidate">
      ${avatarHtml(c.agent_avatar || DEFAULT_AVATAR, c.agent_name, 'avatar-sm')}
      <div class="match-candidate-info">
        <div class="match-candidate-name">${esc(c.agent_name)} <span style="color:var(--muted);font-size:11px;">— ${esc(c.agent_role)}${agentDeptSuffix(agentById(c.agent_id))}</span></div>
        <div class="match-candidate-reason">${esc(c.reason)}</div>
      </div>
      <div style="text-align:right;">
        <div class="match-score-bar"><div class="match-score-fill" style="width:${c.score}%;"></div></div>
        <div class="match-score-text">${Math.round(c.score)}</div>
      </div>
      <button class="btn btn-primary btn-sm" data-click="assignFromSuggestion" data-click-args='${jattr(c.agent_id, c.agent_name)}' title="${t('tasks.assign_now')}">
        ${t('tasks.assign_now')}
      </button>
    </div>`).join('');
  section.style.display = '';
}

export function assignFromSuggestion(agentId, agentName) {
  const sel = document.getElementById('card-agent');
  sel.value = agentId;
  if (!sel.value) {
    // agent not in list yet — add it
    const opt = document.createElement('option');
    opt.value = agentId; opt.textContent = agentName;
    sel.appendChild(opt);
    sel.value = agentId;
  }
  clearMatchSection();
}

function updateAlertBanner(count) {
  const banner = document.getElementById('alert-banner');
  const text   = document.getElementById('alert-banner-text');
  if (count > 0) {
    text.textContent = t('tasks.alert_banner', count);
    banner.style.display = 'flex';
  } else {
    banner.style.display = 'none';
  }
}

async function openAlertModal() {
  const data = await api('GET', '/projects/items/alerts').catch(() => ({ alerts: [] }));
  const alerts = data.alerts || [];
  const body = document.getElementById('alert-modal-body');
  if (!alerts.length) {
    body.innerHTML = `<div style="color:var(--muted);font-size:13px;text-align:center;padding:20px 0;">${t('tasks.no_alerts')}</div>`;
  } else {
    body.innerHTML = alerts.map(a => {
      let suggestions = [];
      try { suggestions = JSON.parse(a.suggestions_json || '[]'); } catch(_) {}
      return `
        <div style="background:var(--bg3);border:1px solid var(--border);border-radius: 0;padding:12px 14px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
            <div>
              <span style="font-size:13px;font-weight:600;">${esc(a.title)}</span>
              <span class="badge badge-muted" style="margin-left:8px;">${esc(a.project_name)}</span>
            </div>
            <span class="badge badge-amber">${icon('warning')} ${t('tasks.unassigned')}</span>
          </div>
          ${suggestions.length ? `<div style="font-size:11px;color:var(--muted);margin-bottom:6px;">${t('tasks.suggestions_hint')}</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;">
            ${suggestions.slice(0,3).map(s => `<span class="badge badge-blue" style="font-size:11px;">${esc(s.agent_name)} (${Math.round(s.score)})</span>`).join('')}
          </div>` : `<div style="font-size:11px;color:var(--muted);">${t('tasks.no_suggestions')}</div>`}
        </div>`;
    }).join('');
  }
  document.getElementById('alert-modal').classList.remove('hidden');
}

// ════════════════════════════════════════
