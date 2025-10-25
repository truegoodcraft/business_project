/* Token bootstrap & fetch patch for FixKit (local-only) */

const STORAGE_KEY = 'BUS_SESSION_TOKEN';

function normalizeToken(v) {
  // Accept: plain string, {"token": "..."} object, or JSON stringified versions
  try {
    if (!v) return '';
    if (typeof v === 'string') {
      // if looks like JSON, try parse
      if (v.trim().startsWith('{')) {
        const j = JSON.parse(v);
        return typeof j === 'string' ? j : (j.token || '');
      }
      return v;
    }
    if (typeof v === 'object' && v !== null) {
      return v.token || '';
    }
  } catch {}
  return '';
}

export function getToken() {
  const raw = localStorage.getItem(STORAGE_KEY);
  return normalizeToken(raw);
}

async function fetchToken() {
  const resp = await fetch('/session/token', { cache: 'no-store' });
  if (!resp.ok) throw new Error('token_fetch_' + resp.status);
  const j = await resp.json();
  const tok = normalizeToken(j);
  if (!tok) throw new Error('invalid_token_payload');
  // persist only the plain string
  localStorage.setItem(STORAGE_KEY, tok);
  // set cookie for debug/compat
  document.cookie = 'X-Session-Token=' + encodeURIComponent(tok) + '; SameSite=Lax; Path=/';
  // notify app
  window.dispatchEvent(new CustomEvent('bus:token-ready', { detail: { token: tok } }));
  return tok;
}

function sameOrigin(u) {
  try { return new URL(u, location.origin).origin === location.origin; }
  catch { return false; }
}

// Patch fetch once to inject X-Session-Token on same-origin URLs (relative or absolute)
if (!window.__BUS_FETCH_PATCHED__) {
  const _fetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    let url, headers;
    if (typeof input === 'string') {
      url = input;
      if (sameOrigin(url)) headers = new Headers((init && init.headers) || {});
    } else if (input instanceof Request) {
      url = input.url;
      if (sameOrigin(url)) headers = new Headers(input.headers);
    }
    if (headers) {
      const t = getToken();
      if (t) headers.set('X-Session-Token', t);
      if (input instanceof Request) input = new Request(input, { headers });
      else init = Object.assign({}, init, { headers });
    }
    return _fetch(input, init);
  };
  window.__BUS_FETCH_PATCHED__ = true;
}

// Kick off token load ASAP; renderers can listen for 'bus:token-ready'
(async () => {
  try {
    if (!getToken()) await fetchToken();
    else window.dispatchEvent(new CustomEvent('bus:token-ready', { detail: { token: getToken() } }));
  } catch (e) {
    console.error('Token bootstrap failed:', e);
  }
})();
