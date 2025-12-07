// SPDX-License-Identifier: AGPL-3.0-or-later
// TGC BUS Core (Business Utility System Core)
// Copyright (C) 2025 True Good Craft
//
// This file is part of TGC BUS Core.
//
// TGC BUS Core is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// TGC BUS Core is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

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

  // Dispatch error event
  const message = (body && typeof body === 'object' && (body.error || body.message)) || response.statusText;
  dispatchError('http', message, response.status);

  throw buildError(response.status, body, response.statusText);
}

// Wrapper to handle network errors
async function safeRequest(url, init) {
  try {
    const response = await request(url, init);
    return await handleResponse(response);
  } catch (error) {
    // If it's a network error (no status), dispatch it
    if (!error.status) {
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
