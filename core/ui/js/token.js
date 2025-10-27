export let BUS_TOKEN = null;

function loadCached() {
  const t = localStorage.getItem("bus.token");
  return t && t.length > 0 ? t : null;
}

export async function ensureToken(force = false) {
  if (!force) {
    if (BUS_TOKEN) return BUS_TOKEN;
    BUS_TOKEN = loadCached();
    if (BUS_TOKEN) return BUS_TOKEN;
  }
  const r = await fetch("/session/token", { method: "GET" });
  if (!r.ok) throw new Error("token fetch failed: " + r.status);
  const j = await r.json();
  BUS_TOKEN = j.token;
  localStorage.setItem("bus.token", BUS_TOKEN);
  window.dispatchEvent(new CustomEvent("bus:token-ready", { detail: { token: BUS_TOKEN } }));
  return BUS_TOKEN;
}

async function doFetch(path, opts = {}, retry = true) {
  const t = await ensureToken();
  const headers = new Headers(opts.headers || {});
  headers.set("X-Session-Token", t);
  headers.set("Authorization", `Bearer ${t}`);
  const res = await fetch(path, { ...opts, headers });
  if (res.status === 401 && retry) {
    await ensureToken(true);
    return doFetch(path, opts, false);
  }
  return res;
}

export async function apiGet(path) {
  const r = await doFetch(path, { method: "GET" });
  if (!r.ok) throw new Error(`${path} GET ${r.status}`);
  return r.json();
}

export async function apiPost(path, body) {
  const r = await doFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!r.ok) throw new Error(`${path} POST ${r.status}`);
  return r.json();
}
