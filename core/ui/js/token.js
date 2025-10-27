export async function ensureToken() {
  let t = localStorage.getItem('bus.token');
  if (!t) {
    const r = await fetch('/session/token', { method: 'GET' });
    if (!r.ok) throw new Error('token fetch failed: ' + r.status);
    const j = await r.json();
    t = j.token;
    if (!t) throw new Error('no token in response');
    localStorage.setItem('bus.token', t);
  }
  return t;
}

export async function withAuth(init = {}) {
  const t = await ensureToken();
  const h = new Headers(init.headers || {});
  if (!h.has('X-Session-Token')) h.set('X-Session-Token', t);
  if (!h.has('Authorization'))   h.set('Authorization', `Bearer ${t}`);
  return { ...init, headers: h };
}

export async function apiGet(path) {
  const res = await fetch(path, await withAuth());
  if (res.status === 401) {
    localStorage.removeItem('bus.token');
    const retry = await fetch(path, await withAuth());
    return parse(retry);
  }
  return parse(res);
}

export async function apiPost(path, body) {
  const init = await withAuth({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const res = await fetch(path, init);
  if (res.status === 401) {
    localStorage.removeItem('bus.token');
    const retry = await fetch(path, await withAuth(init));
    return parse(retry);
  }
  return parse(res);
}

async function parse(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} ${res.statusText} :: ${text}`);
  }
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}
