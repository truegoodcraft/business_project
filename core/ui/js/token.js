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
  return fetch(path, { method: 'GET', headers: authHeaders() });
}

export async function apiPost(path, body) {
  return fetch(path, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {})
  }).then(r => r.json());
}

export async function apiJson(path) {
  return fetch(path, { headers: authHeaders() }).then(r => r.json());
}
