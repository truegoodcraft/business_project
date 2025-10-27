// ESM token + API helpers
const KEY = "bus.session.token";
const TTL_MS = 1000 * 60 * 30; // 30 min soft TTL

function now(){ return Date.now(); }

function readCache(){
  try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch { return null; }
}

function writeCache(obj){
  try { localStorage.setItem(KEY, JSON.stringify(obj)); } catch {}
}

async function fetchToken(){
  // prefer POST; fall back to GET
  let r = await fetch("/session/token", { method:"POST" });
  if (r.status === 405 || r.status === 404) r = await fetch("/session/token");
  if (!r.ok) throw new Error(`token ${r.status}`);
  const data = await r.json();               // expect { token: "..." }
  const token = data.token || data.session || data.id || "";
  if (!token) throw new Error("empty token");
  const entry = { token, ts: now() };
  writeCache(entry);
  return token;
}

export async function ensureToken(force=false){
  const cached = readCache();
  if (!force && cached && cached.token && (now() - (cached.ts||0) < TTL_MS)) {
    return cached.token;
  }
  const t = await fetchToken();
  // notify listeners once per refresh
  try { window.dispatchEvent(new CustomEvent("bus:token-ready", { detail: { token: t } })); } catch {}
  return t;
}

async function withToken(init={}){
  const { force, ...rest } = init;
  const t = await ensureToken(force);
  const headers = new Headers(rest.headers || {});
  headers.set("X-Session-Token", t);
  headers.set("Authorization", `Bearer ${t}`);
  return { ...rest, headers };
}

export async function apiGet(path){
  const r = await fetch(path, await withToken({ method:"GET" }));
  if (r.status === 401) { // one retry on forced refresh
    const rr = await fetch(path, await withToken({ method:"GET", headers:{} , force:true }));
    return rr.ok ? rr.json() : Promise.reject(await rr.json().catch(()=>({status:rr.status})));
  }
  return r.ok ? r.json() : Promise.reject(await r.json().catch(()=>({status:r.status})));
}

export async function apiPost(path, body){
  const r = await fetch(path, await withToken({
    method:"POST",
    headers:{ "Content-Type":"application/json" },
    body: JSON.stringify(body||{})
  }));
  if (r.status === 401) {
    const rr = await fetch(path, await withToken({
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(body||{}),
      force:true
    }));
    return rr.ok ? rr.json() : Promise.reject(await rr.json().catch(()=>({status:rr.status})));
  }
  return r.ok ? r.json() : Promise.reject(await r.json().catch(()=>({status:r.status})));
}

export function clearToken(){ localStorage.removeItem(KEY); }
