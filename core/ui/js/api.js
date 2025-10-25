// core/ui/js/api.js
(function(){
  const KEY = 'BUS_SESSION_TOKEN';
  let refreshPromise = null;

  async function refreshToken(){
    if (refreshPromise) return refreshPromise;
    refreshPromise = (async () => {
      const r = await fetch('/session/token', { credentials: 'same-origin' });
      if (!r.ok) throw new Error('refresh http ' + r.status);
      const j = await r.json();
      if (!j || !j.token) throw new Error('refresh missing token');
      const tok = String(j.token);
      localStorage.setItem(KEY, tok);
      document.cookie = 'X-Session-Token=' + encodeURIComponent(tok) + '; SameSite=Lax; Path=/';
      return tok;
    })();
    try {
      return await refreshPromise;
    } finally {
      refreshPromise = null; // clear after completion to avoid cycles
    }
  }

  async function doFetch(method, url, body){
    const init = { method, headers: { 'Accept': 'application/json' } };
    if (body !== undefined){ init.body = JSON.stringify(body); init.headers['Content-Type'] = 'application/json'; }

    let resp = await fetch(url, init);
    if (resp.status === 401){
      try { await refreshToken(); }
      catch(e){ window.dispatchEvent(new CustomEvent('bus:auth-failed', { detail: { stage: 'refresh', error: String(e) } })); throw e; }
      resp = await fetch(url, init);
    }
    if (!resp.ok) {
      const text = await resp.text().catch(()=>String(resp.status));
      throw new Error('HTTP ' + resp.status + ' ' + text);
    }
    const ct = resp.headers.get('Content-Type') || '';
    return ct.includes('application/json') ? resp.json() : resp.text();
  }

  function apiGet(u){ return doFetch('GET', u); }
  function apiPost(u,b){ return doFetch('POST', u, b); }
  function apiPut(u,b){ return doFetch('PUT', u, b); }
  function apiDel(u){ return doFetch('DELETE', u); }

  // global helpers expected by cards
  window.apiGet = apiGet; window.apiPost = apiPost; window.apiPut = apiPut; window.apiDel = apiDel;
  window.busApi = { apiGet, apiPost, apiPut, apiDel };
})();
