import { get, post } from '/ui/js/api.js';
export async function mountWrites(root){
  root.innerHTML = `
    <h2>Writes</h2>
    <div class="row">
      <div id="status" class="muted">Loading…</div>
      <button id="toggle" disabled>Toggle</button>
    </div>
    <pre id="out" class="muted"></pre>
  `;
  const $ = sel => root.querySelector(sel);
  async function refresh(){
    const j = await get('/dev/writes');
    $('#status').textContent = 'Writes: ' + (j.enabled ? 'Enabled' : 'Disabled');
    $('#toggle').disabled = false;
    $('#toggle').textContent = j.enabled ? 'Disable' : 'Enable';
  }
  $('#toggle').onclick = async ()=>{
    $('#toggle').disabled = true;
    const j = await post('/dev/writes', {enabled: $('#toggle').textContent==='Enable'});
    $('#out').textContent = JSON.stringify(j,null,2);
    await refresh();
  };
  await refresh();
}
