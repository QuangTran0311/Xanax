import { api } from './api.js';

// Logout / Auth
// ════════════════════════════════════════
export async function logout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.top.location.href = '/login';
}

// ════════════════════════════════════════
