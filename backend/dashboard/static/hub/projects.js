import { api } from './api.js';
import { icon } from './icons.js';
import { openProjectModal } from './knowledge.js';
import { meetings, renderMeetingList } from './meetings.js';
import { opsRenderSubTab } from './ops.js';
import { esc, jattr } from './utils.js';

// State của tab Dự án — chỉ file này gán lại.
export let projects = [];
export let currentProjectId = null;
export let currentProjectSubTab = 'results';

// Nút "Sửa" trong đầu trang chi tiết dự án luôn sửa dự án đang mở. Trước đây
// HTML viết openProjectModal(currentProjectId); currentProjectId nay là phạm
// vi module nên gói lại thành hành động riêng.
export function openCurrentProjectModal() { openProjectModal(currentProjectId); }

// PROJECTS / KANBAN
// ════════════════════════════════════════
export async function loadProjects() {
  const data = await api('GET', '/projects/');
  projects = data.projects || [];
  renderProjectGrid();
  if (meetings.length) renderMeetingList();
}

function renderProjectGrid() {
  const grid = document.getElementById('proj-grid');
  if (!grid) return;
  const q = (document.getElementById('proj-search')?.value || '').toLowerCase();
  const list = q ? projects.filter(p => p.name.toLowerCase().includes(q) || (p.description||'').toLowerCase().includes(q)) : projects;
  if (!list.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state-icon">${icon('folder')}</div><div class="empty-state-text">${q ? 'Không tìm thấy dự án nào.' : 'Chưa có dự án nào. Tạo dự án đầu tiên!'}</div></div>`;
    return;
  }
  grid.innerHTML = list.map(p => `
    <div class="proj-card" data-click="openProjectDetail" data-click-args='${jattr(p.id)}'>
      <div class="proj-card-name">${esc(p.name)}</div>
      <div class="proj-card-desc">${esc(p.description || '')}</div>
      <div class="proj-card-stats">
        <span class="proj-stat"><b id="ps-items-${p.id}">—</b> công việc</span>
        <span class="proj-stat"><b id="ps-runs-${p.id}">—</b> lượt chạy</span>
      </div>
    </div>`).join('');
  list.forEach(p => _loadProjCardStats(p.id));
}

export function filterProjectGrid() { renderProjectGrid(); }

async function _loadProjCardStats(pid) {
  try {
    const [items, runs] = await Promise.all([
      api('GET', `/projects/${pid}/items`),
      api('GET', `/workflow/runs?project_id=${pid}&limit=100`),
    ]);
    const ie = document.getElementById(`ps-items-${pid}`);
    const re = document.getElementById(`ps-runs-${pid}`);
    if (ie) ie.textContent = (items.items||[]).length;
    if (re) re.textContent = (runs.runs||[]).length;
  } catch {}
}

export async function openProjectDetail(pid) {
  currentProjectId = pid;
  const proj = projects.find(p => p.id === pid);
  document.getElementById('proj-grid-view').style.display = 'none';
  document.getElementById('proj-detail-view').style.display = 'flex';
  document.getElementById('proj-detail-name').textContent = proj?.name || '';
  document.getElementById('proj-detail-desc').textContent = proj?.description || '';
  switchProjectSubTab('overview');
}

export function closeProjectDetail() {
  currentProjectId = null;
  document.getElementById('proj-detail-view').style.display = 'none';
  document.getElementById('proj-grid-view').style.display = '';
}

export async function switchProjectSubTab(tab) {
  currentProjectSubTab = tab;
  document.querySelectorAll('.proj-subtab').forEach(b => b.classList.toggle('active', b.dataset.subtab === tab));
  document.querySelectorAll('.proj-subtab-panel').forEach(p => p.classList.toggle('active', p.id === 'proj-panel-' + tab));
  await opsRenderSubTab(tab);
}

// ════════════════════════════════════════
