import { api } from './api.js';
import { icon } from './icons.js';
import { esc } from './utils.js';

// ASSETS (Tài sản)
// ════════════════════════════════════════
let allAssets = [];
let assetsFilter = 'all';
const ASSET_SOURCE_LABEL = { all: 'Tất cả', upload: 'Đã upload', workflow: 'Quy trình', benchmark: 'Benchmark' };
const ASSET_ICON = { upload: 'document', workflow: 'settings', benchmark: 'flask' };

export async function loadAssets() {
  const data = await api('GET', '/assets/');
  allAssets = data.assets || [];
  renderAssetFilters();
  renderAssets();
}

function renderAssetFilters() {
  const el = document.getElementById('assets-filter-tabs');
  const counts = { all: allAssets.length };
  for (const a of allAssets) counts[a.source] = (counts[a.source] || 0) + 1;
  el.innerHTML = Object.keys(ASSET_SOURCE_LABEL).map(key => `
    <button class="assets-filter-btn${assetsFilter === key ? ' active' : ''}" onclick="setAssetsFilter('${key}')">
      ${ASSET_SOURCE_LABEL[key]} (${counts[key] || 0})
    </button>
  `).join('');
}

export function setAssetsFilter(key) {
  assetsFilter = key;
  renderAssetFilters();
  renderAssets();
}

function _formatBytes(n) {
  if (!n) return '';
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  return (n / (1024 * 1024)).toFixed(1) + ' MB';
}

function renderAssets() {
  const el = document.getElementById('assets-list');
  const items = assetsFilter === 'all' ? allAssets : allAssets.filter(a => a.source === assetsFilter);
  if (!items.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${icon('assets')}</div><div class="empty-state-text">Chưa có tài sản nào</div></div>`;
    return;
  }
  el.innerHTML = items.map(a => {
    const totalBytes = (a.files || []).reduce((s, f) => s + (f.size_bytes || 0), 0);
    return `
    <div class="asset-card">
      <div class="asset-card-top">
        <div class="asset-card-icon">${icon(ASSET_ICON[a.source] || 'document')}</div>
        <span class="asset-card-tag tag-${a.source}">${ASSET_SOURCE_LABEL[a.source] || a.source}</span>
      </div>
      <div class="asset-card-name">${esc(a.name)}</div>
      <div class="asset-card-meta">${a.label ? esc(a.label) + ' · ' : ''}${a.files.length} file${totalBytes ? ' · ' + _formatBytes(totalBytes) : ''} · ${esc((a.created_at || '').slice(0, 16))}</div>
      <div class="asset-card-files">
        ${a.files.map(f => `
          <a class="asset-file-row" href="${f.download_url}" target="_blank" rel="noopener" title="${esc(f.note || f.name)}">
            <span class="asset-file-name">${esc(f.name)}</span>
            <span class="asset-file-size">${_formatBytes(f.size_bytes)}</span>
          </a>
        `).join('')}
      </div>
      ${a.deletable ? `<div class="asset-card-actions"><span class="danger" onclick="deleteAssetItem('${a.id}')">Xoá</span></div>` : ''}
    </div>
  `;
  }).join('');
}

export async function deleteAssetItem(id) {
  if (!id.startsWith('upload-')) return;
  if (!confirm('Xoá file này?')) return;
  await api('DELETE', '/assets/' + id.replace('upload-', ''));
  await loadAssets();
}

async function uploadAssetFiles(fileList) {
  for (const file of fileList) {
    const form = new FormData();
    form.append('file', file);
    const r = await fetch('/api/assets/upload', { method: 'POST', body: form });
    if (r.status === 401) { window.top.location.href = '/login'; return; }
    if (!r.ok) { alert('Upload thất bại: ' + file.name); continue; }
  }
  await loadAssets();
}

(function initAssetsDropzone() {
  document.addEventListener('DOMContentLoaded', () => {
    const zone = document.getElementById('assets-dropzone');
    const input = document.getElementById('assets-file-input');
    if (!zone || !input) return;
    input.addEventListener('change', () => { if (input.files.length) uploadAssetFiles(input.files); input.value = ''; });
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      if (e.dataTransfer.files.length) uploadAssetFiles(e.dataTransfer.files);
    });
  });
})();

// ════════════════════════════════════════
