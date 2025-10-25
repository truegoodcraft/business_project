// Gate card init on token readiness
(function(){
  function init(){
    if (!window.apiGet) {
      console.error('Card missing API helpers');
      return;
    }

    const busApi = window.busApi || {};
    const apiGet = busApi.apiGet || window.apiGet;
    if (typeof apiGet !== 'function') {
      console.error('Card missing API helpers');
      return;
    }

    async function mountDev(root){
      if(!root) return;
      root.innerHTML='<h2>Dev Tools</h2><button id="ping">Ping Plugin</button><pre id="o" class="muted" style="margin-top:8px"></pre>';
      const button=root.querySelector('#ping');
      const out=root.querySelector('#o');

      button.addEventListener('click',async()=>{
        try{
          const data=await apiGet('/dev/ping_plugin');
          out.textContent=JSON.stringify(data,null,2);
        }catch(error){
          out.textContent='Error: '+error.message;
        }
      });
    }

    window.busCards = window.busCards || {};
    window.busCards.mountDev = mountDev;
  }
  if (localStorage.getItem('BUS_SESSION_TOKEN')) init();
  else window.addEventListener('bus:token-ready', init, { once: true });
})();
