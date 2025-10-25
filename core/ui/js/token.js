export const Token = (()=> {
  function readCookie(name){
    const m = document.cookie.match(new RegExp('(?:^|; )'+name.replace(/([.$?*|{}()[\\]\\/+^])/g,'\\\\$1')+'=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }
  async function ensure(){
    let t = window.BUS_SESSION_TOKEN || localStorage.getItem('BUS_SESSION_TOKEN') || readCookie('X-Session-Token') || '';
    if (!t) {
      try {
        const r = await fetch('/session/token', {cache:'no-store'});
        const j = await r.json();
        t = j.token || '';
      } catch(e) {}
    }
    if (t){
      window.BUS_SESSION_TOKEN = t;
      localStorage.setItem('BUS_SESSION_TOKEN', t);
      document.cookie = 'X-Session-Token=' + encodeURIComponent(t) + '; SameSite=Lax; Path=/';
      document.dispatchEvent(new CustomEvent('bus:token-ready', {detail:{token:t}}));
    }
    return t;
  }
  // Patch fetch once
  if (!window.__fetchPatched){
    const _f = window.fetch;
    window.fetch = async (input, init)=>{
      init = init || {};
      const headers = new Headers(init.headers || {});
      const t = window.BUS_SESSION_TOKEN || localStorage.getItem('BUS_SESSION_TOKEN') || readCookie('X-Session-Token') || '';
      if (t && typeof input === 'string' && input.startsWith('/')) headers.set('X-Session-Token', t);
      init.headers = headers;
      return _f(input, init);
    };
    window.__fetchPatched = true;
  }
  ensure(); // kick off
  return { ensure };
})();
