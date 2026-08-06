// API helpers
// ════════════════════════════════════════
export async function checkAuthOrRedirect() {
  try {
    const r = await fetch('/api/health');
    if (r.status === 401) { window.top.location.href = '/login'; return false; }
  } catch (_) {}
  return true;
}

// Heartbeat: tự động redirect về login khi server restart xóa session
setInterval(async () => {
  try {
    const r = await fetch('/api/auth/me');
    if (r.status === 401) window.top.location.href = '/login';
  } catch (_) { /* server đang down, bỏ qua */ }
}, 5000);

export async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch('/api' + path, opts);
  if (r.status === 401) { window.top.location.href = '/login'; return; }
  if (!r.ok) throw new Error(await r.text());
  if (r.status === 204) return null;
  return r.json();
}

// ════════════════════════════════════════
