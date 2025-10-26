let _token = null;

export async function ensureToken() {
  if (_token) return _token;
  const r = await fetch("/session/token", { credentials: "same-origin" });
  if (!r.ok) throw new Error(`token fetch failed: ${r.status}`);
  const j = await r.json();
  const t = typeof j?.token === "string" ? j.token : null;
  if (!t) throw new Error("no token in response");
  _token = t;
  return _token;
}

async function _withAuth(path, opts = {}) {
  const token = await ensureToken();
  const headers = Object.assign({}, opts.headers || {}, {
    "X-Session-Token": token,
    "X-Plugin-Name": "ui",
  });
  const init = Object.assign({}, opts, { headers });
  let res = await fetch(path, init);
  if (res.status === 401) {
    _token = null; // force refresh
    const t2 = await ensureToken();
    init.headers["X-Session-Token"] = t2;
    res = await fetch(path, init);
  }
  return res;
}

export async function apiGet(path) {
  const res = await _withAuth(path);
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json();
}

export async function apiPost(path, body) {
  const res = await _withAuth(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : "{}",
  });
  if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
  return res.json();
}
