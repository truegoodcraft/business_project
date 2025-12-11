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

const API_BASE_PRIMARY = '/app';
const API_BASE_LEGACY = '/api';

function normalizePath(path) {
  if (/^https?:\/\//i.test(path)) return path;
  return path.startsWith('/') ? path : `/${path}`;
}

function buildPrimary(path) {
  const normalized = normalizePath(path);
  if (normalized.startsWith(API_BASE_PRIMARY)) return normalized;
  if (normalized.startsWith(API_BASE_LEGACY)) return normalized.replace(API_BASE_LEGACY, API_BASE_PRIMARY);
  return `${API_BASE_PRIMARY}${normalized}`;
}

function buildLegacy(path) {
  const normalized = normalizePath(path);
  if (normalized.startsWith(API_BASE_LEGACY)) return normalized;
  if (normalized.startsWith(API_BASE_PRIMARY)) return normalized.replace(API_BASE_PRIMARY, API_BASE_LEGACY);
  return `${API_BASE_LEGACY}${normalized}`;
}

async function requestWithFallback(path, init) {
  const primaryPath = buildPrimary(path);
  let response = await request(primaryPath, init);

  if (response.status === 404) {
    const legacyPath = buildLegacy(path);
    if (legacyPath !== primaryPath) {
      response = await request(legacyPath, init);
    }
  }

  return response;
}

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
    (body && typeof body === 'object' && (body.error || body.message || body.detail)) ||
    (typeof body === 'string' && body) ||
    statusText ||
    `Request failed with status ${status}`;
  const error = new Error(message);
  error.status = status;
  error.payload = body;
  error.data = body;
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
  const response = await requestWithFallback(url, { method: 'GET', ...(init || {}) });
  return handleResponse(response);
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
  const response = await requestWithFallback(url, createJsonInit('POST', data, init));
  return handleResponse(response);
}

export async function apiPut(url, data, init) {
  const response = await requestWithFallback(url, createJsonInit('PUT', data, init));
  return handleResponse(response);
}

export async function apiPatch(url, data, init) {
  const response = await requestWithFallback(url, createJsonInit('PATCH', data, init));
  return handleResponse(response);
}

export async function apiDelete(url, data, init) {
  const jsonInit = data === undefined ? { method: 'DELETE', ...(init || {}) } : createJsonInit('DELETE', data, init);
  const response = await requestWithFallback(url, jsonInit);
  return handleResponse(response);
}
