const TOKEN_KEY = "BUS_SESSION_TOKEN";
let tokenPromise = null;
let licensePromise = null;
let cachedLicense = null;

function normalizePath(path){
  if (!path) return "/";
  return path.startsWith("/") ? path : `/${path}`;
}

async function ensureToken(){
  if (cachedToken()) {
    return cachedToken();
  }
  if (!tokenPromise) {
    tokenPromise = fetch("/session/token", { credentials: "include" })
      .then(async response => {
        if (!response.ok) {
          throw new Error(`Token fetch failed: ${response.status}`);
        }
        const payload = await response.json();
        const token = payload && typeof payload.token === "string" ? payload.token : "";
        if (!token) {
          throw new Error("Token missing from response");
        }
        localStorage.setItem(TOKEN_KEY, token);
        return token;
      })
      .catch(error => {
        tokenPromise = null;
        throw error;
      });
  }
  return tokenPromise;
}

function cachedToken(){
  const token = localStorage.getItem(TOKEN_KEY);
  return token && token.trim() ? token : null;
}

async function request(method, path, body){
  const token = cachedToken() || await ensureToken();
  const headers = new Headers({
    "X-Plugin-Name": "ui",
    "Accept": "application/json",
  });
  if (token) {
    headers.set("X-Session-Token", token);
  }
  let payload = undefined;
  if (body !== undefined && body !== null) {
    headers.set("Content-Type", "application/json");
    payload = JSON.stringify(body);
  }

  const response = await fetch(normalizePath(path), {
    method,
    headers,
    body: payload,
    credentials: "include",
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    const message = text ? `${response.status}: ${text}` : `HTTP ${response.status}`;
    throw new Error(message);
  }

  if (response.status === 204) {
    return {};
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

export async function apiGet(path){
  return request("GET", path);
}

export async function apiPost(path, body){
  return request("POST", path, body);
}

export async function getLicense(){
  if (cachedLicense) {
    return cachedLicense;
  }
  if (!licensePromise) {
    licensePromise = apiGet("/dev/license")
      .then(data => {
        cachedLicense = data;
        return data;
      })
      .catch(error => {
        licensePromise = null;
        throw error;
      });
  }
  return licensePromise;
}
