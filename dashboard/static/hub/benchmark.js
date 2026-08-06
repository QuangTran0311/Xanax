import { api, checkAuthOrRedirect } from './api.js';
import { icon } from './icons.js';
import { showToast } from './modals.js';
import { t } from './ui.js';
import { esc } from './utils.js';

// State của tab Benchmark — chỉ file này gán lại.
let benchmarks = [];
let benchModels = [];
let benchCases = [];
let currentBenchmarkId = null;

// BENCHMARK
// ════════════════════════════════════════
export async function loadBenchmarks() {
  const data = await api('GET', '/benchmarks/');
  benchmarks = data.benchmarks || [];
  renderBenchmarkList();
}

function renderBenchmarkList() {
  const el = document.getElementById('benchmarks-list');
  if (!benchmarks.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${icon('chart')}</div><div class="empty-state-text">No benchmarks yet</div></div>`;
    return;
  }
  el.innerHTML = benchmarks.map(b => `
    <div class="list-item${b.id===currentBenchmarkId?' selected':''}" onclick="openBenchmark(${b.id})">
      <div style="flex:1;min-width:0;">
        <div class="list-item-name">${esc(b.name)}</div>
        <div class="list-item-sub" style="display:flex;gap:6px;margin-top:3px;">
          <span class="badge ${b.status==='completed'?'badge-green':b.status==='running'?'badge-amber':'badge-muted'}">${b.status}</span>
          <span>${b.models.length} models</span>
        </div>
      </div>
    </div>`).join('');
}

export function showBenchmarkCreate() {
  hideBenchmarkViews();
  document.getElementById('benchmark-create-view').style.display = 'flex';
  document.getElementById('benchmark-empty').style.display = 'none';
}

export function cancelBenchmark() {
  hideBenchmarkViews();
  document.getElementById('benchmark-empty').style.display = 'flex';
}

function hideBenchmarkViews() {
  ['benchmark-create-view','benchmark-progress-view','benchmark-results-view','benchmark-empty'].forEach(id => {
    document.getElementById(id).style.display = 'none';
  });
}

export function addBenchModel() {
  const inp = document.getElementById('bench-model-input');
  const m = inp.value.trim();
  if (!m || benchModels.includes(m)) { inp.value = ''; return; }
  benchModels.push(m);
  inp.value = '';
  renderBenchModels();
}

export function removeBenchModel(m) {
  benchModels = benchModels.filter(x => x !== m);
  renderBenchModels();
}

function renderBenchModels() {
  const el = document.getElementById('bench-models-list');
  el.innerHTML = benchModels.map(m => `
    <div class="model-tag">
      ${esc(m)}
      <button class="model-tag-remove" onclick="removeBenchModel('${m}')">×</button>
    </div>`).join('');
}

export async function addTestCase() {
  const el = document.getElementById('bench-cases-list');
  const idx = benchCases.length;
  benchCases.push({ prompt: '', criteria: '' });
  const div = document.createElement('div');
  div.className = 'test-case-item';
  div.id = `case-${idx}`;
  div.innerHTML = `
    <button class="test-case-remove" onclick="removeTestCase(${idx})">×</button>
    <div class="form-group" style="margin-bottom:8px;">
      <label class="form-label">${t('js.case_prompt')}</label>
      <textarea class="form-textarea" id="case-prompt-${idx}" rows="2" placeholder="Ask the model to do something..." oninput="benchCases[${idx}].prompt=this.value"></textarea>
    </div>
    <div class="form-group" style="margin-bottom:0;">
      <label class="form-label">${t('js.case_expected')}</label>
      <input class="form-input" id="case-criteria-${idx}" placeholder="What makes a good answer? (optional)" oninput="benchCases[${idx}].criteria=this.value">
    </div>`;
  el.appendChild(div);
}

export function removeTestCase(idx) {
  document.getElementById(`case-${idx}`)?.remove();
  benchCases[idx] = null;
}

export async function createAndRunBenchmark() {
  const name = document.getElementById('bench-name').value.trim();
  const role = document.getElementById('bench-role').value.trim();
  if (!name) return showToast('Benchmark name is required', 'error');
  if (!benchModels.length) return showToast('Add at least one model to test', 'error');
  const cases = benchCases.filter(Boolean).filter(c => c.prompt.trim());
  if (!cases.length) return showToast('Add at least one test case', 'error');

  try {
    const b = await api('POST', '/benchmarks/', {
      name, role_description: role, test_cases: cases, models: benchModels,
    });
    currentBenchmarkId = b.id;
    await loadBenchmarks();
    runBenchmarkWs(b.id);
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

function runBenchmarkWs(benchmarkId) {
  hideBenchmarkViews();
  document.getElementById('benchmark-progress-view').style.display = 'flex';
  const progressList = document.getElementById('benchmark-progress-list');
  progressList.innerHTML = '';

  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${location.host}/ws/benchmark`);

  const modelStatus = {};

  ws.onopen = () => ws.send(JSON.stringify({ type: 'run', benchmark_id: benchmarkId }));
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);

    if (msg.type === 'started') {
      benchModels.forEach(m => {
        modelStatus[m] = { status: 'pending', scores: null };
        progressList.insertAdjacentHTML('beforeend', `
          <div class="progress-item" id="prog-${m.replace(/[^a-z0-9]/gi,'_')}">
            <div class="progress-status status-pending" id="dot-${m.replace(/[^a-z0-9]/gi,'_')}"></div>
            <div style="flex:1;">
              <div style="font-size:13px;font-weight:500;">${esc(m)}</div>
              <div style="font-size:11px;color:var(--muted);" id="prog-sub-${m.replace(/[^a-z0-9]/gi,'_')}">${t('js.waiting')}</div>
            </div>
          </div>`);
      });
    }

    if (msg.type === 'progress') {
      const key = msg.model.replace(/[^a-z0-9]/gi,'_');
      const dot = document.getElementById(`dot-${key}`);
      const sub = document.getElementById(`prog-sub-${key}`);
      if (dot) { dot.className = 'progress-status status-running'; }
      if (sub) sub.textContent = `${t('js.case')} ${msg.case_index+1}/${msg.total}: ${msg.prompt}`;
    }

    if (msg.type === 'scored') {
      const key = msg.model.replace(/[^a-z0-9]/gi,'_');
      const dot = document.getElementById(`dot-${key}`);
      const sub = document.getElementById(`prog-sub-${key}`);
      if (dot) dot.className = 'progress-status status-done';
      if (sub) sub.textContent = `${t('js.done_score')} ${msg.scores.total}/10`;
    }

    if (msg.type === 'complete') {
      hideBenchmarkViews();
      document.getElementById('benchmark-results-view').style.display = 'flex';
      document.getElementById('bench-result-title').textContent = benchmarks.find(b=>b.id===benchmarkId)?.name || 'Results';
      showBenchmarkResults(msg.results, msg.recommendation);
      loadBenchmarks();
    }

    if (msg.type === 'error') {
      showToast(t('js.bench_error') + msg.message, 'error');
      hideBenchmarkViews();
      document.getElementById('benchmark-empty').style.display = 'flex';
    }
  };

  ws.onerror = () => {
    showToast(t('js.ws_error'), 'error');
    hideBenchmarkViews();
    document.getElementById('benchmark-empty').style.display = 'flex';
  };
  ws.onclose = (e) => { if (e.code !== 1000) checkAuthOrRedirect(); };
}

export async function openBenchmark(id) {
  currentBenchmarkId = id;
  renderBenchmarkList();
  const b = benchmarks.find(x => x.id === id);
  if (!b) return;

  if (b.status !== 'completed') {
    hideBenchmarkViews();
    document.getElementById('benchmark-empty').style.display = 'flex';
    return;
  }

  const data = await api('GET', `/benchmarks/${id}/results`);
  hideBenchmarkViews();
  document.getElementById('benchmark-results-view').style.display = 'flex';
  document.getElementById('bench-result-title').textContent = b.name;

  const results = (data.results || []).map(r => ({ model: r.model, scores: r.scores }));
  const best = results.reduce((a, b) => (b.scores.total > a.scores.total ? b : a), results[0] || {model:'',scores:{total:0}});
  showBenchmarkResults(results, best.model);
}

function showBenchmarkResults(results, recommendation) {
  if (recommendation) {
    document.getElementById('bench-recommendation').style.display = '';
    document.getElementById('bench-recommended-model').textContent = recommendation;
    const scores = results.find(r => r.model === recommendation)?.scores;
    document.getElementById('bench-recommended-reason').textContent =
      scores ? `Chất lượng: ${scores.quality}/10 · Tốc độ: ${scores.speed_score}/10 · Phản hồi TB: ${scores.avg_response_time}s` : '';
  }
  const tbody = document.getElementById('bench-results-tbody');
  const sorted = [...results].sort((a,b) => b.scores.total - a.scores.total);
  tbody.innerHTML = sorted.map((r, i) => {
    const isBest = r.model === recommendation;
    const qualPct = (r.scores.quality / 10 * 100).toFixed(0);
    const speedPct = (r.scores.speed_score / 10 * 100).toFixed(0);
    return `
      <tr class="${isBest?'best-row':''}">
        <td style="font-size:12px;">
          ${isBest?icon('trophy')+' ':''}${esc(r.model)}
        </td>
        <td>
          <div class="score-bar">
            <div class="score-bar-track"><div class="score-bar-fill" style="width:${qualPct}%;background:${r.scores.quality>=7?'var(--green)':r.scores.quality>=4?'var(--amber)':'var(--red)'};"></div></div>
            <span style="font-size:12px;">${r.scores.quality}/10</span>
          </div>
        </td>
        <td>
          <div class="score-bar">
            <div class="score-bar-track"><div class="score-bar-fill" style="width:${speedPct}%;background:var(--blue);"></div></div>
            <span style="font-size:12px;">${r.scores.speed_score}/10</span>
          </div>
        </td>
        <td style="font-size:12px;color:var(--muted);">${r.scores.avg_response_time}s</td>
        <td>
          <span style="font-size:15px;font-weight:700;color:${r.scores.total>=7?'var(--green)':r.scores.total>=4?'var(--amber)':'var(--red)'};">${r.scores.total}</span>
          <span style="font-size:11px;color:var(--muted);">/10</span>
        </td>
      </tr>`;
  }).join('');
}

// ════════════════════════════════════════
