(function(){
  function init(){
    const api = (window.busApi && window.busApi.apiPost) || window.apiPost;
    if (typeof api !== 'function') return;

    async function mountBackup(root){
      if(!root) return;
      root.innerHTML = `
        <h2>Backup / Sync</h2>
        <div class="row"><button id="exp">Export encrypted backup</button></div>
        <div class="row"><input id="path" placeholder="Full path to .tgc" style="min-width:480px"></div>
        <div class="row"><button id="pv">Preview Import</button><button id="cm" disabled>Commit Import</button></div>
        <pre id="out" class="muted" style="margin-top:8px"></pre>
      `;
      const $ = s => root.querySelector(s);
      const out = $('#out');

      $('#exp').addEventListener('click', async ()=>{
        const pwd = prompt('Enter export password'); if(!pwd) return;
        try { const res = await api('/app/export', { password: pwd }); out.textContent = JSON.stringify(res, null, 2); }
        catch(e){ out.textContent = 'Error: ' + (e.message || e); }
      });

      $('#pv').addEventListener('click', async ()=>{
        const pwd = prompt('Enter import password'); if(!pwd) return;
        const p = $('#path').value.trim(); if(!p){ alert('Missing .tgc path'); return; }
        try {
          const res = await api('/app/import/preview', { path: p, password: pwd });
          out.textContent = JSON.stringify(res, null, 2);
          const ok = !!(res && res.ok && !res.incompatible);
          $('#cm').disabled = !ok;
          $('#cm')._pwd = ok ? pwd : null; // transient only
        } catch(e){ out.textContent = 'Error: ' + (e.message || e); }
      });

      $('#cm').addEventListener('click', async ()=>{
        const p = $('#path').value.trim(); if(!p){ alert('Missing .tgc path'); return; }
        const pwd = $('#cm')._pwd; if(!pwd){ alert('Preview first or incompatible'); return; }
        try { const res = await api('/app/import/commit', { path: p, password: pwd }); out.textContent = JSON.stringify(res, null, 2); }
        catch(e){ out.textContent = 'Error: ' + (e.message || e); }
      });
    }

    window.busCards = window.busCards || {};
    window.busCards.mountBackup = mountBackup;
  }
  if (localStorage.getItem('BUS_SESSION_TOKEN')) init();
  else window.addEventListener('bus:token-ready', init, { once: true });
})();
