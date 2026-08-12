import { renderAgentSkillsSelect } from './agents.js';
import { api } from './api.js';
import { icon } from './icons.js';
import { showConfirm, showToast } from './modals.js';
import { t } from './ui.js';
import { esc, jattr } from './utils.js';

// State của tab Kỹ năng — chỉ file này gán lại.
export let skills = [];
let selectedSkillId = null;
let selectedSkillTypeFilter = null;

// SKILLS
// ════════════════════════════════════════
// skill_id -> { connected, error, tools: [...] }. Nạp rời khỏi loadSkills vì lần
// đầu phải khởi chạy MCP server thật (vài giây), không để nó chặn hiển thị tab.
let mcpStatusBySkill = {};

export async function loadSkills() {
  const [data] = await Promise.all([
    api('GET', '/skills/'),
    loadBuiltinTools(),
  ]);
  skills = data.skills || [];
  renderSkillList();
  document.getElementById('skills-count').textContent = t('count.skills', skills.length);
  if (skills.some(s => s.type === 'mcp')) refreshMcpStatus();
}

async function refreshMcpStatus() {
  try {
    const data = await api('GET', '/tools/mcp/status');
    mcpStatusBySkill = Object.fromEntries((data.servers || []).map(s => [s.skill_id, s]));
  } catch (error) {
    console.warn('Không lấy được trạng thái MCP server:', error);
    mcpStatusBySkill = {};
  }
  renderSkillList();
}

const SKILL_TYPE_LABELS = {
  builtin: 'Có sẵn', api: 'API', mcp: 'MCP', custom: 'Custom',
};
let availableBuiltinTools = [];
let skillWizardStep = 1;
let skillWizardMaxStep = 1;

async function loadBuiltinTools(selectedName = '') {
  try {
    const data = await api('GET', '/tools/');
    availableBuiltinTools = data.tools || [];
  } catch (error) {
    console.warn('Không thể tải danh sách công cụ hệ thống:', error);
    availableBuiltinTools = [];
  }
  renderBuiltinToolOptions(selectedName || document.getElementById('skill-builtin-tool')?.value || '');
}

function renderBuiltinToolOptions(selectedName = '') {
  const el = document.getElementById('skill-builtin-tool');
  if (!el) return;
  const known = availableBuiltinTools.some(tool => tool.name === selectedName);
  el.innerHTML = '<option value="">— Chọn công cụ —</option>' +
    (!known && selectedName ? `<option value="${esc(selectedName)}">${esc(selectedName)} (không còn đăng ký)</option>` : '') +
    availableBuiltinTools.map(tool => `<option value="${esc(tool.name)}">${esc(tool.name)} — ${esc(tool.description || '')}</option>`).join('');
  el.value = selectedName;
  updateBuiltinToolDescription();
}

export function updateBuiltinToolDescription() {
  const name = document.getElementById('skill-builtin-tool')?.value || '';
  const tool = availableBuiltinTools.find(item => item.name === name);
  const description = document.getElementById('skill-builtin-tool-description');
  if (description) description.textContent = tool?.description || (name ? 'Công cụ này hiện không có trong registry.' : '');
}

export function filterSkillsByType(type) {
  selectedSkillTypeFilter = type || null;
  renderSkillList();
}

export function renderSkillList() {
  const el = document.getElementById('skills-list');
  const q = (document.getElementById('skill-search')?.value || '').trim().toLowerCase();
  const list = skills.filter(s =>
    (!selectedSkillTypeFilter || s.type === selectedSkillTypeFilter) &&
    (!q || (s.name || '').toLowerCase().includes(q) || (s.description || '').toLowerCase().includes(q))
  );
  const filter = document.getElementById('skill-type-filter');
  const chip = (type, label) => {
    const active = selectedSkillTypeFilter === type;
    const count = type ? skills.filter(s => s.type === type).length : skills.length;
    return `<span class="badge ${active ? (type ? `skill-type-${type}` : 'badge-green') : 'badge-muted'}" data-click="filterSkillsByType" data-click-args='${jattr(type ?? null)}'>${label} (${count})</span>`;
  };
  filter.innerHTML = chip(null, 'Tất cả') + Object.entries(SKILL_TYPE_LABELS).map(([type, label]) => chip(type, label)).join('');
  if (!list.length) {
    el.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state-icon">${icon('bolt')}</div><div class="empty-state-text">${skills.length ? 'Không tìm thấy kỹ năng phù hợp.' : 'Chưa có kỹ năng nào — tạo kỹ năng đầu tiên của bạn.'}</div></div>`;
    return;
  }
  el.innerHTML = list.map(s => s.type === 'mcp' ? mcpSkillCard(s) : plainSkillCard(s)).join('');
}

function skillEnabledMeta(s) {
  const off = s.enabled === false || s.enabled === 0;
  return `<span class="status-dot-label"><i class="sdot ${off ? 'idle' : 'on'}"></i>${off ? 'Tắt' : 'Bật'}</span>`;
}

function plainSkillCard(s) {
  return `
    <div class="skill-card" data-click="selectSkill" data-click-args='${jattr(s.id)}'>
      <div class="skill-card-icon skill-type-${s.type}">${icon('bolt')}</div>
      <div class="skill-card-name">${esc(s.name)}</div>
      <div class="skill-card-description">${esc(s.description || 'Chưa có mô tả')}</div>
      <div class="skill-card-badges"><span class="skill-type-badge skill-type-${s.type}">${esc(SKILL_TYPE_LABELS[s.type] || s.type)}</span></div>
      <div class="skill-card-meta"><span>Cấu hình kết nối</span>${skillEnabledMeta(s)}</div>
    </div>`;
}

// Một MCP server phơi ra nhiều tool, nên card của nó là một khối chứa danh sách
// tool chứ không phải một ô đơn như các loại skill khác.
function mcpSkillCard(s) {
  const status = mcpStatusBySkill[s.id];
  const prefix = status?.prefix || '';
  const tools = (status?.tools || []).map(n => prefix && n.startsWith(prefix) ? n.slice(prefix.length) : n);

  let body;
  if (!status) {
    body = `<span class="skill-mcp-empty">Đang kiểm tra kết nối...</span>`;
  } else if (!status.connected) {
    body = `<span class="skill-mcp-empty">Không kết nối được${status.error ? ' — ' + esc(status.error) : ''}</span>`;
  } else if (!tools.length) {
    body = `<span class="skill-mcp-empty">Server không phơi ra tool nào.</span>`;
  } else {
    body = tools.map(n => `<span class="skill-mcp-tool-chip">${esc(n)}</span>`).join('');
  }

  const total = (status?.available || []).length;
  const count = status?.connected
    ? (total && total !== tools.length ? `đang bật ${tools.length}/${total} tool` : `${tools.length} tool`)
    : 'Chưa kết nối';
  return `
    <div class="skill-card skill-card-mcp" data-click="selectSkill" data-click-args='${jattr(s.id)}'>
      <div class="skill-mcp-head">
        <div class="skill-card-icon skill-type-mcp">${icon('bolt')}</div>
        <div class="skill-mcp-headings">
          <div class="skill-card-name">${esc(s.name)}</div>
          <div class="skill-card-description">${esc(s.description || 'Chưa có mô tả')}</div>
          <div class="skill-card-badges" style="justify-content:flex-start;"><span class="skill-type-badge skill-type-mcp">${esc(SKILL_TYPE_LABELS.mcp)}</span></div>
        </div>
      </div>
      <div class="skill-mcp-toollist">${body}</div>
      <div class="skill-card-meta"><span>${esc(count)}</span>${skillEnabledMeta(s)}</div>
    </div>`;
}

function _clearSkillFilePreview() {
  document.getElementById('skill-file-input').value = '';
  document.getElementById('skill-file-preview').style.display = 'none';
  document.getElementById('skill-upload-zone').style.display = '';
}

function resetSkillConfigFields() {
  ['skill-builtin-tool','skill-api-endpoint','skill-api-key','skill-mcp-target','skill-mcp-token','skill-builtin-legacy','skill-mcp-legacy'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('skill-api-method').value = 'GET';
  document.getElementById('skill-mcp-transport').value = 'stdio';
  document.getElementById('skill-api-extra').value = '{}';
  document.getElementById('skill-config').value = '{}';
  document.getElementById('skill-image-pool-wrap').style.display = 'none';
  document.getElementById('skill-builtin-legacy-wrap').style.display = 'none';
  document.getElementById('skill-mcp-legacy-wrap').style.display = 'none';
  updateBuiltinToolDescription();
}

export function updateSkillImagePoolField() {
  const isImageSkill =
    document.getElementById('skill-type').value === 'custom' &&
    document.getElementById('skill-name').value.trim() === 'generate_post_image';
  document.getElementById('skill-image-pool-wrap').style.display = isImageSkill ? '' : 'none';
}

export function chooseSkillType(type) {
  if (!Object.hasOwn(SKILL_TYPE_LABELS, type)) return;
  document.getElementById('skill-type').value = type;
  document.querySelectorAll('.skill-type-option').forEach(el => el.classList.toggle('selected', el.dataset.skillType === type));
  document.querySelectorAll('.skill-config-panel').forEach(el => el.classList.toggle('active', el.dataset.configType === type));
  document.getElementById('skill-type-required').style.display = 'none';
  // Chỉ 'api' và 'mcp' mới có kết nối ra ngoài để mà thử.
  document.getElementById('skill-conn-test').style.display = (type === 'api' || type === 'mcp') ? '' : 'none';
  clearSkillConnResult();
  updateSkillImagePoolField();
}

function clearSkillConnResult() {
  const box = document.getElementById('skill-conn-result');
  if (box) { box.innerHTML = ''; box.className = 'skill-conn-result'; }
}

export async function testSkillConnection() {
  const type = document.getElementById('skill-type').value;
  if (type !== 'api' && type !== 'mcp') return;
  const config = buildSkillConfig(type);
  if (config === null) return;

  const btn = document.getElementById('skill-conn-btn');
  const box = document.getElementById('skill-conn-result');
  btn.disabled = true;
  btn.textContent = 'Đang thử...';
  box.className = 'skill-conn-result pending';
  box.innerHTML = type === 'mcp'
    ? 'Đang khởi chạy MCP server — lần đầu có thể mất vài giây nếu server phải nạp model.'
    : 'Đang gọi thử endpoint...';

  try {
    // Gửi kèm id skill đang sửa: ô secret hiển thị dạng mặt nạ, backend tra lại
    // giá trị thật từ DB thì mới test được kết nối của skill đã lưu.
    const editingId = parseInt(document.getElementById('skill-id').value, 10);
    const payload = { type, config };
    if (Number.isInteger(editingId)) payload.skill_id = editingId;
    const r = await api('POST', '/skills/test-connection', payload);
    box.className = 'skill-conn-result ' + (r.ok ? 'ok' : 'fail');
    box.innerHTML = r.ok ? renderConnOk(type, r) : renderConnFail(r);
  } catch (error) {
    box.className = 'skill-conn-result fail';
    box.innerHTML = `<div class="skill-conn-title">Không gọi được API kiểm tra</div><div class="skill-conn-detail">${esc(String(error))}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Kiểm tra kết nối';
  }
}

function renderConnOk(type, r) {
  const ms = r.elapsed_ms != null ? ` · ${r.elapsed_ms}ms` : '';
  if (type === 'mcp') {
    const tools = r.tools || [];
    const head = `<div class="skill-conn-title">Kết nối được${ms} — server phơi ra ${tools.length} tool</div>`;
    if (!tools.length) {
      return head + `<div class="skill-conn-detail">Server không khai báo tool nào. Kiểm tra lại lệnh khởi chạy.</div>`;
    }
    // Chưa từng chọn -> mặc định bật hết, giữ nguyên hành vi cũ cho skill đã có.
    if (!Array.isArray(skillMcpSelectedTools)) skillMcpSelectedTools = tools.map(t => t.name);
    mcpAvailableTools = tools.map(t => t.name);
    return head
      + `<div class="skill-conn-detail">Chọn những tool muốn giao cho nhân viên. Bỏ chọn bớt sẽ tiết kiệm token mỗi lượt gọi — mỗi tool được bật đều phải kèm schema vào request.
           <a href="javascript:void(0)" data-click="toggleAllMcpTools" data-click-args='${jattr(true)}'>Chọn tất cả</a> ·
           <a href="javascript:void(0)" data-click="toggleAllMcpTools" data-click-args='${jattr(false)}'>Bỏ chọn tất cả</a></div>`
      + `<div class="skill-conn-tools" id="skill-mcp-tool-picker">${renderMcpToolPicker(tools)}</div>`;
  }
  const title = r.executed
    ? `Kết nối được — HTTP ${r.status_code}${ms}`
    : `Tới được server — HTTP ${r.status_code}${ms} (chưa gọi thật)`;
  return `<div class="skill-conn-title">${esc(title)}</div>`
    + (r.note ? `<div class="skill-conn-detail">${esc(r.note)}</div>` : '');
}

// Tool của MCP server đang được chọn để giao cho nhân viên.
// null = chưa từng chọn -> backend lấy tất cả (tương thích skill tạo trước tính năng này).
let skillMcpSelectedTools = null;
let mcpAvailableTools = [];

function renderMcpToolPicker(tools) {
  const chosen = new Set(skillMcpSelectedTools || []);
  return tools.map(t => `
    <label class="skill-conn-tool skill-conn-tool-pick${chosen.has(t.name) ? ' picked' : ''}">
      <input type="checkbox" ${chosen.has(t.name) ? 'checked' : ''}
             data-change="toggleMcpTool" data-change-args='${jattr(t.name, "$checked")}'>
      <span>
        <span class="skill-conn-tool-name">${esc(t.name)}</span>
        <span class="skill-conn-tool-desc">${esc((t.description || 'Không có mô tả').split('\n')[0])}</span>
      </span>
    </label>`).join('');
}

export function toggleMcpTool(name, on) {
  const set = new Set(skillMcpSelectedTools || []);
  if (on) set.add(name); else set.delete(name);
  skillMcpSelectedTools = mcpAvailableTools.filter(n => set.has(n));
  refreshMcpPickerStyles();
}

export function toggleAllMcpTools(on) {
  skillMcpSelectedTools = on ? mcpAvailableTools.slice() : [];
  const box = document.getElementById('skill-mcp-tool-picker');
  if (box) {
    const chosen = new Set(skillMcpSelectedTools);
    box.querySelectorAll('label').forEach(label => {
      const name = label.querySelector('.skill-conn-tool-name')?.textContent || '';
      const input = label.querySelector('input');
      if (input) input.checked = chosen.has(name);
    });
  }
  refreshMcpPickerStyles();
}

function refreshMcpPickerStyles() {
  const box = document.getElementById('skill-mcp-tool-picker');
  if (!box) return;
  box.querySelectorAll('label').forEach(label => {
    label.classList.toggle('picked', !!label.querySelector('input')?.checked);
  });
}

function renderConnFail(r) {
  const what = r.status_code != null ? `HTTP ${r.status_code}` : 'Không kết nối được';
  return `<div class="skill-conn-title">${esc(what)}</div>`
    + `<div class="skill-conn-detail">${esc(r.error || r.note || 'Không rõ nguyên nhân')}</div>`;
}

export function toggleSkillSecret(id) {
  const el = document.getElementById(id);
  el.type = el.type === 'password' ? 'text' : 'password';
}

function parseSkillJson(id, label) {
  try { return JSON.parse(document.getElementById(id).value || '{}'); }
  catch { showToast(`${label} phải là JSON hợp lệ`, 'error'); return null; }
}

function buildSkillConfig(type, showErrors = true) {
  if (type === 'builtin') {
    const legacy = parseSkillJson('skill-builtin-legacy', 'Dữ liệu cấu hình cũ');
    if (legacy === null) return null;
    const toolName = document.getElementById('skill-builtin-tool').value;
    if (!toolName) {
      if (showErrors) showToast('Hãy chọn một công cụ hệ thống', 'error');
      return null;
    }
    return { ...legacy, tool_name: toolName };
  }
  if (type === 'api') {
    const extra = parseSkillJson('skill-api-extra', 'Tuỳ chọn nâng cao');
    if (extra === null) return null;
    return {
      ...extra,
      endpoint: document.getElementById('skill-api-endpoint').value.trim(),
      method: document.getElementById('skill-api-method').value,
      api_key: document.getElementById('skill-api-key').value,
    };
  }
  if (type === 'mcp') {
    const legacy = parseSkillJson('skill-mcp-legacy', 'Dữ liệu cấu hình cũ');
    if (legacy === null) return null;
    const cfg = {
      ...legacy,
      target: document.getElementById('skill-mcp-target').value.trim(),
      transport: document.getElementById('skill-mcp-transport').value,
      token: document.getElementById('skill-mcp-token').value,
    };
    // null = chưa từng chọn -> lấy tất cả tool của server (tương thích ngược).
    // Mảng rỗng vẫn được lưu: đó là chủ ý "tắt hết tool của server này".
    if (Array.isArray(skillMcpSelectedTools)) cfg.tools = skillMcpSelectedTools;
    return cfg;
  }
  if (type === 'custom') {
    const custom = parseSkillJson('skill-config', 'Cấu hình Custom');
    if (custom === null) return null;
    delete custom.image_pool_id;
    return custom;
  }
  if (showErrors) showToast('Hãy chọn một loại kết nối', 'error');
  return null;
}

function populateSkillConfig(type, config) {
  resetSkillConfigFields();
  const cfg = config && typeof config === 'object' && !Array.isArray(config) ? config : {};
  if (type === 'builtin') {
    const selectedTool = cfg.tool_name || cfg.builtin_name || '';
    renderBuiltinToolOptions(selectedTool);
    const legacy = { ...cfg }; delete legacy.tool_name; delete legacy.builtin_name;
    if (Object.keys(legacy).length) {
      document.getElementById('skill-builtin-legacy').value = JSON.stringify(legacy, null, 2);
      document.getElementById('skill-builtin-legacy-wrap').style.display = '';
    }
  } else if (type === 'api') {
    document.getElementById('skill-api-endpoint').value = cfg.endpoint || '';
    document.getElementById('skill-api-method').value = ['GET','POST','PUT','PATCH','DELETE'].includes(String(cfg.method).toUpperCase()) ? String(cfg.method).toUpperCase() : 'GET';
    document.getElementById('skill-api-key').value = cfg.api_key || '';
    const extra = { ...cfg }; delete extra.endpoint; delete extra.method; delete extra.api_key;
    document.getElementById('skill-api-extra').value = JSON.stringify(extra, null, 2);
  } else if (type === 'mcp') {
    document.getElementById('skill-mcp-target').value = cfg.target || '';
    document.getElementById('skill-mcp-transport').value = ['stdio','http','sse'].includes(cfg.transport) ? cfg.transport : 'stdio';
    document.getElementById('skill-mcp-token').value = cfg.token || '';
    skillMcpSelectedTools = Array.isArray(cfg.tools) ? cfg.tools.slice() : null;
    const legacy = { ...cfg }; delete legacy.target; delete legacy.transport; delete legacy.token; delete legacy.tools;
    if (Object.keys(legacy).length) {
      document.getElementById('skill-mcp-legacy').value = JSON.stringify(legacy, null, 2);
      document.getElementById('skill-mcp-legacy-wrap').style.display = '';
    }
  } else {
    document.getElementById('skill-config').value = JSON.stringify(config ?? {}, null, 2);
    updateSkillImagePoolField(cfg);
  }
}

function renderSkillReview() {
  const type = document.getElementById('skill-type').value;
  const config = buildSkillConfig(type, false);
  const item = (label, value) => `<div class="skill-review-item"><div class="skill-review-label">${esc(label)}</div><div class="skill-review-value">${esc(value || 'Chưa thiết lập')}</div></div>`;
  document.getElementById('skill-review-summary').innerHTML = [
    item('Tên kỹ năng', document.getElementById('skill-name').value.trim()),
    item('Mô tả', document.getElementById('skill-description').value.trim()),
    item('Loại kết nối', SKILL_TYPE_LABELS[type] || 'Chưa chọn'),
    item('Cấu hình', config ? JSON.stringify(config, null, 2) : 'JSON chưa hợp lệ'),
  ].join('');
}

export function goSkillWizardStep(step, force = false) {
  step = Math.max(1, Math.min(3, step));
  const editing = Boolean(document.getElementById('skill-id').value);
  if (!force && !editing && step > skillWizardMaxStep + 1) return;
  if (step === 3) renderSkillReview();
  skillWizardStep = step;
  skillWizardMaxStep = Math.max(skillWizardMaxStep, step);
  document.querySelectorAll('.skill-wizard-step').forEach(el => el.classList.toggle('active', Number(el.dataset.skillStep) === step));
  document.querySelectorAll('.skill-wizard-tab').forEach((el, i) => {
    el.classList.toggle('active', i + 1 === step);
    el.classList.toggle('done', i + 1 < step);
  });
  document.getElementById('skill-wizard-back').style.visibility = step === 1 ? 'hidden' : 'visible';
  document.getElementById('skill-wizard-next').style.display = step === 3 ? 'none' : '';
  document.getElementById('skill-wizard-save').style.display = step === 3 ? '' : 'none';
}

export function changeSkillWizardStep(delta) {
  if (delta > 0 && skillWizardStep === 1 && !document.getElementById('skill-name').value.trim()) return showToast('Tên kỹ năng là bắt buộc', 'error');
  if (delta > 0 && skillWizardStep === 2 && !document.getElementById('skill-type').value) {
    document.getElementById('skill-type-required').style.display = '';
    return showToast('Hãy chọn một loại kết nối', 'error');
  }
  goSkillWizardStep(skillWizardStep + delta, true);
}

export function selectSkill(id) {
  selectedSkillId = id;
  renderSkillList();
  const s = skills.find(x => x.id === id);
  if (!s) return;
  _clearSkillFilePreview();
  document.getElementById('skill-wizard-layer').style.display = 'flex';
  document.getElementById('skill-form-container').style.display = 'flex';
  document.getElementById('skill-form-title').textContent = s.name;
  document.getElementById('skill-delete-btn').style.display = '';
  document.getElementById('skill-id').value = s.id;
  document.getElementById('skill-name').value = s.name;
  document.getElementById('skill-description').value = s.description || '';
  chooseSkillType(Object.hasOwn(SKILL_TYPE_LABELS, s.type) ? s.type : 'custom');
  populateSkillConfig(Object.hasOwn(SKILL_TYPE_LABELS, s.type) ? s.type : 'custom', s.config);
  skillWizardMaxStep = 3;
  goSkillWizardStep(1, true);
}

export function newSkill() {
  selectedSkillId = null;
  renderSkillList();
  _clearSkillFilePreview();
  document.getElementById('skill-wizard-layer').style.display = 'flex';
  document.getElementById('skill-form-container').style.display = 'flex';
  document.getElementById('skill-form-title').textContent = t('js.new_skill');
  document.getElementById('skill-delete-btn').style.display = 'none';
  document.getElementById('skill-id').value = '';
  document.getElementById('skill-name').value = '';
  document.getElementById('skill-description').value = '';
  document.getElementById('skill-type').value = '';
  resetSkillConfigFields();
  // Chưa chọn loại kết nối thì chưa có gì để thử. chooseSkillType() sẽ bật lại
  // khi người dùng chọn api/mcp.
  document.getElementById('skill-conn-test').style.display = 'none';
  clearSkillConnResult();
  skillMcpSelectedTools = null;   // skill mới: chưa chọn gì -> mặc định bật hết sau khi test
  mcpAvailableTools = [];
  document.querySelectorAll('.skill-type-option').forEach(el => el.classList.remove('selected'));
  document.querySelectorAll('.skill-config-panel').forEach(el => el.classList.remove('active'));
  skillWizardMaxStep = 1;
  goSkillWizardStep(1, true);
}

export function cancelSkillForm() {
  selectedSkillId = null;
  document.getElementById('skill-form-container').style.display = 'none';
  document.getElementById('skill-wizard-layer').style.display = 'none';
  renderSkillList();
}

export async function saveSkill() {
  const id = document.getElementById('skill-id').value;
  const type = document.getElementById('skill-type').value;
  if (!type) return showToast('Hãy chọn một loại kết nối', 'error');
  const config = buildSkillConfig(type);
  if (config === null) return;
  const body = {
    name: document.getElementById('skill-name').value.trim(),
    description: document.getElementById('skill-description').value.trim(),
    type,
    config,
  };
  if (!body.name) return showToast('Name is required', 'error');
  try {
    if (id) { await api('PATCH', `/skills/${id}`, body); }
    else { await api('POST', '/skills/', body); }
    await loadSkills();
    cancelSkillForm();
    renderAgentSkillsSelect();
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

export async function deleteSkill() {
  const id = document.getElementById('skill-id').value;
  if (!id) return;
  if (!(await showConfirm('Delete this skill?'))) return;
  await api('DELETE', `/skills/${id}`);
  await loadSkills();
  cancelSkillForm();
}

// ════════════════════════════════════════
