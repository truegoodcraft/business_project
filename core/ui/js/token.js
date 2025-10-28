// core/ui/js/token.js
const KEY = 'bus.token';

export function authHeaders() {
  const t = localStorage.getItem(KEY);
  return t ? { 'X-Session-Token': t, 'Authorization': `Bearer ${t}` } : {};
}

export async function ensureToken() {
  let t = localStorage.getItem(KEY);
  if (!t) {
    const r = await fetch('/session/token');
    if (!r.ok) throw new Error('token fetch failed: ' + r.status);
    const j = await r.json();
    t = j.token || j.value || j.session;
    if (!t) throw new Error('no token in response');
    localStorage.setItem(KEY, String(t));
  }
  window.dispatchEvent(new CustomEvent('bus:token-ready', { detail: { token: t } }));
  return t;
}

// Centralized request that always injects headers
export async function request(input, init = {}) {
  const t = localStorage.getItem(KEY) || await ensureToken();
  const headers = new Headers(init.headers || {});
  if (!headers.get('X-Session-Token')) headers.set('X-Session-Token', t);
  if (!headers.get('Authorization')) headers.set('Authorization', `Bearer ${t}`);
  return fetch(input, { ...init, headers });
}

// Convenience helpers (use request())
export async function apiGet(path) {
  return request(path, { method: 'GET' });
}
export async function apiPost(path, body) {
  const r = await request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {})
  });
  return r.json();
}
export async function apiJson(path) {
  const r = await request(path, { method: 'GET' });
  return r.json();
}
