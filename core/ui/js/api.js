import { getToken } from '/ui/js/token.js';

const TOKEN_KEY = 'tgc_token';
const MAX_ATTEMPTS = 2;

function normalizeMethod(method = 'GET') {
  return method.toUpperCase();
}

function normalizeBody(method, body) {
  if (method === 'GET' || body == null || body instanceof FormData || body instanceof Blob) {
    return body;
  }
  if (typeof body === 'string') {
    return body;
  }
  return JSON.stringify(body);
}

async function ensureToken(forceRefresh = false) {
  const token = await getToken(forceRefresh);
  if (!token) {
    throw new Error('No token');
  }
  return token;
}

export async function apiCall(path, opts = {}) {
  const init = { ...opts };
  init.method = normalizeMethod(init.method);
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt += 1) {
    let token = '';
    try {
      token = localStorage.getItem(TOKEN_KEY) || '';
    } catch (err) {
      console.warn('[api] Unable to access localStorage', err);
    }

    if (!token) {
      console.warn('[api] Missing token, requesting…');
      token = await ensureToken(attempt > 0);
    }

    const headers = new Headers(init.headers || {});
    headers.set('X-Session-Token', token);
    if (init.method !== 'GET' && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const request = {
      ...init,
      headers,
    };

    if (init.method !== 'GET') {
      request.body = normalizeBody(init.method, init.body);
    }

    console.log('[api] Fetch', init.method, path);
    const response = await fetch(path, request);
    console.log('[api] Response', response.status, path);

    if (response.status === 401 && attempt === 0) {
      console.warn('[api] 401 received, refreshing token');
      try {
        localStorage.removeItem(TOKEN_KEY);
      } catch (err) {
        console.warn('[api] Failed clearing token', err);
      }
      await ensureToken(true);
      continue;
    }

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `HTTP ${response.status}`);
    }

    return init.method === 'GET' ? response.json() : response;
  }

  localStorage.removeItem(TOKEN_KEY);
  throw new Error('Token expired—reload');
}

export const get = (path, options = {}) => apiCall(path, { ...options, method: 'GET' });
export const post = (path, body, options = {}) => apiCall(path, { ...options, method: 'POST', body });
export const del = (path, options = {}) => apiCall(path, { ...options, method: 'DELETE' });
