import { agents } from './agents.js';
import { api } from './api.js';
import { DEFAULT_AVATAR, avatarHtml } from './avatar.js';
import { _buildDaySeries, _isoLocal } from './cost.js';
import { icon } from './icons.js';
import { meetings } from './meetings.js';
import { projects } from './projects.js';
import { skills } from './skills.js';
import { switchTab } from './tabs.js';
import { esc, jattr } from './utils.js';

// Overview / Home
// ════════════════════════════════════════
const _STATUS_LABEL = {
  completed: 'Hoàn thành', failed: 'Thất bại',
  running: 'Đang chạy', cancelled: 'Đã huỷ', pending: 'Chờ xử lý',
};
const _STATUS_COLOR = {
  completed: 'var(--green)', failed: 'var(--red)',
  running: 'var(--cyan)', cancelled: 'var(--muted)', pending: 'var(--amber)',
};

let _homeCostChart = null;

function _homeDate(value) {
  if (!value) return null;
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : value.replace(' ', 'T') + 'Z');
}

function _homeTime(value) {
  const d = _homeDate(value);
  return d && !Number.isNaN(d.getTime()) ? d.toLocaleString('vi-VN') : '—';
}

function _homeRelativeTime(value) {
  const d = _homeDate(value);
  if (!d || Number.isNaN(d.getTime())) return '—';
  const seconds = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
  if (seconds < 60) return 'vừa xong';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} phút trước`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} giờ trước`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)} ngày trước`;
  return d.toLocaleDateString('vi-VN');
}

function _renderHomeRuns(runs) {
  const recentEl = document.getElementById('ov-recent-runs');
  if (!recentEl) return;
  if (!runs.length) {
    recentEl.innerHTML = '<div class="home-empty">Chưa có hoạt động nào — khi một quy trình bắt đầu, bạn sẽ thấy ở đây.</div>';
    return;
  }
  recentEl.innerHTML = runs.slice(0, 4).map(r => {
    const st = r.status || 'pending';
    const titleClass = st === 'completed' ? ' is-completed' : st === 'failed' ? ' is-failed' : '';
    return `<div class="recent-run-row" data-click="switchTab" data-click-args='${jattr("auto-runner")}'>
      <span style="display:inline-flex;">${icon('sync')}</span>
      <span class="recent-run-name${titleClass}">${esc(r.task_name || 'Quy trình')}</span>
      <span class="recent-run-time">${_homeTime(r.started_at || r.created_at)}</span>
    </div>`;
  }).join('');
}

async function loadHomeRunningTasks(existingRuns) {
  const runs = existingRuns || (await api('GET', '/workflow/runs?limit=20')).runs || [];
  const running = runs.filter(r => r.status === 'running');
  const el = document.getElementById('home-running-tasks');
  if (el) el.innerHTML = running.length ? `<div class="home-widget-list">${running.map(r => `
    <div class="home-list-row">
      <span style="display:inline-flex;color:var(--sky-ink);">${icon('sync')}</span>
      <div class="home-list-main"><div class="home-list-name">${esc(r.task_name || 'Quy trình')}</div>
      <div class="home-list-meta">Bắt đầu ${_homeTime(r.started_at || r.created_at)}</div></div>
    </div>`).join('')}</div>` : '<div class="home-empty">Chưa có tác vụ nào đang chạy — hệ thống đang rảnh.</div>';
  return runs;
}

async function loadHomeConversations() {
  const el = document.getElementById('home-conversations');
  try {
    const data = await api('GET', '/meetings/messages/recent?limit=8');
    const rooms = data.rooms || [];
    if (!el) return;
    if (!rooms.length) {
      el.innerHTML = '<div class="home-empty">Chưa có hội thoại nào — các trao đổi mới trong phòng họp sẽ xuất hiện ở đây.</div>';
      return;
    }
    el.innerHTML = `<div class="home-widget-list">${rooms.map(room => {
      const agent = (typeof agents !== 'undefined' ? agents : []).find(a => a.name === room.last_sender);
      const avatar = room.last_sender_type === 'agent'
        ? avatarHtml(agent?.avatar_color || DEFAULT_AVATAR, room.last_sender, 'avatar-sm')
        : `<span style="display:inline-flex;color:var(--lavender-ink);">${icon('meeting')}</span>`;
      const content = String(room.last_content || '').replace(/\s+/g, ' ').trim();
      const excerpt = content.length > 58 ? content.slice(0, 58).trimEnd() + '…' : content;
      return `<div class="home-list-row">${avatar}<div class="home-list-main">
        <div class="home-list-name">${esc(room.meeting_name || 'Phòng họp')}</div>
        <div class="home-list-meta">${esc(room.last_sender || 'Hệ thống')}: ${esc(excerpt)} · ${_homeRelativeTime(room.last_created_at)}</div>
      </div>${room.message_count ? `<span class="home-list-meta" style="flex-shrink:0;">${room.message_count} tin</span>` : ''}</div>`;
    }).join('')}</div>`;
  } catch (_) {
    if (el) el.innerHTML = '<div class="home-empty">Chưa thể tải hội thoại gần đây.</div>';
  }
}

async function loadHomeCostTrend() {
  const end = new Date();
  const start = new Date(end); start.setDate(start.getDate() - 6);
  const from = _isoLocal(start), to = _isoLocal(end);
  const data = await api('GET', `/model-pool/cost/report?period=day&date_from=${from}&date_to=${to}`).catch(() => null);
  const ctx = document.getElementById('home-cost-trend');
  if (!ctx || !data) return;
  const byDate = {};
  (data.rows || []).forEach(r => { byDate[r.bucket] = (byDate[r.bucket] || 0) + Number(r.estimated_cost || 0); });
  const series = _buildDaySeries({ from, to }, 'week', byDate);
  const trend = series.values.map((_, index, values) => {
    const window = values.slice(Math.max(0, index - 2), index + 1);
    return +(window.reduce((sum, value) => sum + value, 0) / window.length).toFixed(4);
  });
  const totalEl = document.getElementById('home-cost-total');
  if (totalEl) {
    const totals = data.totals || {};
    const totalText = Object.keys(totals).length
      ? Object.entries(totals).map(([currency, value]) => `${Number(value).toLocaleString('vi-VN', { maximumFractionDigits: 4 })} ${currency}`).join(' · ')
      : '0';
    totalEl.innerHTML = `${esc(totalText)}<small>Tổng 7 ngày</small>`;
  }
  if (_homeCostChart) _homeCostChart.destroy();
  const styles = getComputedStyle(document.documentElement);
  const accent = styles.getPropertyValue('--accent').trim();
  const lavender = styles.getPropertyValue('--lavender-ink').trim();
  const chartContext = ctx.getContext('2d');
  const barGradient = chartContext.createLinearGradient(0, 0, 0, 170);
  barGradient.addColorStop(0, accent);
  barGradient.addColorStop(1, styles.getPropertyValue('--accent-soft').trim());
  const hasCost = series.values.some(value => value > 0);
  _homeCostChart = new Chart(ctx, {
    type: 'bar',
    data: { labels: series.labels, datasets: [
      { type: 'bar', label: 'Chi phí', data: series.values, backgroundColor: barGradient, borderColor: accent, borderWidth: 1, borderRadius: 7, borderSkipped: false, maxBarThickness: 26, order: 2 },
      { type: 'line', label: 'Xu hướng 3 ngày', data: trend, borderColor: lavender, backgroundColor: lavender, borderWidth: 2.2, tension: 0.42, pointRadius: 2.5, pointHoverRadius: 5, pointBackgroundColor: styles.getPropertyValue('--bg-card').trim(), pointBorderColor: lavender, pointBorderWidth: 2, fill: false, order: 1 }
    ] },
    options: {
      responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      animation: { duration: 700, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: styles.getPropertyValue('--text').trim(), titleColor: styles.getPropertyValue('--bg-card').trim(), bodyColor: styles.getPropertyValue('--bg-card').trim(),
          padding: 10, cornerRadius: 9, displayColors: true,
          callbacks: { label: context => ` ${context.dataset.label}: ${Number(context.raw).toLocaleString('vi-VN', { maximumFractionDigits: 4 })}` }
        }
      },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: styles.getPropertyValue('--muted').trim(), font: { size: 9 }, maxRotation: 0 } },
        y: { display: hasCost, beginAtZero: true, border: { display: false }, grid: { color: styles.getPropertyValue('--border').trim(), drawTicks: false }, ticks: { color: styles.getPropertyValue('--muted').trim(), font: { size: 9 }, padding: 6, maxTicksLimit: 4 } }
      }
    }
  });
}

async function loadHomeAlerts() {
  const el = document.getElementById('home-alerts');
  const section = document.getElementById('home-alerts-section');
  try {
    const data = await api('GET', '/projects/items/alerts');
    const alerts = (data.alerts || []).filter(a => !a.status || a.status === 'open');
    section?.classList.toggle('has-alerts', alerts.length > 0);
    if (!el) return;
    el.innerHTML = alerts.length ? alerts.map(a => `<div class="home-alert-row">
      <span style="display:inline-flex;color:var(--peach-ink);">${icon('warning')}</span>
      <div><div class="home-list-name">${esc(a.title || 'Tác vụ cần chú ý')}</div>
      <div class="home-list-meta">${esc(a.reason || 'Cần kiểm tra')} · ${_homeTime(a.created_at)}</div></div>
    </div>`).join('') : '<div style="font-size:12px;color:var(--ink-muted);">Mọi thứ đang ổn — chưa có cảnh báo nào.</div>';
  } catch (_) {
    if (el) el.innerHTML = '<div style="font-size:12px;color:var(--ink-muted);">Chưa thể kiểm tra cảnh báo lúc này.</div>';
  }
}

let overviewClockTimer = null;

function updateOverviewClock() {
  const now = new Date();
  const dateStr = now.toLocaleDateString('vi-VN', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'Asia/Ho_Chi_Minh',
  });
  const timeStr = now.toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'Asia/Ho_Chi_Minh',
  });
  const ovDate = document.getElementById('ov-date');
  if (ovDate) {
    ovDate.innerHTML = `<span>${dateStr.charAt(0).toUpperCase() + dateStr.slice(1)}</span>`
      + `<span class="overview-clock-separator">·</span>`
      + `<span class="overview-clock-time">${timeStr}</span>`;
  }
}

function startOverviewClock() {
  updateOverviewClock();
  if (!overviewClockTimer) overviewClockTimer = setInterval(updateOverviewClock, 1000);
}

function _formatHomeCostTotals(totals) {
  const entries = Object.entries(totals || {});
  if (!entries.length) return '0';
  return entries.map(([currency, rawValue]) => {
    const value = Number(rawValue) || 0;
    const rounded = Number(value.toFixed(2));
    const amount = value > 0 && rounded === 0
      ? '< 0,01'
      : value.toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return `${amount} ${currency}`;
  }).join(' · ');
}

async function loadHomeCostComparison(todayTotals) {
  const el = document.getElementById('ov-cost-today-sub');
  if (!el) return;
  el.textContent = '';
  el.classList.remove('up', 'down');
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const date = _isoLocal(yesterday);
  const report = await api('GET', `/model-pool/cost/report?period=day&date_from=${date}&date_to=${date}`).catch(() => null);
  const previousTotals = report?.totals || {};
  const currencies = Object.keys(previousTotals);
  if (!currencies.length || currencies.some(currency => !(currency in (todayTotals || {})))) {
    el.textContent = 'chưa đủ dữ liệu';
    return;
  }
  const previous = currencies.reduce((sum, currency) => sum + Number(previousTotals[currency] || 0), 0);
  if (previous <= 0) {
    el.textContent = 'chưa đủ dữ liệu';
    return;
  }
  const current = currencies.reduce((sum, currency) => sum + Number(todayTotals[currency] || 0), 0);
  const change = Math.round((current - previous) / previous * 100);
  if (change === 0) {
    el.textContent = 'Không đổi so với hôm qua';
    return;
  }
  const increased = change > 0;
  el.textContent = `${increased ? '↑' : '↓'} ${Math.abs(change)}% so với hôm qua`;
  el.classList.add(increased ? 'down' : 'up');
}

async function loadHomeMiniStats() {
  document.getElementById('ms-icon-wf').innerHTML = icon('workflow');
  document.getElementById('ms-icon-auto').innerHTML = icon('sync');
  document.getElementById('ms-icon-meet').innerHTML = icon('meeting');
  document.getElementById('ms-icon-tool').innerHTML = icon('code');
  const [workflows, automations, meetingData, skillData] = await Promise.all([
    api('GET', '/workflow/tasks?kind=company').catch(() => null),
    api('GET', '/workflow/tasks?kind=automation').catch(() => null),
    api('GET', '/meetings/').catch(() => null),
    api('GET', '/skills/').catch(() => null),
  ]);
  const setTaskCount = (id, data) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (!data) { el.textContent = '—'; return; }
    const tasks = data.tasks || [];
    el.textContent = `${tasks.filter(task => task.status === 'active').length}/${tasks.length}`;
  };
  setTaskCount('ms-workflows', workflows);
  setTaskCount('ms-automations', automations);
  const meetingsEl = document.getElementById('ms-meetings');
  if (meetingsEl) meetingsEl.textContent = meetingData ? (meetingData.meetings || []).length : '—';
  const toolsEl = document.getElementById('ms-tools');
  if (toolsEl) {
    const items = skillData?.skills || [];
    toolsEl.textContent = skillData
      ? `${items.filter(item => item.enabled !== 0 && item.enabled !== false).length}/${items.length}`
      : '—';
  }
}

export async function renderOverview() {
  startOverviewClock();
  const now = new Date();
  document.getElementById('home-running-icon').innerHTML = icon('sync');
  document.getElementById('home-conversation-icon').innerHTML = icon('meeting');
  document.getElementById('home-cost-icon').innerHTML = icon('cost');
  document.getElementById('home-alert-icon').innerHTML = icon('warning');
  const agentsEl = document.getElementById('ov-n-agents');
  if (agentsEl) agentsEl.textContent = typeof agents !== 'undefined' ? agents.length : 0;
  const agentsSubEl = document.getElementById('ov-n-agents-sub');
  if (agentsSubEl) agentsSubEl.textContent = `${agents.filter(agent => agent.enabled !== 0 && agent.enabled !== false).length} đang bật`;

  const [runsResult, overview] = await Promise.all([
    api('GET', '/workflow/runs?limit=20').catch(() => ({ runs: [] })),
    api('GET', '/model-pool/cost/overview').catch(() => null),
  ]);
  const runs = runsResult.runs || [];
  const running = runs.filter(r => r.status === 'running');
  const today = _isoLocal(now);
  const todayRuns = runs.filter(r => {
    const d = _homeDate(r.started_at || r.created_at);
    return d && _isoLocal(d) === today;
  });
  const finished = todayRuns.filter(r => r.status === 'completed' || r.status === 'failed');
  const success = finished.filter(r => r.status === 'completed').length;
  document.getElementById('ov-n-running').textContent = running.length;
  document.getElementById('ov-n-running-sub').textContent = `${todayRuns.length} lượt chạy hôm nay`;
  document.getElementById('ov-success-rate').textContent = finished.length ? `${Math.round(success / finished.length * 100)}%` : '—';
  document.getElementById('ov-success-rate-sub').textContent = `${success}/${finished.length} lượt hoàn thành`;
  const totals = overview?.today?.totals || {};
  document.getElementById('ov-cost-today').textContent = _formatHomeCostTotals(totals);
  _renderHomeRuns(runs);
  await Promise.all([loadHomeRunningTasks(runs), loadHomeConversations(), loadHomeCostTrend(), loadHomeAlerts(), loadHomeCostComparison(totals), loadHomeMiniStats()]);
}

// ════════════════════════════════════════
