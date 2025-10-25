const COOKIE='X-Session-Token', STORE='BUS_SESSION_TOKEN';
function setCookie(k,v){ document.cookie=k+'='+encodeURIComponent(v)+'; SameSite=Lax; Path=/'; }
function getCookie(k){ const m=document.cookie.match(new RegExp('(?:^|; )'+k.replace(/([.$?*|{}()[\\]\\/+^])/g,'\\$1')+'=([^;]*)')); return m?decodeURIComponent(m[1]):''; }
function setToken(t){ if(!t) return; window.BUS_SESSION_TOKEN=t; try{localStorage.setItem(STORE,t);}catch{} setCookie(COOKIE,t); }
function getToken(){ return window.BUS_SESSION_TOKEN || (typeof localStorage!=='undefined'&&localStorage.getItem(STORE)) || getCookie(COOKIE) || ''; }
async function fetchTokenOnce(ms=1500){ const ctl=new AbortController(); const to=setTimeout(()=>ctl.abort(),ms);
  try{ const r=await fetch('/session/token',{cache:'no-store',signal:ctl.signal}); if(r.ok){ const j=await r.json(); if(j?.token) return j.token; } }catch{} finally{ clearTimeout(to); }
  return ''; }
async function ensure(){ let t=getToken(); if(!t) t=await fetchTokenOnce(); if(t) setToken(t);
  document.dispatchEvent(new CustomEvent('bus:token-ready',{detail:{token:getToken()}})); return getToken(); }
if(!window.__fetchPatched){ const _f=window.fetch; window.fetch=async(i,n)=>{ n=n||{}; const h=new Headers(n.headers||{}); const t=getToken(); if(t&&typeof i==='string'&&i.startsWith('/')) h.set('X-Session-Token',t); n.headers=h; return _f(i,n); }; window.__fetchPatched=true; }
ensure();
export const Token={get:getToken,ensure};
