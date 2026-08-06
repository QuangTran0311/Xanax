import { api } from './api.js';
import { _fmtNum } from './model-pool.js';
import { esc } from './utils.js';

// COST TAB
// ════════════════════════════════════════
let _costChartTrend = null, _costChartByModel = null, _lastCostReport = null;

// dd-mm-yyyy — định dạng ngày chuẩn Việt Nam
function _fmtDateVN(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-');
  return `${d}-${m}-${y}`;
}
function _fmtBucketVN(b) {
  return b.bucket_from === b.bucket_to
    ? _fmtDateVN(b.bucket_from)
    : `${_fmtDateVN(b.bucket_from)} → ${_fmtDateVN(b.bucket_to)}`;
}

// Định dạng Date -> "YYYY-MM-DD" theo giờ ĐỊA PHƯƠNG (không dùng toISOString(),
// vì nó quy đổi sang UTC và có thể lùi 1 ngày vào buổi sáng sớm ở múi giờ +).
export function _isoLocal(d) {
  const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0'), day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function _prevWindow(dateFrom, dateTo) {
  const from = new Date(dateFrom + 'T00:00:00');
  const to = new Date(dateTo + 'T00:00:00');
  const spanDays = Math.round((to - from) / 86400000) + 1;
  const prevTo = new Date(from); prevTo.setDate(prevTo.getDate() - 1);
  const prevFrom = new Date(prevTo); prevFrom.setDate(prevFrom.getDate() - spanDays + 1);
  return { from: _isoLocal(prevFrom), to: _isoLocal(prevTo) };
}

// Khoảng ngày của "kỳ hiện tại" tương ứng với lựa chọn tuần/tháng (dùng cho biểu đồ xu hướng)
function _currentPeriodRange(period) {
  const now = new Date();
  if (period === 'week') {
    const monday = new Date(now); monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));
    const sunday = new Date(monday); sunday.setDate(monday.getDate() + 6);
    return { from: _isoLocal(monday), to: _isoLocal(sunday) };
  }
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { from: _isoLocal(start), to: _isoLocal(end) };
}

function _weekdayLabelVN(dateStr) {
  const names = ['CN', 'Th 2', 'Th 3', 'Th 4', 'Th 5', 'Th 6', 'Th 7'];
  const d = new Date(dateStr + 'T00:00:00');
  return `${names[d.getDay()]} ${_fmtDateVN(dateStr).slice(0, 5)}`;
}

// Dựng chuỗi giá trị theo ngày trong tuần (7 điểm), hoặc nhóm 3 ngày/điểm cho tháng
export function _buildDaySeries(range, period, byDate) {
  const labels = [], values = [];
  let d = new Date(range.from + 'T00:00:00');
  const end = new Date(range.to + 'T00:00:00');
  if (period === 'week') {
    while (d <= end) {
      const iso = _isoLocal(d);
      labels.push(_weekdayLabelVN(iso));
      values.push(+(byDate[iso] || 0).toFixed(4));
      d.setDate(d.getDate() + 1);
    }
  } else {
    while (d <= end) {
      const groupEnd = new Date(d); groupEnd.setDate(groupEnd.getDate() + 2);
      if (groupEnd.getTime() > end.getTime()) groupEnd.setTime(end.getTime());
      let sum = 0;
      const cursor = new Date(d);
      while (cursor <= groupEnd) {
        sum += byDate[_isoLocal(cursor)] || 0;
        cursor.setDate(cursor.getDate() + 1);
      }
      const dIso = _isoLocal(d), geIso = _isoLocal(groupEnd);
      labels.push(dIso === geIso ? _fmtDateVN(dIso) : `${_fmtDateVN(dIso)}→${_fmtDateVN(geIso)}`);
      values.push(+sum.toFixed(4));
      d.setDate(d.getDate() + 3);
    }
  }
  return { labels, values };
}

export async function loadCostTab() {
  const period = document.getElementById('cost-period-select').value;
  const [data, overview] = await Promise.all([
    api('GET', `/model-pool/cost/report?period=${period}`).catch(() => null),
    api('GET', `/model-pool/cost/overview`).catch(() => null),
  ]);
  if (!data) return;
  _lastCostReport = data;
  document.getElementById('cost-range-label').textContent = `${_fmtDateVN(data.date_from)} → ${_fmtDateVN(data.date_to)}`;
  renderCostOverviewCards(overview);
  renderCostDetailTable(data);
  renderCostByModelChart(data);
  await loadCostTrendChart(period);
  toggleTokenColumns(document.getElementById('cost-show-tokens')?.checked);
}

export function toggleTokenColumns(visible) {
  document.querySelectorAll('.token-col').forEach(el => {
    el.style.display = visible ? '' : 'none';
  });
}

// Trục x của biểu đồ xu hướng đổi theo period đang chọn:
// ngày → theo giờ (0h-23h) của hôm nay so với hôm qua;
// tuần → từng ngày trong tuần hiện tại (Thứ 2 → Chủ nhật) so với tuần trước;
// tháng → nhóm mỗi 3 ngày trong tháng hiện tại so với tháng trước.
async function loadCostTrendChart(period) {
  if (period === 'day') {
    const today = _isoLocal(new Date());
    const yest = new Date(); yest.setDate(yest.getDate() - 1);
    const [cur, prev] = await Promise.all([
      api('GET', `/model-pool/cost/report-hourly?date=${today}`).catch(() => null),
      api('GET', `/model-pool/cost/report-hourly?date=${_isoLocal(yest)}`).catch(() => null),
    ]);
    renderCostTrendChartHourly(cur, prev);
    return;
  }
  const range = _currentPeriodRange(period);
  const prevRange = _prevWindow(range.from, range.to);
  const [cur, prev] = await Promise.all([
    api('GET', `/model-pool/cost/report?period=day&date_from=${range.from}&date_to=${range.to}`).catch(() => null),
    api('GET', `/model-pool/cost/report?period=day&date_from=${prevRange.from}&date_to=${prevRange.to}`).catch(() => null),
  ]);
  renderCostTrendChartDays(period, cur, range, prev, prevRange);
}

function renderCostTrendChartHourly(data, prevData) {
  const ctx = document.getElementById('cost-trend-chart');
  if (!ctx) return;
  const sumByHour = rows => {
    const arr = new Array(24).fill(0);
    (rows || []).forEach(r => { arr[r.hour] += r.estimated_cost; });
    return arr.map(v => +v.toFixed(4));
  };
  const labels = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, '0')}h`);
  const values = sumByHour(data && data.rows);
  const datasets = [{ label: 'Hôm nay', data: values, borderColor: '#22d3ee', tension: 0.3 }];
  if (prevData) {
    datasets.push({ label: 'Hôm qua', data: sumByHour(prevData.rows), borderColor: '#a78bfa', borderDash: [6, 4], tension: 0.3 });
  }
  if (_costChartTrend) _costChartTrend.destroy();
  _costChartTrend = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: { responsive: true, plugins: { legend: { display: true } } },
  });
}

function renderCostTrendChartDays(period, data, range, prevData, prevRange) {
  const ctx = document.getElementById('cost-trend-chart');
  if (!ctx) return;
  const byDate = {};
  ((data && data.rows) || []).forEach(r => { byDate[r.bucket_from] = (byDate[r.bucket_from] || 0) + r.estimated_cost; });
  const { labels, values } = _buildDaySeries(range, period, byDate);

  const datasets = [{ label: 'Kỳ này', data: values, borderColor: '#22d3ee', tension: 0.3 }];
  if (prevData && prevRange) {
    const byPrevDate = {};
    (prevData.rows || []).forEach(r => { byPrevDate[r.bucket_from] = (byPrevDate[r.bucket_from] || 0) + r.estimated_cost; });
    let prevValues = _buildDaySeries(prevRange, period, byPrevDate).values;
    while (prevValues.length < values.length) prevValues.push(0);
    prevValues = prevValues.slice(0, values.length);
    datasets.push({ label: 'Kỳ trước', data: prevValues, borderColor: '#a78bfa', borderDash: [6, 4], tension: 0.3 });
  }

  if (_costChartTrend) _costChartTrend.destroy();
  _costChartTrend = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: { responsive: true, plugins: { legend: { display: true } } },
  });
}

function renderCostOverviewCards(overview) {
  const el = document.getElementById('cost-summary-cards');
  if (!overview) { el.innerHTML = '<div style="font-size:12px;color:var(--muted);">Chưa có dữ liệu</div>'; return; }
  const cardsFor = (totals, label, sub) => Object.entries(totals || {}).map(([cur, v]) => `
    <div class="mp-stat-box" style="min-width:190px;">
      <div class="mp-stat-val">${v.toFixed(4)} ${esc(cur)}</div>
      <div class="mp-stat-lbl">${esc(label)}${sub ? ' · ' + esc(sub) : ''}</div>
    </div>`).join('');
  let html = '';
  html += cardsFor(overview.today.totals, 'Chi phí hôm nay', _fmtDateVN(overview.today.date));
  html += cardsFor(overview.this_week.totals, 'Tổng chi phí tuần này', `${_fmtDateVN(overview.this_week.date_from)} → ${_fmtDateVN(overview.this_week.date_to)}`);
  html += cardsFor(overview.this_month.totals, 'Tổng chi phí tháng này', `${_fmtDateVN(overview.this_month.date_from)} → ${_fmtDateVN(overview.this_month.date_to)}`);
  html += cardsFor(overview.all_time, 'Tổng chi phí từ trước đến giờ');
  el.innerHTML = html || '<div style="font-size:12px;color:var(--muted);">Chưa có dữ liệu</div>';
}

export function toggleCostModelRow(rowId) {
  const firstRow = document.querySelector('.' + rowId);
  const willShow = !firstRow || getComputedStyle(firstRow).display === 'none';
  document.querySelectorAll('.' + rowId).forEach(el => { el.style.display = willShow ? 'table-row' : 'none'; });
  const arrow = document.getElementById(rowId + '-arrow');
  if (arrow) arrow.textContent = willShow ? '▾' : '▸';
}

// Theo ngày: chi tiết bấm vào để xem TỪNG LƯỢT GỌI (kèm giờ chính xác).
// Theo tuần/tháng: chi tiết bấm vào để xem tổng theo model trong kỳ đó (như cũ).
function renderCostDetailTable(data) {
  if (data.period === 'day') {
    document.getElementById('cost-detail-title').textContent = 'Chi tiết theo ngày (bấm vào 1 ngày để xem từng lượt gọi model, kèm giờ)';
    document.getElementById('cost-detail-col2-th').textContent = 'Số lượt';
    renderCostDetailTableDaily(data);
  } else {
    document.getElementById('cost-detail-title').textContent = 'Chi tiết theo kỳ (bấm vào 1 dòng để xem chi tiết theo model)';
    document.getElementById('cost-detail-col2-th').textContent = 'Số model';
    renderCostDetailTableGrouped(data);
  }
}

function renderCostDetailTableDaily(data) {
  const tbody = document.getElementById('cost-detail-tbody');
  const rows = data.rows || [];
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);">Không có dữ liệu</td></tr>';
    return;
  }
  // rows đã là 1 dòng / (model, ngày) — gộp theo ngày để làm dòng cha có thể bấm mở.
  const byDay = {};
  rows.forEach(r => {
    const agg = byDay[r.bucket] || (byDay[r.bucket] = {
      bucket_from: r.bucket_from, bucket_to: r.bucket_to, currency: r.currency,
      request_count: 0, tokens_input: 0, tokens_cache: 0, tokens_output: 0, estimated_cost: 0,
    });
    agg.request_count += r.request_count;
    agg.tokens_input += r.tokens_input;
    agg.tokens_cache += r.tokens_cache;
    agg.tokens_output += r.tokens_output;
    agg.estimated_cost += r.estimated_cost;
  });
  const sortedDays = Object.values(byDay).sort((a, b) => a.bucket_from.localeCompare(b.bucket_from));
  let html = '';
  sortedDays.forEach((agg, idx) => {
    const rowId = `cost-day-${idx}`;
    html += `
      <tr id="${rowId}-parent" class="cost-model-row" onclick="toggleCostDayRow('${rowId}','${agg.bucket_from}')">
        <td><span id="${rowId}-arrow">▸</span> ${esc(_fmtBucketVN(agg))}</td>
        <td>${agg.request_count} lượt</td>
        <td>${agg.request_count}</td>
        <td class="token-col">${_fmtNum(agg.tokens_input)}</td>
        <td class="token-col">${_fmtNum(agg.tokens_cache)}</td>
        <td class="token-col">${_fmtNum(agg.tokens_output)}</td>
        <td>${agg.estimated_cost.toFixed(4)} ${esc(agg.currency)}</td>
      </tr>`;
  });
  tbody.innerHTML = html;
}

// Bấm vào 1 ngày trong bảng "theo ngày" → tải (lazy) chi tiết từng lượt gọi
// (called_at chính xác đến giây) của đúng ngày đó, để tra chi phí 1 lượt chạy ngay lập tức.
export async function toggleCostDayRow(rowId, dateStr) {
  const already = document.querySelectorAll('.' + rowId);
  if (already.length) {
    const willShow = already[0].style.display === 'none';
    already.forEach(el => { el.style.display = willShow ? 'table-row' : 'none'; });
    const arrow = document.getElementById(rowId + '-arrow');
    if (arrow) arrow.textContent = willShow ? '▾' : '▸';
    return;
  }
  const arrow = document.getElementById(rowId + '-arrow');
  if (arrow) arrow.textContent = '▾';
  const parentRow = document.getElementById(rowId + '-parent');
  parentRow.insertAdjacentHTML('afterend', `<tr class="${rowId}"><td colspan="7" style="text-align:center;color:var(--muted);font-size:12px;">Đang tải...</td></tr>`);
  const data = await api('GET', `/model-pool/cost/report-calls?date=${dateStr}`).catch(() => null);
  document.querySelectorAll('.' + rowId).forEach(el => el.remove());
  const calls = (data && data.calls) || [];
  let html;
  if (!calls.length) {
    html = `<tr class="${rowId}"><td colspan="7" style="text-align:center;color:var(--muted);font-size:12px;">Không có lượt chạy nào</td></tr>`;
  } else {
    html = calls.map(c => `
      <tr class="${rowId}" style="color:var(--muted);font-size:12px;">
        <td style="padding-left:24px;">${esc((c.called_at || '').split(' ')[1] || c.called_at)}</td>
        <td>${esc(c.name)}</td>
        <td></td>
        <td class="token-col">${_fmtNum(c.tokens_input)}</td>
        <td class="token-col">${_fmtNum(c.tokens_cache)}</td>
        <td class="token-col">${_fmtNum(c.tokens_output)}</td>
        <td>${c.estimated_cost.toFixed(4)} ${esc(c.currency)}</td>
      </tr>`).join('');
  }
  parentRow.insertAdjacentHTML('afterend', html);
  toggleTokenColumns(document.getElementById('cost-show-tokens')?.checked);
}

function renderCostDetailTableGrouped(data) {
  const tbody = document.getElementById('cost-detail-tbody');
  const rows = data.rows || [];
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);">Không có dữ liệu</td></tr>';
    return;
  }
  // Nhóm theo kỳ (tuần/tháng) trước — bấm vào 1 kỳ để xem chi tiết theo model.
  const byBucket = {};
  rows.forEach(r => {
    const agg = byBucket[r.bucket] || (byBucket[r.bucket] = {
      bucket_from: r.bucket_from, bucket_to: r.bucket_to, currency: r.currency,
      request_count: 0, tokens_input: 0, tokens_cache: 0, tokens_output: 0,
      estimated_cost: 0, models: [],
    });
    agg.request_count += r.request_count;
    agg.tokens_input += r.tokens_input;
    agg.tokens_cache += r.tokens_cache;
    agg.tokens_output += r.tokens_output;
    agg.estimated_cost += r.estimated_cost;
    agg.models.push(r);
  });

  const sortedBuckets = Object.values(byBucket).sort((a, b) => a.bucket_from.localeCompare(b.bucket_from));
  let html = '';
  sortedBuckets.forEach((agg, idx) => {
    const rowId = `cost-bucket-${idx}`;
    html += `
      <tr class="cost-model-row" onclick="toggleCostModelRow('${rowId}')">
        <td><span id="${rowId}-arrow">▸</span> ${esc(_fmtBucketVN(agg))}</td>
        <td>${agg.models.length} model</td>
        <td>${agg.request_count}</td>
        <td class="token-col">${_fmtNum(agg.tokens_input)}</td>
        <td class="token-col">${_fmtNum(agg.tokens_cache)}</td>
        <td class="token-col">${_fmtNum(agg.tokens_output)}</td>
        <td>${agg.estimated_cost.toFixed(4)} ${esc(agg.currency)}</td>
      </tr>`;
    agg.models.forEach(m => {
      html += `
      <tr class="cost-bucket-row ${rowId}">
        <td style="padding-left:24px;">${esc(m.name)}</td>
        <td></td>
        <td>${m.request_count}</td>
        <td class="token-col">${_fmtNum(m.tokens_input)}</td>
        <td class="token-col">${_fmtNum(m.tokens_cache)}</td>
        <td class="token-col">${_fmtNum(m.tokens_output)}</td>
        <td>${m.estimated_cost.toFixed(4)} ${esc(m.currency)}</td>
      </tr>`;
    });
  });
  tbody.innerHTML = html;
}

function renderCostByModelChart(data) {
  const ctx = document.getElementById('cost-by-model-chart');
  if (!ctx) return;
  const byModel = {};
  (data.rows || []).forEach(r => { byModel[r.name] = (byModel[r.name] || 0) + r.estimated_cost; });
  const labels = Object.keys(byModel);
  const values = labels.map(l => byModel[l]);
  if (_costChartByModel) _costChartByModel.destroy();
  _costChartByModel = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: ['#22d3ee','#a78bfa','#f472b6','#fb923c','#4ade80','#facc15'] }] },
    options: { responsive: true },
  });
}

export function exportCostXlsx() {
  const period = document.getElementById('cost-period-select').value;
  window.location.href = `/api/model-pool/cost/export.xlsx?period=${period}`;
}

// ════════════════════════════════════════
