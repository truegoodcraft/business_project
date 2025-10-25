// core/ui/js/token.js
(function(){
  const KEY = 'BUS_SESSION_TOKEN';
  const COOKIE = 'X-Session-Token';
  let fired = false;

  function setCookie(name, value){
    document.cookie = name + '=' + encodeURIComponent(value) + '; SameSite=Lax; Path=/';
  }

  async function getToken(){
    const r = await fetch('/session/token', { credentials: 'same-origin' });
    if (!r.ok) throw new Error('token http ' + r.status);
    const j = await r.json();
    if (!j || !j.token) throw new Error('token missing');
    return String(j.token);
  }

  async function bootstrap(){
    try {
      let tok = localStorage.getItem(KEY);
      if (!tok) {
        try { tok = await getToken(); }
        catch(e){ await new Promise(r=>setTimeout(r,300)); tok = await getToken(); }
        localStorage.setItem(KEY, tok);
      }
      setCookie(COOKIE, tok);
      if (!fired){ fired = true; window.dispatchEvent(new CustomEvent('bus:token-ready')); }
    } catch(e){
      console.error('token bootstrap failed', e);
      window.dispatchEvent(new CustomEvent('bus:auth-failed', { detail: { stage: 'bootstrap', error: String(e) } }));
    }
  }

  // Patch fetch to inject header for relative and same-origin absolute URLs
  const _fetch = window.fetch.bind(window);
  window.fetch = async function(input, init){
    const u = (typeof input === 'string') ? new URL(input, location.origin) : new URL(input.url, location.origin);
    const sameOrigin = (u.origin === location.origin);
    const headers = new Headers((init && init.headers) || (typeof input !== 'string' ? input.headers : undefined) || {});
    const tok = localStorage.getItem(KEY);
    if (sameOrigin && tok) headers.set('X-Session-Token', tok);
    return _fetch(input, Object.assign({}, init, { headers }));
  };

  document.addEventListener('DOMContentLoaded', bootstrap);
})();
