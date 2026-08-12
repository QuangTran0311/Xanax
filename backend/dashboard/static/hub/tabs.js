import { agents } from './agents.js';
import { loadAssets } from './assets.js';
import { loadCostTab } from './cost.js';
import { loadModelPool } from './model-pool.js';
import { opsRenderSubTab } from './ops.js';
import { renderOverview } from './overview.js';
import { currentProjectId, currentProjectSubTab } from './projects.js';
import { skills } from './skills.js';

// Tab switching
// ════════════════════════════════════════
const _HUB_TABS = new Set(['home','agents','skills','tasks','meeting','train','company-runner','auto-runner','assets','runner','model','cost','settings']);

export function switchTab(tab, pushState = true) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + tab));
  // Lazy-load iframes on first visit
  const panel = document.getElementById('tab-' + tab);
  const iframe = panel?.querySelector('iframe[data-src]');
  if (iframe && iframe.src === 'about:blank') {
    iframe.src = iframe.dataset.src;
    delete iframe.dataset.src;
  }
  // Update browser URL without reload
  if (pushState) {
    const urlPath = tab === 'home' ? '/hub' : '/hub/' + tab;
    history.pushState({tab}, '', urlPath);
  }
  if (tab === 'company-runner') _syncRunnerIframe('company');
  if (tab === 'auto-runner') _syncRunnerIframe('automation');
  // Refresh data when entering certain tabs
  if (tab === 'home')  renderOverview();
  if (tab === 'model') { loadModelPool(); }
  if (tab === 'assets') { loadAssets(); }
  if (tab === 'cost') { loadCostTab(); }
  if (tab === 'tasks' && currentProjectId) opsRenderSubTab(currentProjectSubTab);
}

// Restore tab on browser back/forward
window.addEventListener('popstate', e => {
  const tab = e.state?.tab || _tabFromPath();
  if (tab === 'company-runner') _syncRunnerIframe('company');
  if (tab === 'auto-runner') _syncRunnerIframe('automation');
  if (_HUB_TABS.has(tab)) switchTab(tab, false);
});

export function _tabFromPath() {
  const seg = location.pathname.split('/').filter(Boolean);
  const candidate = seg[1]; // /hub/<candidate>
  if (!candidate) return 'home'; // pathname is exactly /hub
  return _HUB_TABS.has(candidate) ? candidate : 'home';
}

// /hub/company-runner/<id> hoặc /hub/auto-runner/<id> — sub-route mở trang chỉnh sửa quy trình
function _runnerIdFromPath() {
  const seg = location.pathname.split('/').filter(Boolean); // ['hub','company-runner','id']
  if ((seg[1] === 'company-runner' || seg[1] === 'auto-runner' || seg[1] === 'runner') && seg[2]) return decodeURIComponent(seg[2]);
  return null;
}

export function _syncRunnerIframe(tabType) {
  const iframeId = tabType === 'company' ? 'company-runner-iframe' : 'auto-runner-iframe';
  const iframe = document.getElementById(iframeId);
  if (!iframe) return;
  const runnerId = _runnerIdFromPath();
  const targetSrc = '/taskrunner' + (runnerId ? '/' + encodeURIComponent(runnerId) : '') + '?embed=1&tab=' + tabType + '&ui=trigger-inspector-4';
  if (iframe.src === 'about:blank') {
    // Chưa từng load — ghi vào data-src để switchTab() lazy-load đúng route
    iframe.dataset.src = targetSrc;
  } else if (!iframe.src.endsWith(targetSrc)) {
    iframe.src = targetSrc;
  }
}

// ════════════════════════════════════════
