// --- single-auth helpers: atomic token + retry on 401 ---

let _tokenCache = null;        // string | null
let _tokenPromise = null;      // Promise<string> | null

export async function ensureToken() {
  if (_tokenCache) return _tokenCache;
  if (_tokenPromise) return _tokenPromise; // in-flight, await it

  _tokenPromise = (async () => {
    const r = await fetch('/session/token', { credentials: 'omit' });
    if (!r.ok) throw new Error(`token fetch failed: ${r.status}`);
    const j = await r.json();
    _tokenCache = j.token;
    _tokenPromise = null;
    return _tokenCache;
  })();

  return _tokenPromise;
}

function clearToken() {
  _tokenCache = null;
  _tokenPromise = null;
}

async function withAuth(init = {}) {
  const t = await ensureToken();
  const headers = new Headers(init.headers || {});
  headers.set('X-Session-Token', t);      // single authority header
  return { ...init, headers, credentials: 'omit' };
}

export async function request(url, init) {
  // first attempt
  let resp = await fetch(url, await withAuth(init || {}));
  if (resp.status !== 401) return resp;

  // single retry path: refresh token and resend
  clearToken();
  await ensureToken();
  resp = await fetch(url, await withAuth(init || {}));
  return resp;
}

// Convenience wrappers. Keep signatures stable.
export const apiGet  = (url, init) => request(url, { method: 'GET', ...(init || {}) });
export const apiPost = (url, body, init) => request(url, { method: 'POST', body, ...(init || {}) });
export const apiJson = (url, obj, init) =>
  request(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(obj || {}),
    ...(init || {})
  });

export const apiGetJson = async (url, init) => {
  const r = await apiGet(url, init);
  return r.json();
};

// --- end single-auth helpers ---

export const apiJsonJson = (url, obj, init) => apiJson(url, obj, init).then(res => res.json());
