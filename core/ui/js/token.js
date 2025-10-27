const TOKEN_KEY = 'bus.token';

async function fetchToken() {
  const r = await fetch('/session/token', { method: 'GET' });
  if (!r.ok) throw new Error('token fetch failed: ' + r.status);
  const j = await r.json();
  const t = j.token || j.value || j.id;
  if (!t) throw new Error('no token field in response');
  localStorage.setItem(TOKEN_KEY, t);   // store RAW string
  return t;
}

export async function ensureToken() {
  let t = localStorage.getItem(TOKEN_KEY);
  if (!t || t.startsWith('{')) {        // purge legacy bad value
    localStorage.removeItem(TOKEN_KEY);
    t = await fetchToken();
  }
  return t;
}

export async function request(path, opts = {}) {
  const t = await ensureToken();
  const h = opts.headers ? { ...opts.headers } : {};
  h['X-Session-Token'] = t;
  h['Authorization']   = `Bearer ${t}`;
  if (opts.body && !h['Content-Type']) h['Content-Type'] = 'application/json';
  return fetch(path, { ...opts, headers: h, credentials: 'same-origin' });
}

export async function apiGet(path) {
  let r = await request(path, { method: 'GET' });
  if (r.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    await ensureToken();
    r = await request(path, { method: 'GET' });
  }
  if (!r.ok) throw new Error(`${path} ${r.status}`);
  return r.json();
}

export async function apiPost(path, body) {
  let r = await request(path, { method: 'POST', body: body ? JSON.stringify(body) : '{}' });
  if (r.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    await ensureToken();
    r = await request(path, { method: 'POST', body: body ? JSON.stringify(body) : '{}' });
  }
  if (!r.ok) throw new Error(`${path} ${r.status}`);
  return r.json();
}

export function currentToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}
