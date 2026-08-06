import { api } from './api.js';
import { icon } from './icons.js';
import { renderAgentModelList } from './init.js';
import { closeModal, showConfirm, showToast } from './modals.js';
import { t } from './ui.js';
import { esc } from './utils.js';

// MODEL POOL
// ════════════════════════════════════════
export let modelPool = [], currentModelId = null;

const CAT_LABEL = { general:'General', coding:'Coding', creative:'Creative', fast:'Fast', analysis:'Analysis' };
const CAT_CLASS = { general:'cat-general', coding:'cat-coding', creative:'cat-creative', fast:'cat-fast', analysis:'cat-analysis' };

export async function loadModelPool() {
  const data = await api('GET', '/model-pool');
  modelPool = data.models || [];
  renderModelList();
  loadModelChart();
  renderAgentModelList();
}

function renderModelList() {
  const el = document.getElementById('mp-list');
  const count = document.getElementById('mp-count');
  if (count) count.textContent = `${modelPool.length} model`;
  if (!modelPool.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${icon('puzzle')}</div><div class="empty-state-text">Chưa có model nào</div></div>`;
    return;
  }
  el.innerHTML = modelPool.map(m => {
    const u = m.usage_today || {};
    const reqPct = m.max_requests_per_day ? Math.min(100, (u.request_count||0) / m.max_requests_per_day * 100) : 0;
    const tokPct = m.max_tokens_per_day   ? Math.min(100, ((u.tokens_input||0)+(u.tokens_output||0)) / m.max_tokens_per_day * 100) : 0;
    const barColor = reqPct >= 90 ? 'var(--red)' : reqPct >= 70 ? 'var(--amber)' : 'var(--cyan)';
    const isOff = !m.enabled;
    return `<div class="mp-model-card${currentModelId===m.id?' selected':''}" onclick="selectModel(${m.id})">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
        <span class="cat-badge ${CAT_CLASS[m.category]||'cat-general'}">${CAT_LABEL[m.category]||m.category}</span>
        ${isOff ? '<span style="font-size:10px;color:var(--muted);">OFF</span>' : ''}
      </div>
      <div class="mp-model-name">${esc(m.name)}</div>
      <div class="mp-model-meta">${esc(m.model_id)} · ${esc(m.provider)}</div>
      ${(m.max_requests_per_day||m.max_tokens_per_day) ? `
        <div class="mp-limit-bar"><div class="mp-limit-fill" style="width:${Math.max(reqPct,tokPct)}%;background:${barColor};"></div></div>
      ` : ''}
    </div>`;
  }).join('');
}

let _mpUsageToday = {};

function _renderLimitBars(maxReq, maxTok) {
  const u = _mpUsageToday;
  const limEl = document.getElementById('mp-d-limits');
  if (!limEl) return;
  const limits = [];
  if (maxReq) {
    const used = u.request_count || 0;
    const pct = Math.min(100, used / maxReq * 100);
    const col = pct >= 90 ? 'var(--red)' : pct >= 70 ? 'var(--amber)' : 'var(--cyan)';
    limits.push(`<div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:4px;">
        <span>Request/ngày</span><span>${used} / ${maxReq}</span>
      </div>
      <div class="mp-limit-bar" style="height:6px;"><div class="mp-limit-fill" style="width:${pct}%;background:${col};transition:width .25s;"></div></div>
    </div>`);
  }
  if (maxTok) {
    const used = (u.tokens_input || 0) + (u.tokens_output || 0);
    const pct = Math.min(100, used / maxTok * 100);
    const col = pct >= 90 ? 'var(--red)' : pct >= 70 ? 'var(--amber)' : 'var(--cyan)';
    limits.push(`<div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:4px;">
        <span>Token/ngày</span><span>${_fmtNum(used)} / ${_fmtNum(maxTok)}</span>
      </div>
      <div class="mp-limit-bar" style="height:6px;"><div class="mp-limit-fill" style="width:${pct}%;background:${col};transition:width .25s;"></div></div>
    </div>`);
  }
  limEl.innerHTML = limits.join('') || '<div style="font-size:12px;color:var(--muted);">Không có giới hạn</div>';
}

export function livePreviewLimits() {
  const maxReq = parseInt(document.getElementById('mp-modal-max-req').value) || 0;
  const maxTok = parseInt(document.getElementById('mp-modal-max-tok').value) || 0;
  _renderLimitBars(maxReq, maxTok);
}

export async function selectModel(id) {
  currentModelId = id;
  renderModelList();
  const entry = await api('GET', `/model-pool/${id}`);
  _mpUsageToday = entry.usage_today || {};
  document.getElementById('mp-empty').style.display = 'none';
  const detail = document.getElementById('mp-detail');
  detail.style.display = 'flex';
  document.getElementById('mp-d-name').textContent = entry.name;
  document.getElementById('mp-d-meta').innerHTML =
    `<span class="cat-badge ${CAT_CLASS[entry.category]||'cat-general'}">${CAT_LABEL[entry.category]||entry.category}</span>
     &nbsp;${esc(entry.model_id)} · ${esc(entry.provider)}`;
  document.getElementById('mp-d-req').textContent  = _mpUsageToday.request_count || 0;
  document.getElementById('mp-d-tin').textContent  = _fmtNum(_mpUsageToday.tokens_input || 0);
  document.getElementById('mp-d-tout').textContent = _fmtNum(_mpUsageToday.tokens_output || 0);
  _renderLimitBars(entry.max_requests_per_day || 0, entry.max_tokens_per_day || 0);
}

async function loadModelChart() {
  const data = await api('GET', '/model-pool/stats?limit=10').catch(() => ({ top_models: [] }));
  const top = data.top_models || [];
  const chart = document.getElementById('mp-chart');
  if (!chart) return;
  if (!top.length) {
    chart.innerHTML = '<div style="font-size:12px;color:var(--muted);margin:auto;">Chưa có dữ liệu</div>';
    return;
  }
  const maxVal = Math.max(...top.map(m => m.total_requests || 0), 1);
  chart.innerHTML = top.map(m => {
    const pct = ((m.total_requests || 0) / maxVal) * 100;
    return `<div class="mp-bar-wrap">
      <div class="mp-bar-label" title="${esc(m.model_id||m.name)}">${esc(m.model_id||m.name)}</div>
      <div class="mp-bar-track"><div class="mp-bar" style="width:${Math.max(pct,1)}%;"></div></div>
      <div class="mp-bar-val">${m.total_requests||0}</div>
    </div>`;
  }).join('');
}

let _modalActiveTab = 'subscription';

const NATIVE_BASE_URLS = { openai: 'https://api.openai.com/v1', anthropic: 'https://api.anthropic.com', gemini: 'https://generativelanguage.googleapis.com' };
const NATIVE_API_STYLES = { openai: 'openai_native', anthropic: 'anthropic_native', gemini: 'gemini_native' };
const NATIVE_PROVIDER_LABELS = { openai: 'OpenAI', anthropic: 'Anthropic', gemini: 'Google Gemini' };
const NATIVE_MODEL_PLACEHOLDERS = { openai: 'gpt-4o', anthropic: 'claude-sonnet-4-5', gemini: 'gemini-2.0-flash' };

const CLI_PROVIDER_LABELS = { claude_cli: 'Claude CLI', codex_cli: 'Codex CLI' };
const CLI_MODEL_PLACEHOLDERS = { claude_cli: 'claude-sonnet-5', codex_cli: 'gpt-5.5' };
const CLI_CONFIG_HINTS = {
  claude_cli: 'Thư mục CLAUDE_CONFIG_DIR. Để trống = ~/.claude. Mỗi tài khoản một thư mục riêng — cách chạy nhiều gói song song.',
  codex_cli: 'Thư mục CODEX_HOME. Để trống = ~/.codex. Mỗi tài khoản một thư mục riêng — cách chạy nhiều gói song song.',
};

export function switchModelModalTab(tab) {
  _modalActiveTab = tab;
  for (const t of ['subscription', 'native', 'cli']) {
    document.getElementById(`mp-subtab-btn-${t}`).classList.toggle('active', tab === t);
    document.getElementById(`mp-subtab-${t}`).style.display = tab === t ? '' : 'none';
  }
  if (tab === 'native') updateNativeModelHints();
  if (tab === 'cli') updateCliModelHints();
}

export function updateNativeModelHints() {
  const p = document.getElementById('mp-modal-native-provider').value;
  document.getElementById('mp-modal-native-model-id').placeholder = NATIVE_MODEL_PLACEHOLDERS[p] || '';
  document.getElementById('mp-modal-native-base-url-preview').value = NATIVE_BASE_URLS[p] || '';
}

export function updateCliModelHints() {
  const e = document.getElementById('mp-modal-cli-engine').value;
  document.getElementById('mp-modal-cli-model-id').placeholder = CLI_MODEL_PLACEHOLDERS[e] || '';
  document.getElementById('mp-modal-cli-config-hint').textContent = CLI_CONFIG_HINTS[e] || '';
}

export function openModelModal(id) {
  const entry = id ? modelPool.find(m => m.id === id) : null;
  document.getElementById('mp-modal-title').textContent = entry ? 'Sửa model' : 'Thêm model';
  document.getElementById('mp-modal-id').value = entry ? entry.id : '';
  document.getElementById('mp-modal-name').value = entry?.name || '';

  const NATIVE_STYLE_TO_PROVIDER = { openai_native: 'openai', anthropic_native: 'anthropic', gemini_native: 'gemini' };
  const isNative = entry && NATIVE_STYLE_TO_PROVIDER[entry.api_style];
  const isCli = entry && CLI_PROVIDER_LABELS[entry.api_style];
  switchModelModalTab(isCli ? 'cli' : (isNative ? 'native' : 'subscription'));
  if (isCli) {
    document.getElementById('mp-modal-cli-engine').value = entry.api_style;
    document.getElementById('mp-modal-cli-model-id').value = entry.model_id || '';
    document.getElementById('mp-modal-cli-config-dir').value = entry.cli_config_dir || '';
    updateCliModelHints();
  } else if (isNative) {
    document.getElementById('mp-modal-native-provider').value = NATIVE_STYLE_TO_PROVIDER[entry.api_style];
    document.getElementById('mp-modal-native-model-id').value = entry.model_id || '';
    document.getElementById('mp-modal-native-api-key').value = '';
    updateNativeModelHints();
  } else {
    document.getElementById('mp-modal-provider').value = entry?.provider || '9router';
    document.getElementById('mp-modal-model-id').value = entry?.model_id || '';
    document.getElementById('mp-modal-base-url').value = entry?.base_url || '';
    document.getElementById('mp-modal-api-key').value = '';
  }

  document.getElementById('mp-modal-category').value = entry?.category || 'general';
  document.getElementById('mp-modal-max-req').value = entry?.max_requests_per_day || 0;
  document.getElementById('mp-modal-max-tok').value = entry?.max_tokens_per_day || 0;
  document.getElementById('mp-modal-price-in').value = entry?.price_input_per_1m || 0;
  document.getElementById('mp-modal-price-cache').value = entry?.price_cache_per_1m || 0;
  document.getElementById('mp-modal-price-out').value = entry?.price_output_per_1m || 0;
  document.getElementById('mp-modal-currency').value = entry?.currency || 'USD';
  document.getElementById('model-pool-modal').classList.remove('hidden');
}

export async function saveModel() {
  const id = document.getElementById('mp-modal-id').value;
  let conn;
  if (_modalActiveTab === 'cli') {
    const e = document.getElementById('mp-modal-cli-engine').value;
    conn = {
      provider: CLI_PROVIDER_LABELS[e],
      api_style: e,
      model_id: document.getElementById('mp-modal-cli-model-id').value.trim(),
      // CLI xác thực bằng thư mục tài khoản, không có endpoint/key nào.
      base_url: '',
      api_key: '',
      cli_config_dir: document.getElementById('mp-modal-cli-config-dir').value.trim(),
    };
  } else if (_modalActiveTab === 'native') {
    const p = document.getElementById('mp-modal-native-provider').value;
    conn = {
      provider: NATIVE_PROVIDER_LABELS[p],
      api_style: NATIVE_API_STYLES[p],
      model_id: document.getElementById('mp-modal-native-model-id').value.trim(),
      base_url: NATIVE_BASE_URLS[p],
      api_key: document.getElementById('mp-modal-native-api-key').value,
    };
  } else {
    conn = {
      provider: document.getElementById('mp-modal-provider').value.trim() || '9router',
      api_style: 'openai_compat',
      model_id: document.getElementById('mp-modal-model-id').value.trim(),
      base_url: document.getElementById('mp-modal-base-url').value.trim(),
      api_key: document.getElementById('mp-modal-api-key').value,
    };
  }
  const body = {
    name: document.getElementById('mp-modal-name').value.trim(),
    ...conn,
    category: document.getElementById('mp-modal-category').value,
    max_requests_per_day: parseInt(document.getElementById('mp-modal-max-req').value)||0,
    max_tokens_per_day: parseInt(document.getElementById('mp-modal-max-tok').value)||0,
    price_input_per_1m: parseFloat(document.getElementById('mp-modal-price-in').value)||0,
    price_cache_per_1m: parseFloat(document.getElementById('mp-modal-price-cache').value)||0,
    price_output_per_1m: parseFloat(document.getElementById('mp-modal-price-out').value)||0,
    currency: document.getElementById('mp-modal-currency').value || 'USD',
  };
  if (!body.name || !body.model_id) return showToast('Tên và Model ID là bắt buộc', 'error');
  if (id) {
    if (!body.api_key) delete body.api_key;
    await api('PATCH', `/model-pool/${id}`, body);
  } else {
    await api('POST', '/model-pool', body);
  }
  closeModal('model-pool-modal');
  await loadModelPool();
  if (id && currentModelId == id) _renderLimitBars(body.max_requests_per_day, body.max_tokens_per_day);
}

export async function deleteModel(id) {
  if (!id) return;
  if (!(await showConfirm('Xoá model này?'))) return;
  await api('DELETE', `/model-pool/${id}`);
  currentModelId = null;
  document.getElementById('mp-empty').style.display = '';
  document.getElementById('mp-detail').style.display = 'none';
  await loadModelPool();
}

export async function testModel(id) {
  const btn = document.getElementById('mp-test-btn');
  if (!btn) return;
  btn.textContent = '⏳ Đang test...';
  btn.style.color = '';
  btn.disabled = true;
  try {
    const res = await api('POST', `/model-pool/${id}/test`);
    if (res.ok) {
      btn.innerHTML = icon('check') + ' Kết nối tốt';
      btn.style.color = 'var(--status-on)';
    } else {
      btn.innerHTML = icon('close') + ' Không kết nối được';
      btn.style.color = 'var(--red)';
      showToast('Không kết nối được tới model: ' + (res.error || 'lỗi không rõ nguyên nhân'), 'error');
    }
  } catch (e) {
    btn.innerHTML = icon('close') + ' Có lỗi xảy ra';
    btn.style.color = 'var(--red)';
    showToast('Không kết nối được tới server: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    setTimeout(() => { btn.innerHTML = icon('plug') + ' Kiểm tra kết nối'; btn.style.color = ''; }, 5000);
  }
}

export function _fmtNum(n) {
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
  if (n >= 1000)    return (n/1000).toFixed(1) + 'K';
  return String(n);
}

// ════════════════════════════════════════
