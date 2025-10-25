import { get } from '/ui/js/api.js';
export async function mountDev(root){
  root.innerHTML = `
    <h2>Dev Tools</h2>
    <button id="ping">Ping Plugin</button>
    <pre id="out" style="margin-top:8px" class="muted"></pre>
  `;
  const $ = sel => root.querySelector(sel);
  $('#ping').onclick = async ()=>{
    const j = await get('/dev/ping_plugin');
    $('#out').textContent = JSON.stringify(j,null,2);
  };
}
