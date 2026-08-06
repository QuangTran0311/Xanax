import { loadAgents, loadDepartments, updateAgentPreview } from './agents.js';
import { api } from './api.js';
import { AVATAR_COLORS, AVATAR_ICONS, AVATAR_ICON_LABEL, AVATAR_PALETTE, AVATAR_PALETTE_LABEL, DEFAULT_AVATAR, avatarShape } from './avatar.js';
import { addTestCase, loadBenchmarks } from './benchmark.js';
import { icon } from './icons.js';
import { loadMeetings } from './meetings.js';
import { loadModelPool, modelPool } from './model-pool.js';
import { loadProjects } from './projects.js';
import { loadSkills } from './skills.js';
import { _syncRunnerIframe, _tabFromPath, switchTab } from './tabs.js';
import { t } from './ui.js';
import { esc } from './utils.js';

// Init
// ════════════════════════════════════════
export async function init() {
  try {
    const me = await api('GET', '/auth/me');
    if (me?.username) {
      document.getElementById('topbar-user-name').textContent = me.username;
      const si = document.getElementById('settings-session-info');
      if (si) si.textContent = t('js.logged_as', me.username);
    }
  } catch {}
  await loadDepartments();
  await Promise.all([loadAgents(), loadSkills(), loadProjects(), loadMeetings(), loadBenchmarks(), loadModelPool()]);
  initAvatarPicker();
  await addTestCase(); // start with one test case
  // Activate tab from URL path (home is default for /hub)
  _syncRunnerIframe();
  switchTab(_tabFromPath(), false);
}

export function initAvatarPicker(selectedIconKey = 'bot', selectedColorKey = DEFAULT_AVATAR) {
  const el = document.getElementById('avatar-picker');
  if (!el) return;
  const currentIcon = AVATAR_ICONS[selectedIconKey] ? selectedIconKey : 'bot';
  const currentColor = AVATAR_PALETTE.includes(selectedColorKey) ? selectedColorKey : DEFAULT_AVATAR;
  el.innerHTML = `<div class="avatar-picker-group"><div class="avatar-picker-label">Chọn hình đại diện</div><div class="avatar-shape-grid">` +
    Object.keys(AVATAR_ICONS).map(key => `<div class="avatar-shape-opt${key===currentIcon?' selected':''}" data-avatar-icon="${key}" onclick="selectAvatarShape(this)" title="${AVATAR_ICON_LABEL[key]}">${avatarShape(key)}</div>`).join('') +
    `</div></div><div class="avatar-picker-group"><div class="avatar-picker-label">Chọn màu nền</div><div class="avatar-picker-grid">` + AVATAR_PALETTE.map(key => `
    <div class="avatar-opt${key===currentColor?' selected':''}" data-icon="${key}" onclick="selectAvatar(this)" title="${AVATAR_PALETTE_LABEL[key]}"
         style="background:${AVATAR_COLORS[key].bg};color:${AVATAR_COLORS[key].ink};">${avatarShape(currentIcon)}</div>
  `).join('') + `</div></div>`;
}

export function selectAvatarShape(el) {
  document.querySelectorAll('.avatar-shape-opt').forEach(s => s.classList.remove('selected'));
  el.classList.add('selected');
  const shape = el.dataset.avatarIcon;
  document.querySelectorAll('.avatar-opt').forEach(color => { color.innerHTML = avatarShape(shape); });
  updateAgentPreview();
}

export function selectAvatar(el) {
  document.querySelectorAll('.avatar-opt').forEach(s => s.classList.remove('selected'));
  el.classList.add('selected');
  updateAgentPreview();
}

// ── Danh sách model ưu tiên của nhân viên (tối đa 5, tự fallback khi lỗi) ────
const AGENT_MAX_MODELS = 5;
export let agentModelIds = [];

export function setAgentModelIds(ids) {
  agentModelIds = Array.isArray(ids) ? [...ids] : [];
  renderAgentModelList();
}

export function renderAgentModelList() {
  const el = document.getElementById('agent-model-list');
  if (!el) return;
  if (!agentModelIds.length) {
    el.innerHTML = '<div style="font-size:12px;color:var(--muted);padding:4px 0;">Chưa chọn model nào — sẽ dùng model mặc định (Hermes).</div>';
  } else {
    el.innerHTML = agentModelIds.map((id, i) => {
      const m = modelPool.find(x => x.id === id);
      const label = m ? `${esc(m.name)} (${esc(m.model_id)})` : `Model #${id} (đã xoá khỏi pool)`;
      const upBtn = i > 0 ? `<button class="btn btn-ghost btn-sm" onclick="moveAgentModel(${i},-1)" style="padding:2px 6px;" title="Ưu tiên hơn">↑</button>` : '';
      const dnBtn = i < agentModelIds.length - 1 ? `<button class="btn btn-ghost btn-sm" onclick="moveAgentModel(${i},1)" style="padding:2px 6px;" title="Ưu tiên thấp hơn">↓</button>` : '';
      return `<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;background:var(--bg2);border-radius: 0;font-size:12px;">
        <span style="width:18px;height:18px;border-radius:50%;background:var(--cyan);color:#000;font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;">${i+1}</span>
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${label}</span>
        ${upBtn}${dnBtn}
        <button class="btn btn-ghost btn-sm" onclick="removeAgentModel(${i})" style="padding:2px 6px;color:var(--red);" title="Xoá khỏi danh sách">${icon('close')}</button>
      </div>`;
    }).join('');
  }
  populateAgentModelAddSelect();
}

function populateAgentModelAddSelect() {
  const sel = document.getElementById('agent-model-add');
  const hint = document.getElementById('agent-model-empty-hint');
  if (!sel) return;
  if (!modelPool.length) {
    hint.style.display = '';
    sel.style.display = 'none';
    return;
  }
  hint.style.display = 'none';
  const remaining = modelPool.filter(m => !agentModelIds.includes(m.id));
  if (agentModelIds.length >= AGENT_MAX_MODELS || !remaining.length) {
    sel.style.display = 'none';
    return;
  }
  sel.style.display = '';
  sel.innerHTML = '<option value="">+ Thêm model vào danh sách ưu tiên...</option>' +
    remaining.map(m => `<option value="${m.id}">${esc(m.name)} (${esc(m.model_id)})</option>`).join('');
}

export function addAgentModel(idStr) {
  if (!idStr) return;
  const id = parseInt(idStr);
  if (agentModelIds.length >= AGENT_MAX_MODELS || agentModelIds.includes(id)) return;
  agentModelIds.push(id);
  renderAgentModelList();
}
export function removeAgentModel(i) { agentModelIds.splice(i, 1); renderAgentModelList(); }
export function moveAgentModel(i, dir) {
  const ni = i + dir;
  if (ni < 0 || ni >= agentModelIds.length) return;
  [agentModelIds[i], agentModelIds[ni]] = [agentModelIds[ni], agentModelIds[i]];
  renderAgentModelList();
}

// ════════════════════════════════════════
