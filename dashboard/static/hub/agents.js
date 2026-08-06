import { api } from './api.js';
import { AVATAR_ICON_LABEL, AVATAR_PALETTE_LABEL, DEFAULT_AVATAR, avatarHtml, avatarInfo } from './avatar.js';
import { icon } from './icons.js';
import { agentModelIds, initAvatarPicker, setAgentModelIds } from './init.js';
import { renderCardAgentSelect } from './knowledge.js';
import { showConfirm, showToast } from './modals.js';
import { modelPool } from './model-pool.js';
import { skills } from './skills.js';
import { t } from './ui.js';
import { esc } from './utils.js';

// State của tab Nhân viên. Các module khác đọc `agents` qua live binding
// của ES module; chỉ file này được gán lại.
export let agents = [];
let departments = [];
let selectedAgentId = null;
let selectedDeptFilter = null;

// AGENTS
// ════════════════════════════════════════
export async function loadAgents() {
  const data = await api('GET', '/agent-configs/');
  agents = data.agents || [];
  renderAgentList();
  document.getElementById('agents-count').textContent = t('count.agents', agents.length);
  renderAgentSkillsSelect();
  renderCardAgentSelect();
  renderDepartmentFilter();
}

// ── Phòng ban (Department) helpers — dùng chung ở mọi nơi hiển thị tên nhân viên ──

export function agentDeptBadgeHtml(a) {
  if (!a || !a.department_name) return '';
  const c = a.department_color || '#7C6BAE';
  return `<span class="badge" style="background:${c}22;color:${c};font-size:10px;font-weight:600;">${esc(a.department_name)}</span>`;
}

export function agentDeptSuffix(a) {
  return (a && a.department_name) ? ` · ${a.department_name}` : '';
}

export function agentById(id) {
  return agents.find(x => x.id === id);
}

export async function loadDepartments() {
  const data = await api('GET', '/departments/');
  departments = data.departments || [];
  renderDepartmentSelect();
  renderDepartmentModalList();
  renderDepartmentFilter();
}

function renderDepartmentFilter() {
  const el = document.getElementById('agent-dept-filter');
  if (!el) return;
  if (!departments.length) { el.innerHTML = ''; return; }
  const chip = (label, active, onclick, color) => `
    <div onclick="${onclick}" class="badge ${active ? '' : 'badge-muted'}"
         style="cursor:pointer;${active ? `background:${color}22;color:${color};` : ''}">${esc(label)}</div>`;
  const all = chip(`Tất cả (${agents.length})`, selectedDeptFilter === null, 'filterByDepartment(null)', '#7C6BAE');
  const rest = departments.map(d => {
    const count = agents.filter(a => a.department_id === d.id).length;
    return chip(`${d.name} (${count})`, selectedDeptFilter === d.id, `filterByDepartment(${d.id})`, d.color);
  }).join('');
  el.innerHTML = all + rest;
}

function filterByDepartment(deptId) {
  selectedDeptFilter = deptId;
  renderDepartmentFilter();
  renderAgentList();
}

function renderDepartmentSelect() {
  const el = document.getElementById('agent-department');
  if (!el) return;
  const current = el.value;
  el.innerHTML = '<option value="">— Chưa gán phòng ban —</option>' +
    departments.map(d => `<option value="${d.id}">${esc(d.name)}</option>`).join('');
  el.value = current;
}

export function checkDeptHeadPrompt() {
  const prompt = document.getElementById('agent-set-head-prompt');
  const checkbox = document.getElementById('agent-set-head-checkbox');
  const deptId = document.getElementById('agent-department').value;
  const dept = deptId ? departments.find(d => d.id === parseInt(deptId)) : null;
  if (dept && !dept.head_agent_id) {
    document.getElementById('agent-set-head-text').textContent = `Đặt làm Trưởng phòng ${dept.name}?`;
    prompt.style.display = 'flex';
  } else {
    checkbox.checked = false;
    prompt.style.display = 'none';
  }
}

export function renderAgentList() {
  const el = document.getElementById('agents-list');
  const query = (document.getElementById('agent-search')?.value || '').trim().toLocaleLowerCase('vi');
  const byDepartment = selectedDeptFilter === null ? agents : agents.filter(a => a.department_id === selectedDeptFilter);
  const list = byDepartment.filter(a => !query || `${a.name || ''} ${a.role || ''}`.toLocaleLowerCase('vi').includes(query));
  if (!list.length) {
    const message = agents.length
      ? 'Không tìm thấy nhân viên phù hợp — thử một từ khoá hoặc phòng ban khác.'
      : 'Chưa có nhân viên AI nào — tạo nhân viên đầu tiên của bạn.';
    el.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state-icon">${icon('bot')}</div><div class="empty-state-text">${message}</div></div>`;
    return;
  }
  el.innerHTML = list.map(a => `
    <div class="agent-card" onclick="selectAgent(${a.id})">
      ${avatarHtml(a.avatar_color, a.name, 'avatar-lg', a.avatar_icon || 'bot')}
      <div class="agent-card-name">${esc(a.name)}</div>
      <div class="agent-card-role">${esc(a.role || 'Assistant')}</div>
      <div class="agent-card-badges">${agentDeptBadgeHtml(a)}</div>
      <div class="agent-card-meta">
        <span>${(a.skills || []).length} kỹ năng · ${(a.model_pool_ids || (a.model_pool_id ? [a.model_pool_id] : [])).length} model</span>
        <span class="status-dot-label"><i class="sdot ${a.enabled === false || a.enabled === 0 ? 'idle' : 'on'}"></i>${a.enabled === false || a.enabled === 0 ? 'Tắt' : 'Bật'}</span>
      </div>
    </div>`).join('');
}

// ── Quản lý phòng ban (modal) ──

export function openDepartmentModal() {
  resetDepartmentForm();
  renderDepartmentModalList();
  document.getElementById('department-modal').classList.remove('hidden');
}

function renderDepartmentHeadSelect(selectedId) {
  const el = document.getElementById('department-head');
  el.innerHTML = '<option value="">— Chưa có trưởng phòng —</option>' +
    agents.map(a => `<option value="${a.id}">${esc(a.name)} — ${esc(a.role)}</option>`).join('');
  el.value = selectedId || '';
}

function renderDepartmentModalList() {
  const el = document.getElementById('department-list');
  if (!el) return;
  if (!departments.length) {
    el.innerHTML = '<div style="font-size:12px;color:var(--muted);">Chưa có phòng ban nào.</div>';
    return;
  }
  el.innerHTML = departments.map(d => {
    const count = agents.filter(a => a.department_id === d.id).length;
    const headTxt = d.head_agent_name ? ` · Trưởng phòng: ${esc(d.head_agent_name)}` : '';
    return `
    <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:var(--radius-sm);box-shadow:var(--shadow);background:var(--bg-card);">
      <div style="width:10px;height:10px;border-radius:50%;background:${d.color};flex-shrink:0;"></div>
      <div style="flex:1;min-width:0;">
        <div style="font-size:13px;font-weight:600;">${esc(d.name)}</div>
        <div style="font-size:11px;color:var(--muted);">${count} nhân viên${headTxt}${d.description ? ' · ' + esc(d.description) : ''}</div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="editDepartment(${d.id})">Sửa</button>
      <button class="btn btn-danger btn-sm" onclick="deleteDepartmentConfirm(${d.id})">Xoá</button>
    </div>`;
  }).join('');
}

function hslToHex(h, s, l) {
  h = ((Number(h) % 360) + 360) % 360;
  s = Math.max(0, Math.min(100, Number(s))) / 100;
  l = Math.max(0, Math.min(100, Number(l))) / 100;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs((h / 60) % 2 - 1));
  const m = l - c / 2;
  let r = 0, g = 0, b = 0;
  if (h < 60) [r, g] = [c, x];
  else if (h < 120) [r, g] = [x, c];
  else if (h < 180) [g, b] = [c, x];
  else if (h < 240) [g, b] = [x, c];
  else if (h < 300) [r, b] = [x, c];
  else [r, b] = [c, x];
  return '#' + [r, g, b]
    .map(v => Math.round((v + m) * 255).toString(16).padStart(2, '0'))
    .join('')
    .toUpperCase();
}

function hexToHsl(hex) {
  const match = /^#([0-9a-fA-F]{6})$/.exec(hex);
  if (!match) return null;
  const value = parseInt(match[1], 16);
  const r = ((value >> 16) & 255) / 255;
  const g = ((value >> 8) & 255) / 255;
  const b = (value & 255) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  let h = 0;
  if (delta) {
    if (max === r) h = 60 * (((g - b) / delta) % 6);
    else if (max === g) h = 60 * ((b - r) / delta + 2);
    else h = 60 * ((r - g) / delta + 4);
  }
  if (h < 0) h += 360;
  const l = (max + min) / 2;
  const s = delta === 0 ? 0 : delta / (1 - Math.abs(2 * l - 1));
  return { h: Math.round(h), s: Math.round(s * 100), l: Math.round(l * 100) };
}

function setDepartmentColor(hex) {
  const normalized = /^#([0-9a-fA-F]{6})$/.test(hex) ? hex.toUpperCase() : '#7C6BAE';
  const hsl = hexToHsl(normalized);
  document.getElementById('department-color').value = normalized;
  document.getElementById('department-color-hex').value = normalized;
  document.getElementById('department-color-hex').classList.remove('invalid');
  document.getElementById('department-color-preview').style.background = normalized;
  document.getElementById('department-color-hue').value = hsl.h;
}

document.getElementById('department-color-hue').addEventListener('input', event => {
  setDepartmentColor(hslToHex(event.target.value, 52, 50));
});

document.getElementById('department-color-hex').addEventListener('input', event => {
  const input = event.target;
  if (!/^#([0-9a-fA-F]{6})$/.test(input.value)) {
    input.classList.add('invalid');
    return;
  }
  setDepartmentColor(input.value);
});

export function editDepartment(id) {
  const d = departments.find(x => x.id === id);
  if (!d) return;
  document.getElementById('department-edit-id').value = d.id;
  document.getElementById('department-name').value = d.name;
  document.getElementById('department-description').value = d.description || '';
  setDepartmentColor(d.color || '#7C6BAE');
  renderDepartmentHeadSelect(d.head_agent_id);
  document.getElementById('department-form-title').textContent = `Sửa phòng ban: ${d.name}`;
  document.getElementById('department-cancel-edit-btn').style.display = '';
}

export function resetDepartmentForm() {
  document.getElementById('department-edit-id').value = '';
  document.getElementById('department-name').value = '';
  document.getElementById('department-description').value = '';
  setDepartmentColor('#7C6BAE');
  renderDepartmentHeadSelect(null);
  document.getElementById('department-form-title').textContent = 'Thêm phòng ban mới';
  document.getElementById('department-cancel-edit-btn').style.display = 'none';
}

export async function saveDepartment() {
  const id = document.getElementById('department-edit-id').value;
  const name = document.getElementById('department-name').value.trim();
  if (!name) return showToast('Tên phòng ban là bắt buộc', 'error');
  const colorHexEl = document.getElementById('department-color-hex');
  if (!/^#([0-9a-fA-F]{6})$/.test(colorHexEl.value)) {
    colorHexEl.classList.add('invalid');
    return showToast('Mã màu phải có dạng #RRGGBB', 'error');
  }
  setDepartmentColor(colorHexEl.value);
  const headVal = document.getElementById('department-head').value;
  const body = {
    name,
    description: document.getElementById('department-description').value.trim(),
    color: document.getElementById('department-color').value,
    head_agent_id: headVal ? parseInt(headVal) : null,
  };
  try {
    if (id) {
      await api('PATCH', `/departments/${id}`, body);
    } else {
      await api('POST', '/departments/', body);
    }
    if (body.head_agent_id) await ensureHeadSkillOnAgent(body.head_agent_id);
    await loadDepartments();
    await loadAgents();
    resetDepartmentForm();
    showToast('Đã lưu phòng ban.', 'success');
  } catch (e) { showToast('Error: ' + e.message, 'error'); }
}

export async function deleteDepartmentConfirm(id) {
  const d = departments.find(x => x.id === id);
  const count = agents.filter(a => a.department_id === id).length;
  const msg = count
    ? `Xoá phòng ban "${d?.name}"? ${count} nhân viên sẽ về trạng thái chưa gán phòng ban.`
    : `Xoá phòng ban "${d?.name}"?`;
  if (!(await showConfirm(msg))) return;
  await api('DELETE', `/departments/${id}`);
  if (selectedDeptFilter === id) selectedDeptFilter = null;
  await loadDepartments();
  await loadAgents();
}

export function renderAgentSkillsSelect(selectedIds) {
  const el = document.getElementById('agent-skills-select');
  if (!skills.length) { el.innerHTML = '<span style="font-size:12px;color:var(--muted);">No skills available</span>'; return; }
  const current = selectedIds !== undefined ? selectedIds : getSelectedAgentSkills();
  el.innerHTML = skills.map(s => `
    <div onclick="toggleAgentSkill(${s.id}, this)" data-skill-id="${s.id}"
         class="badge ${current.includes(s.id)?'badge-cyan':'badge-muted'}" style="cursor:pointer;">
      ${esc(s.name)}
    </div>`).join('');
}

function getSelectedAgentSkills() {
  return [...document.querySelectorAll('#agent-skills-select [data-skill-id].badge-cyan')]
    .map(el => parseInt(el.dataset.skillId));
}

// Nhân viên được đặt làm Trưởng phòng mặc định phải có skill quản lý phòng ban
// (xem skills/truong_phong_quan_ly.md) để biết cách dùng dữ liệu nhân sự/công việc
// thực tế được hệ thống chèn sẵn thay vì trả lời chung chung như 1 nhân viên thường.
const HEAD_SKILL_NAME = 'truong_phong_quan_ly';

function withHeadSkill(skillIds) {
  const headSkill = skills.find(s => s.name === HEAD_SKILL_NAME);
  if (!headSkill || skillIds.includes(headSkill.id)) return skillIds;
  return [...skillIds, headSkill.id];
}

async function ensureHeadSkillOnAgent(agentId) {
  const headSkill = skills.find(s => s.name === HEAD_SKILL_NAME);
  if (!headSkill) return;
  const agent = agents.find(a => a.id === agentId) || await api('GET', `/agent-configs/${agentId}`).catch(() => null);
  if (!agent) return;
  const currentSkills = agent.skills || [];
  if (currentSkills.includes(headSkill.id)) return;
  await api('PATCH', `/agent-configs/${agentId}`, { skills: [...currentSkills, headSkill.id] });
}

export function toggleAgentSkill(id, el) {
  el.classList.toggle('badge-cyan');
  el.classList.toggle('badge-muted');
}

let agentWizardStep = 1;
let agentWizardMaxStep = 1;

function renderAgentReview() {
  const el = document.getElementById('agent-review-summary');
  if (!el) return;
  const deptId = parseInt(document.getElementById('agent-department').value || '0');
  const dept = departments.find(d => d.id === deptId);
  const selectedSkills = getSelectedAgentSkills().map(id => skills.find(s => s.id === id)?.name).filter(Boolean);
  const selectedModels = agentModelIds.map(id => modelPool.find(m => m.id === id)?.name || `Model #${id}`);
  const prompt = document.getElementById('agent-system-prompt').value.trim();
  const avatarIcon = document.querySelector('.avatar-shape-opt.selected')?.dataset.avatarIcon || 'bot';
  const avatarColor = document.querySelector('.avatar-opt.selected')?.dataset.icon || DEFAULT_AVATAR;
  const item = (label, value) => `<div class="agent-review-item"><div class="agent-review-label">${esc(label)}</div><div class="agent-review-value">${esc(value || 'Chưa thiết lập')}</div></div>`;
  el.innerHTML = [
    item('Tên nhân viên', document.getElementById('agent-name').value.trim()),
    item('Vai trò', document.getElementById('agent-role').value.trim() || 'Assistant'),
    item('Phòng ban', dept?.name || 'Chưa gán phòng ban'),
    item('Ảnh đại diện', `${AVATAR_ICON_LABEL[avatarIcon] || 'Robot'} · ${AVATAR_PALETTE_LABEL[avatarColor] || avatarColor}`),
    item('Model ưu tiên', selectedModels.join(', ') || 'Dùng model mặc định'),
    item('Kỹ năng', selectedSkills.join(', ') || 'Chưa chọn kỹ năng'),
    item('System Prompt', prompt || 'Chưa thiết lập'),
  ].join('');
}

export function goAgentWizardStep(step, force = false) {
  step = Math.max(1, Math.min(5, step));
  const editing = Boolean(document.getElementById('agent-id').value);
  if (!force && !editing && step > agentWizardMaxStep + 1) return;
  if (step > 1 && !document.getElementById('agent-name').value.trim()) {
    showToast('Vui lòng nhập tên nhân viên AI trước khi tiếp tục.', 'error');
    document.getElementById('agent-name').focus();
    return;
  }
  agentWizardStep = step;
  agentWizardMaxStep = Math.max(agentWizardMaxStep, step);
  document.querySelectorAll('.agent-wizard-step').forEach(el => el.classList.toggle('active', Number(el.dataset.agentStep) === step));
  const stepIcons = ['bot', 'sliders', 'document', 'bolt', 'check'];
  document.querySelectorAll('.agent-wizard-tab').forEach((el, index) => {
    const isDone = index + 1 < step;
    el.classList.toggle('active', index + 1 === step);
    el.classList.toggle('done', isDone);
    const circle = el.querySelector('span');
    if (circle) circle.innerHTML = isDone && index + 1 !== step ? icon('check') : icon(stepIcons[index]);
  });
  document.getElementById('agent-wizard-back').style.visibility = step === 1 ? 'hidden' : 'visible';
  document.getElementById('agent-wizard-next').style.display = step === 5 ? 'none' : '';
  document.getElementById('agent-wizard-save').style.display = step === 5 ? '' : 'none';
  if (step === 5) renderAgentReview();
}

export function changeAgentWizardStep(direction) {
  goAgentWizardStep(agentWizardStep + direction);
}

function openAgentWizard(editing) {
  agentWizardMaxStep = editing ? 5 : 1;
  document.getElementById('agent-wizard-layer').style.display = 'flex';
  document.getElementById('agent-form-container').style.display = 'flex';
  goAgentWizardStep(1, true);
}

export function selectAgent(id) {
  selectedAgentId = id;
  renderAgentList();
  const a = agents.find(x => x.id === id);
  if (!a) return;
  document.getElementById('agent-form-title').textContent = a.name;
  document.getElementById('agent-delete-btn').style.display = '';
  document.getElementById('agent-id').value = a.id;
  document.getElementById('agent-name').value = a.name;
  document.getElementById('agent-role').value = a.role;
  document.getElementById('agent-department').value = a.department_id || '';
  checkDeptHeadPrompt();
  setAgentModelIds(a.model_pool_ids || (a.model_pool_id ? [a.model_pool_id] : []));
  document.getElementById('agent-system-prompt').value = a.system_prompt;
  initAvatarPicker(a.avatar_icon || 'bot', a.avatar_color);
  renderAgentSkillsSelect(a.skills || []);
  updateAgentPreview();
  openAgentWizard(true);
}

export function newAgent() {
  selectedAgentId = null;
  renderAgentList();
  document.getElementById('agent-form-title').textContent = t('js.new_agent');
  document.getElementById('agent-delete-btn').style.display = 'none';
  document.getElementById('agent-id').value = '';
  document.getElementById('agent-name').value = '';
  document.getElementById('agent-role').value = '';
  document.getElementById('agent-department').value = '';
  checkDeptHeadPrompt();
  setAgentModelIds([]);
  document.getElementById('agent-system-prompt').value = '';
  initAvatarPicker('bot', DEFAULT_AVATAR);
  renderAgentSkillsSelect([]);
  updateAgentPreview();
  document.getElementById('agent-set-head-checkbox').checked = false;
  openAgentWizard(false);
}

export function cancelAgentForm() {
  selectedAgentId = null;
  document.getElementById('agent-form-container').style.display = 'none';
  document.getElementById('agent-wizard-layer').style.display = 'none';
  renderAgentList();
}

export function updateAgentPreview() {
  const name = document.getElementById('agent-name').value || 'A';
  const role = document.getElementById('agent-role').value || 'Assistant';
  const avatarKey = document.querySelector('.avatar-opt.selected')?.dataset.icon || DEFAULT_AVATAR;
  const avatarIcon = document.querySelector('.avatar-shape-opt.selected')?.dataset.avatarIcon || 'bot';
  const previewEl = document.getElementById('agent-preview-avatar');
  const {content, style} = avatarInfo(avatarKey, name, avatarIcon);
  previewEl.innerHTML = content;
  previewEl.style.cssText = style;
  document.getElementById('agent-preview-name').textContent = name;
  document.getElementById('agent-preview-role').textContent = role;
}

export async function saveAgent() {
  const id = document.getElementById('agent-id').value;
  const body = {
    name: document.getElementById('agent-name').value.trim(),
    role: document.getElementById('agent-role').value.trim() || 'Assistant',
    model_pool_ids: [...agentModelIds],
    system_prompt: document.getElementById('agent-system-prompt').value,
    avatar_color: document.querySelector('.avatar-opt.selected')?.dataset.icon || DEFAULT_AVATAR,
    avatar_icon: document.querySelector('.avatar-shape-opt.selected')?.dataset.avatarIcon || 'bot',
    skills: getSelectedAgentSkills(),
    department_id: document.getElementById('agent-department').value ? parseInt(document.getElementById('agent-department').value) : null,
  };
  if (!body.name) return showToast('Name is required', 'error');
  const setAsHead = document.getElementById('agent-set-head-checkbox').checked && body.department_id;
  if (setAsHead) body.skills = withHeadSkill(body.skills);
  try {
    let savedId = id ? parseInt(id) : null;
    if (id) {
      await api('PATCH', `/agent-configs/${id}`, body);
    } else {
      const created = await api('POST', '/agent-configs/', body);
      savedId = created.id;
    }
    if (setAsHead) {
      await api('PATCH', `/departments/${body.department_id}`, { head_agent_id: savedId });
      await loadDepartments();
    }
    await loadAgents();
    cancelAgentForm();
    showToast('Đã lưu thay đổi.', 'success');
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

export async function deleteAgent() {
  const id = document.getElementById('agent-id').value;
  if (!id) return;
  if (!(await showConfirm('Delete this agent?'))) return;
  await api('DELETE', `/agent-configs/${id}`);
  await loadAgents();
  cancelAgentForm();
}

// ════════════════════════════════════════
