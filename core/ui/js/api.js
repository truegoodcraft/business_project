import { request, ensureToken } from './token.js';

export { ensureToken };

async function parseBody(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function buildError(status, body, statusText) {
  const message =
    (body && typeof body === 'object' && (body.error || body.message)) ||
    (typeof body === 'string' && body) ||
    statusText ||
    `Request failed with status ${status}`;
  const error = new Error(message);
  error.status = status;
  if (body && typeof body === 'object') {
    Object.assign(error, body);
  } else if (typeof body === 'string') {
    error.error = message;
  }
  return error;
}

async function handleResponse(response) {
  const body = await parseBody(response);
  if (response.ok) {
    return body;
  }
  throw buildError(response.status, body, response.statusText);
}

export async function apiGet(url, init) {
  const response = await request(url, { method: 'GET', ...(init || {}) });
  return handleResponse(response);
}

function createJsonInit(method, data, init) {
  const headers = new Headers(init?.headers || {});
  headers.set('Content-Type', 'application/json');
  const body = data === undefined ? undefined : JSON.stringify(data ?? {});
  return { method, body, ...init, headers };
}

export async function apiPost(url, data, init) {
  const response = await request(url, createJsonInit('POST', data, init));
  return handleResponse(response);
}

export async function apiPut(url, data, init) {
  const response = await request(url, createJsonInit('PUT', data, init));
  return handleResponse(response);
}

export async function apiDelete(url, data, init) {
  const jsonInit = data === undefined ? { method: 'DELETE', ...(init || {}) } : createJsonInit('DELETE', data, init);
  const response = await request(url, jsonInit);
  return handleResponse(response);
}
