const COOKIE = 'X-Session-Token';
const STORE  = 'BUS_SESSION_TOKEN';

function setCookie(name, value) {
  document.cookie = name + '=' + encodeURIComponent(value) + '; SameSite=Lax; Path=/';
}
function getCookie(name) {
  const m = document.cookie.match(new RegExp('(?:^|; )'+name.replace(/([.$?*|{}()[\\]\\/+^])/g,'\\$1')+'=([^;]*)'));
  return m ? decodeURIComponent(m[1]) : '';
}
function setToken(t) {
  if (!t) return;
  window.BUS_SESSION_TOKEN = t;
  try { localStorage.setItem(STORE, t); } catch {}
  setCookie(COOKIE, t);
}
function getToken() {
  return window.BUS_SESSION_TOKEN
      || (typeof localStorage!=='undefined' && localStorage.getItem(STORE))
      || getCookie(COOKIE)
      || '';
}

async function fetchTokenOnce(abortMs=1500) {
  const ctl = new AbortController();
  const to = setTimeout(()=>ctl.abort('timeout'), abortMs);
  try {
    const r = await fetch('/session/token', {cache:'no-store', signal: ctl.signal});
    if (r.ok) {
      const j = await r.json();
      if (j && j.token) return j.token;
    }
  } catch(_) {}
  finally { clearTimeout(to); }
  return '';
}

async function ensure() {
  let t = getToken();
  if (!t) t = await fetchTokenOnce();
  if (t) setToken(t);
  // Always notify once; cards can enable buttons on this event
  document.dispatchEvent(new CustomEvent('bus:token-ready', { detail: { token: getToken() } }));
  return getToken();
}

// Patch fetch once – inject header for same-origin requests
if (!window.__fetchPatched) {
  const _f = window.fetch;
  window.fetch = async (input, init) => {
    init = init || {};
    const headers = new Headers(init.headers || {});
    const t = getToken();
    if (t && typeof input === 'string' && input.startsWith('/')) headers.set('X-Session-Token', t);
    init.headers = headers;
    return _f(input, init);
  };
  window.__fetchPatched = true;
}

ensure(); // kick off immediately

export const Token = { get: getToken, ensure };
