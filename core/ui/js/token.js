let TOKEN = null, LICENSE = null, LP = null;

async function ensureToken(){
  if (TOKEN) return TOKEN;
  const r = await fetch("/session/token", { credentials: "include" });
  if (!r.ok) throw new Error("Token fetch failed");
  const j = await r.json(); TOKEN = j && j.token || ""; return TOKEN;
}

function norm(path){ return path && path.startsWith("/") ? path : `/${path||""}`; }

async function request(method, path, body){
  const t = await ensureToken();
  const headers = new Headers({ "X-Session-Token": t, "X-Plugin-Name": "ui", "Accept": "application/json" });
  let payload; if (body !== undefined) { headers.set("Content-Type","application/json"); payload = JSON.stringify(body); }
  const res = await fetch(norm(path), { method, headers, body: payload, credentials: "include" });
  if (!res.ok){ const txt = await res.text().catch(()=> ""); throw new Error(txt || `HTTP ${res.status}`); }
  if (res.status === 204) return {};
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

export async function apiGet(p){ return request("GET", p); }
export async function apiPost(p,b){ return request("POST", p, b); }
export async function getLicense(){
  if (LICENSE) return LICENSE;
  if (!LP) LP = apiGet("/dev/license").then(d => (LICENSE = d));
  return LP;
}
