// SPDX-License-Identifier: AGPL-3.0-or-later
// TGC BUS Core (Business Utility System Core)

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

function dispatchError(type, message, status) {
  window.dispatchEvent(new CustomEvent('bus-error', {
    detail: { type, message, status }
  }));
}

async function handleResponse(response) {
  const body = await parseBody(response);
  if (response.ok) {
    return body;
  }

  // Dispatch error (5xx or operational)
  if (response.status >= 500) {
    dispatchError('http', response.statusText || 'Server Error', response.status);
  }

  throw buildError(response.status, body, response.statusText);
}

// Wrapper for network error handling
async function safeRequest(url, init) {
  try {
    const response = await request(url, init);
    return await handleResponse(response);
  } catch (error) {
    if (!error.status) {
      // Network error probably
      dispatchError('network', error.message, 0);
    }
    throw error;
  }
}

export async function apiGet(url, init) {
  return safeRequest(url, { method: 'GET', ...(init || {}) });
}

export async function apiGetJson(url, init) {
  return apiGet(url, init);
}

function createJsonInit(method, data, init) {
  const headers = new Headers(init?.headers || {});
  headers.set('Content-Type', 'application/json');
  const body = data === undefined ? undefined : JSON.stringify(data ?? {});
  return { method, body, ...init, headers };
}

export async function apiPost(url, data, init) {
  return safeRequest(url, createJsonInit('POST', data, init));
}

export async function apiPut(url, data, init) {
  return safeRequest(url, createJsonInit('PUT', data, init));
}

export async function apiPatch(url, data, init) {
  return safeRequest(url, createJsonInit('PATCH', data, init));
}

export async function apiDelete(url, data, init) {
  const jsonInit = data === undefined ? { method: 'DELETE', ...(init || {}) } : createJsonInit('DELETE', data, init);
  return safeRequest(url, jsonInit);
}
