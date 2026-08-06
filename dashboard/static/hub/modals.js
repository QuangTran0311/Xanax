import { icon } from './icons.js';

// Modals
// ════════════════════════════════════════
export function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}
document.querySelectorAll('.modal-overlay').forEach(m => {
  m.addEventListener('click', e => { if (e.target === m) m.classList.add('hidden'); });
});

// ── Confirm popup (thay cho confirm() mặc định của trình duyệt) ─────────────
let _confirmResolve = null;
export function showConfirm(message, okLabel) {
  return new Promise(resolve => {
    _confirmResolve = resolve;
    document.getElementById('confirm-modal-body').textContent = message;
    document.getElementById('confirm-modal-ok').textContent = okLabel || 'Xoá';
    document.getElementById('confirm-modal').classList.remove('hidden');
  });
}
export function _answerConfirm(result) {
  document.getElementById('confirm-modal').classList.add('hidden');
  if (_confirmResolve) { _confirmResolve(result); _confirmResolve = null; }
}

// ── Toast (thay cho alert() mặc định) ───────────────────────────────────────
export function showToast(message, type) {
  type = type || 'info';
  const container = document.getElementById('toast-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  const iconSvg = icon(type === 'error' ? 'warning' : type === 'success' ? 'check' : 'info');
  el.innerHTML = `<span class="toast-icon">${iconSvg}</span><span class="toast-msg"></span><button class="toast-close" onclick="this.parentElement.remove()">${icon('close')}</button>`;
  el.querySelector('.toast-msg').textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 6000);
}

// ════════════════════════════════════════
