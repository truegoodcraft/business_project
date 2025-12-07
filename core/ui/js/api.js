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
import { parseApiError } from './utils/parser.js';

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

function logError(message, url, payload) {
  // SoT §5.4.7 Console Logging Standard
  console.error(`BUSCORE_ERROR: ${message}, endpoint=${url}, payload=`, payload);
}

function showErrorBanner(msg) {
  const banner = document.getElementById('error-banner');
  if (banner) {
    banner.textContent = msg;
    banner.classList.remove('hidden');
  } else {
    console.error('CRITICAL UI ERROR: Missing #error-banner container.');
    // Fallback alerts are annoying but better than silent failure if banner is missing
    // But per instructions we expect the banner.
  }
}

async function handleResponse(response, url, payload) {
  const body = await parseBody(response);

  if (response.ok) {
    return body;
  }

  // Unified Error Parsing
  const parsed = parseApiError(body);
  const msg = parsed.message;

  logError(msg, url, payload);

  // 400 Bad Request (and 422 Validation)
  if (response.status === 400 || response.status === 422) {
    const err = new Error(msg);
    err.status = response.status;
    err.fields = parsed.fields;
    err.detail = msg;
    // Contract: Do not close dialog. Display error inside form/toast.
    // We throw so the caller (form handler) receives it.
    throw err;
  }

  // 401/403 Auth
  if (response.status === 401 || response.status === 403) {
    // Redirect to login or show Session Expired
    window.location.hash = '/login';
    throw new Error('Session Expired');
  }

  // 5xx / Network (Operational)
  if (response.status >= 500) {
    const bannerMsg = "An unexpected error occurred. No changes were made.";
    showErrorBanner(bannerMsg);
    throw new Error(bannerMsg);
  }

  // Fallback
  throw new Error(msg);
}

function createJsonInit(method, data, init) {
  const headers = new Headers(init?.headers || {});
  headers.set('Content-Type', 'application/json');
  const body = data === undefined ? undefined : JSON.stringify(data ?? {});
  return { method, body, ...init, headers };
}

async function execRequest(method, url, data, init) {
  let response;
  const jsonInit = (method === 'GET' || (method === 'DELETE' && data === undefined))
    ? { method, ...(init || {}) }
    : createJsonInit(method, data, init);

  try {
    response = await request(url, jsonInit);
  } catch (err) {
    // Network Error (fetch failed)
    const msg = "Request timed out. Check server status.";
    logError(err.message, url, data);
    showErrorBanner(msg);
    throw new Error(msg);
  }

  return handleResponse(response, url, data);
}

export async function apiGet(url, init) {
  return execRequest('GET', url, undefined, init);
}

export async function apiGetJson(url, init) {
  return apiGet(url, init);
}

export async function apiPost(url, data, init) {
  return execRequest('POST', url, data, init);
}

export async function apiPut(url, data, init) {
  return execRequest('PUT', url, data, init);
}

export async function apiPatch(url, data, init) {
  return execRequest('PATCH', url, data, init);
}

export async function apiDelete(url, data, init) {
  return execRequest('DELETE', url, data, init);
}
