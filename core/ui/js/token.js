let TOKEN = null;

async function ensureToken() {
  if (TOKEN) {
    return TOKEN;
  }
  const response = await fetch("/session/token", { credentials: "include" });
  if (!response.ok) {
    throw new Error("token fetch failed");
  }
  const payload = await response.json();
  const token = payload && payload.token;
  if (!token) {
    throw new Error("token fetch failed");
  }
  TOKEN = token;
  return TOKEN;
}

async function request(method, path, body) {
  const token = await ensureToken();
  const headers = new Headers({
    "X-Session-Token": token,
    "X-Plugin-Name": "ui",
    "Accept": "application/json",
  });
  if (body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  const url = path.startsWith("/") ? path : `/${path}`;
  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  if (response.status === 204) {
    return {};
  }
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

export async function apiGet(path) {
  return request("GET", path);
}

export async function apiPost(path, body) {
  return request("POST", path, body);
}

export async function getLicense() {
  return apiGet("/dev/license");
}
