// Ensure we wait for token
(function(){
  function init(){
    const busApi = window.busApi || {};
    const apiGet = busApi.apiGet || window.apiGet;
    const apiPost = busApi.apiPost || window.apiPost;
    if (typeof apiGet !== 'function' || typeof apiPost !== 'function') {
      console.error('Writes card missing API helpers');
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
  }
  if (localStorage.getItem('BUS_SESSION_TOKEN')) init();
  else window.addEventListener('bus:token-ready', init, { once: true });
})();
