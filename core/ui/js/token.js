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

// --- single-auth helpers: atomic token + retry on 401 ---

let _tokenCache = null;        // string | null
let _tokenPromise = null;      // Promise<string> | null

export async function ensureToken() {
  if (_tokenCache) return _tokenCache;
  if (_tokenPromise) return _tokenPromise; // in-flight, await it

  _tokenPromise = (async () => {
    // FIX: 'omit' -> 'same-origin' to allow Set-Cookie to work
    const r = await fetch('/session/token', { credentials: 'same-origin' });
    if (!r.ok) throw new Error(`token fetch failed: ${r.status}`);
    const j = await r.json();
    _tokenCache = j.token;
    _tokenPromise = null;
    return _tokenCache;
  })();

  return _tokenPromise;
}

function clearToken() {
  _tokenCache = null;
  _tokenPromise = null;
}

async function withAuth(init = {}) {
  // Ensure we have established the session (and planted the cookie)
  await ensureToken();

  const headers = new Headers(init.headers || {});
  // REMOVED: X-Session-Token header (Backend is cookie-only now)

  // FIX: 'same-origin' ensures the browser sends the cookie
  return { ...init, headers, credentials: 'same-origin' };
}

export async function request(url, init) {
  // first attempt
  let resp = await fetch(url, await withAuth(init || {}));
  if (resp.status !== 401) return resp;

  // single retry path: refresh token and resend
  clearToken();
  await ensureToken();
  resp = await fetch(url, await withAuth(init || {}));
  return resp;
}

// Convenience wrappers. Keep signatures stable.
export const apiGet  = (url, init) => request(url, { method: 'GET', ...(init || {}) });
export const apiPost = (url, body, init) => request(url, { method: 'POST', body, ...(init || {}) });
export const apiJson = (url, obj, init) =>
  request(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(obj || {}),
    ...(init || {})
  });

export const apiGetJson = async (url, init) => {
  const r = await apiGet(url, init);
  return r.json();
};

// --- end single-auth helpers ---

export const apiJsonJson = (url, obj, init) => apiJson(url, obj, init).then(res => res.json());
