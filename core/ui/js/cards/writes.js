import {get,post} from '/ui/js/api.js';
export async function mountWrites(root){
  root.innerHTML = `<h2>Writes</h2><div class="row"><div id="s" class="muted">Loading…</div>
  <button id="t" disabled>Toggle</button></div><pre id="o" class="muted" style="margin-top:8px"></pre>`;
  const $=s=>root.querySelector(s);
  async function refresh(){ const j=await get('/dev/writes'); $('#s').textContent='Writes: '+(j.enabled?'Enabled':'Disabled'); $('#t').disabled=false; $('#t').textContent=j.enabled?'Disable':'Enable'; }
  $('#t').onclick=async()=>{ $('#t').disabled=true; const on=$('#t').textContent==='Enable'; const j=await post('/dev/writes',{enabled:on}); $('#o').textContent=JSON.stringify(j,null,2); await refresh(); };
  await refresh();
}
