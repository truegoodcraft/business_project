// Gate card init on token readiness
(function(){
  function init(){
    if (!window.apiGet) {
      console.error('Card missing API helpers');
      return;
    }

    const busApi = window.busApi || {};
    const apiGet = busApi.apiGet || window.apiGet;
    const apiPost = busApi.apiPost || window.apiPost;
    if (typeof apiGet !== 'function' || typeof apiPost !== 'function') {
      console.error('Card missing API helpers');
      return;
    }

    async function mountWrites(root){
      if(!root) return;
      root.innerHTML='<label>Writes: <input type="checkbox" id="writes-toggle"></label><pre id="writes-out" class="muted" style="margin-top:8px"></pre>';
      const toggle=root.querySelector('#writes-toggle');
      const out=root.querySelector('#writes-out');

      async function refreshWrites(){
        try{
          const data=await apiGet('/dev/writes');
          toggle.checked=!!data?.enabled;
          out.textContent=JSON.stringify(data,null,2);
        }catch(error){
          out.textContent='Error: '+error.message;
        }
      }

      toggle.addEventListener('change',async()=>{
        try{
          const payload={enabled:toggle.checked};
          const data=await apiPost('/dev/writes',payload);
          out.textContent=JSON.stringify(data,null,2);
          await refreshWrites();
        }catch(error){
          out.textContent='Error: '+error.message;
        }
      });

      await refreshWrites();
    }

    window.busCards = window.busCards || {};
    window.busCards.mountWrites = mountWrites;

    if (!window.busUIRouterInitialized) {
      window.busUIRouterInitialized = true;
      const TOKEN_KEY = 'BUS_SESSION_TOKEN';

      const routes = {
        '/writes':    () => window.busCards.mountWrites,
        '/organizer': () => window.busCards.mountOrganizer,
        '/dev':       () => window.busCards.mountDev,
      };

      function currentRoute() {
        const h = location.hash || '#/writes';
        const key = h.startsWith('#') ? h.slice(1) : h;
        return routes[key] ? key : '/writes';
      }

      function setActive(hash) {
        document.querySelectorAll('.nav a').forEach(a=>a.classList.remove('active'));
        const id = 'nav-' + (hash.replace('#/','') || 'writes');
        const el = document.getElementById(id);
        if (el) el.classList.add('active');
      }

      async function render() {
        const view = document.getElementById('view');
        if (!view) return;
        const key = currentRoute();
        const resolver = routes[key] || routes['/writes'];
        const mount = resolver ? resolver() : null;
        view.innerHTML = '';
        const card = document.createElement('div');
        card.className = 'card';
        view.appendChild(card);
        setActive('#' + key);
        if (typeof mount !== 'function') {
          card.textContent = 'Loading…';
          return;
        }
        try {
          await Promise.resolve(mount(card));
        } catch (error) {
          card.textContent = 'Error: ' + (error && error.message ? error.message : error);
        }
      }

      async function updateLicense(){
        if (typeof window.apiGet !== 'function') return;
        try {
          const info = await window.apiGet('/health');
          const lic = document.getElementById('license');
          if (lic) {
            const tok = localStorage.getItem(TOKEN_KEY) || '';
            const pfx = tok ? tok.slice(0,6) + '…' : '—';
            lic.textContent = `Local-only · Core: ${info?.licenses?.core?.name || '—'} · v ${info?.version || '—'} · token ${pfx}`;
          }
        } catch (error) {
          console.warn('health fetch failed', error);
        }
      }

      window.busRender = render;
      window.busUpdateLicense = updateLicense;

      function ensureInitialRoute(){
        if (!window.busInitialRouteDispatched) {
          window.busInitialRouteDispatched = true;
          if (!location.hash) location.hash = '#/writes';
          window.dispatchEvent(new HashChangeEvent('hashchange'));
        }
      }

      window.addEventListener('hashchange', render);
      window.addEventListener('bus:token-ready', function(){
        Promise.resolve(updateLicense()).finally(ensureInitialRoute);
      });

      if (localStorage.getItem(TOKEN_KEY)) {
        Promise.resolve(updateLicense()).finally(ensureInitialRoute);
      }
    }
  }
  if (localStorage.getItem('BUS_SESSION_TOKEN')) init();
  else window.addEventListener('bus:token-ready', init, { once: true });
})();
