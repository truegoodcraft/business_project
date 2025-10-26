let _token = null;

export async function ensureToken() {
  if (_token) return _token;
  const response = await fetch("/session/token", { credentials: "same-origin" });
  if (!response.ok) throw new Error(`token fetch failed: ${response.status}`);
  const payload = await response.json().catch(() => ({}));
  const token = typeof payload?.token === "string" ? payload.token : null;
  if (!token) throw new Error("no token in response");
  _token = token;
  return _token;
}

function isSerializableBody(body) {
  if (body === undefined || body === null) return false;
  if (typeof body === "string") return false;
  if (typeof FormData !== "undefined" && body instanceof FormData) return false;
  if (typeof Blob !== "undefined" && body instanceof Blob) return false;
  if (typeof ArrayBuffer !== "undefined" && body instanceof ArrayBuffer) return false;
  if (typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams) return false;
  if (typeof ReadableStream !== "undefined" && body instanceof ReadableStream) return false;
  if (ArrayBuffer.isView(body)) return false;
  return typeof body === "object";
}

async function parseResponse(response, method) {
  const contentType = response.headers?.get?.("content-type") || "";
  if (response.status === 204 || method === "HEAD") {
    return {};
  }
  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch (err) {
      if (response.ok) return {};
      return { error: err instanceof Error ? err.message : String(err) };
    }
  }
  try {
    return await response.text();
  } catch (err) {
    return response.ok ? "" : { error: err instanceof Error ? err.message : String(err) };
  }
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
    const refreshed = await ensureToken();
    init.headers["X-Session-Token"] = refreshed;
    res = await fetch(path, init);
  }
  return res;
}

export async function apiCall(path, { method = "GET", body, headers = {}, ...rest } = {}) {
  const init = Object.assign({}, rest, { method, headers: Object.assign({}, headers) });
  if (body !== undefined) {
    if (isSerializableBody(body)) {
      if (!init.headers["Content-Type"]) {
        init.headers["Content-Type"] = "application/json";
      }
      init.body = JSON.stringify(body);
    } else {
      init.body = body;
    }
  }
  const response = await _withAuth(path, init);
  const payload = await parseResponse(response, method);
  if (!response.ok) {
    const message = typeof payload === "string" && payload
      ? payload
      : typeof payload === "object" && payload !== null && (payload.error || payload.detail)
      ? String(payload.error || payload.detail)
      : `Request failed: ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

export function get(path, opts) {
  return apiCall(path, Object.assign({ method: "GET" }, opts));
}

export function post(path, body, opts = {}) {
  return apiCall(path, Object.assign({ method: "POST", body }, opts));
}

export function put(path, body, opts = {}) {
  return apiCall(path, Object.assign({ method: "PUT", body }, opts));
}

export function del(path, opts = {}) {
  return apiCall(path, Object.assign({ method: "DELETE" }, opts));
}

export function apiGet(path, opts) {
  return get(path, opts);
}

export function apiPost(path, body, opts) {
  return post(path, body, opts);
}
