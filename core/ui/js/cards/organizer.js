import {post} from '/ui/js/api.js';
export async function mountOrganizer(root){
  root.innerHTML = `<h2>Organizer</h2>
  <div class="row"><input id="start" placeholder="Start folder" style="min-width:360px">
  <input id="qdir" placeholder="Quarantine (optional)" style="min-width:320px">
  <button id="dup">Duplicates → Plan</button><button id="ren">Normalize → Plan</button></div>
  <div class="row" style="margin-top:8px"><input id="pid" placeholder="Plan ID" style="min-width:320px">
  <button id="prev">Preview</button><button id="commit">Commit</button></div>
  <pre id="out" class="muted" style="margin-top:8px"></pre>`;
  const $=s=>root.querySelector(s);
  $('#dup').onclick=async()=>{ const j=await post('/organizer/duplicates/plan',{start_path:$('#start').value.trim(),quarantine_dir:$('#qdir').value.trim()||null}); $('#pid').value=j.plan_id||''; $('#out').textContent=JSON.stringify(j,null,2); };
  $('#ren').onclick=async()=>{ const j=await post('/organizer/rename/plan',{start_path:$('#start').value.trim()}); $('#pid').value=j.plan_id||''; $('#out').textContent=JSON.stringify(j,null,2); };
  $('#prev').onclick=async()=>{ const id=$('#pid').value.trim(); if(!id) return alert('No plan id'); const j=await post(`/plans/${encodeURIComponent(id)}/preview`,{}); $('#out').textContent=JSON.stringify(j,null,2); };
  $('#commit').onclick=async()=>{ const id=$('#pid').value.trim(); if(!id) return alert('No plan id'); const j=await post(`/plans/${encodeURIComponent(id)}/commit`,{}); $('#out').textContent=JSON.stringify(j,null,2); };
}
