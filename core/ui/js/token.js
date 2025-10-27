export function authHeaders() {
  const t = localStorage.getItem('bus.token');
  return t ? { 'X-Session-Token': t, 'Authorization': 'Bearer ' + t } : {};
}

export async function ensureToken() {
  let t = localStorage.getItem('bus.token');
  if (!t) {
    const r = await fetch('/session/token');
    if (!r.ok) throw new Error('token fetch failed: ' + r.status);
    const j = await r.json();
    t = j.token || j.value || j.session;
    if (!t) throw new Error('no token in response');
    localStorage.setItem('bus.token', String(t));
  }
  window.dispatchEvent(new CustomEvent('bus:token-ready', { detail: { token: t } }));
  return t;
}

export async function apiGet(path) {
  const r = await fetch(path, { headers: authHeaders() });
  if (r.status === 401) { localStorage.removeItem('bus.token'); await ensureToken(); return apiGet(path); }
  return r;
}

export async function apiJson(path) {
  const r = await apiGet(path);
  return r.json();
}

export async function apiPost(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body ?? {})
  });
  if (r.status === 401) { localStorage.removeItem('bus.token'); await ensureToken(); return apiPost(path, body); }
  return r;
}
