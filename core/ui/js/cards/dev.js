import {get} from '/ui/js/api.js';
export async function mountDev(root){
  root.innerHTML = `<h2>Dev Tools</h2><button id="ping">Ping Plugin</button><pre id="o" class="muted" style="margin-top:8px"></pre>`;
  const $=s=>root.querySelector(s);
  $('#ping').onclick=async()=>{ const j=await get('/dev/ping_plugin'); $('#o').textContent=JSON.stringify(j,null,2); };
}
