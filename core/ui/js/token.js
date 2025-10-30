// core/ui/js/token.js
let inflight = null;

export async function ensureToken() {
  const cached = localStorage.getItem('bus.token');
  if (cached) return cached;
  if (!inflight) {
    inflight = fetch('/session/token')
      .then(r => {
        if (!r.ok) throw new Error('token fetch failed: ' + r.status);
        return r.json();
      })
      .then(j => {
        if (!j?.token) throw new Error('token missing');
        localStorage.setItem('bus.token', j.token);
        window.dispatchEvent(new CustomEvent('bus:token-ready', { detail: { token: j.token } }));
        return j.token;
      })
      .finally(() => { inflight = null; });
  }
  return inflight;
}

export async function request(input, init = {}) {
  const token = await ensureToken();
  const headers = new Headers(init.headers || {});
  headers.set('X-Session-Token', token);
  const res = await fetch(input, { ...init, headers });
  if (res.status === 401) {
    localStorage.removeItem('bus.token');
    const t2 = await ensureToken();
    headers.set('X-Session-Token', t2);
    return fetch(input, { ...init, headers });
  }
  return res;
}

export const apiGet  = (url, init) => request(url, { method: 'GET', ...(init || {}) });
export const apiPost = (url, body, init) => request(url, { method: 'POST', body, ...(init || {}) });
export const apiJson = (url, obj, init) => request(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(obj || {}),
  ...(init || {})
});
export const apiGetJson = (url, init) => apiGet(url, init).then(res => res.json());
export const apiJsonJson = (url, obj, init) => apiJson(url, obj, init).then(res => res.json());
