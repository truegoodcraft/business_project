import { post } from './api.js';

export async function mountOrganizer(root){
  if(!root) return;
  root.innerHTML=`<h2>Organizer</h2>
  <div class="row"><input id="start" placeholder="Start folder" style="min-width:360px">
  <input id="qdir" placeholder="Quarantine (optional)" style="min-width:320px">
  <button id="dup">Duplicates → Plan</button><button id="ren">Normalize → Plan</button></div>
  <div class="row" style="margin-top:8px"><input id="pid" placeholder="Plan ID" style="min-width:320px">
  <button id="prev">Preview</button><button id="commit">Commit</button></div>
  <pre id="out" class="muted" style="margin-top:8px"></pre>`;

  const $=selector=>root.querySelector(selector);
  const out=$('#out');

  const renderResult=data=>{ out.textContent=JSON.stringify(data,null,2); };
  const renderError=error=>{ out.textContent='Error: '+error.message; };

  $('#dup').addEventListener('click',async()=>{
    try{
      const data=await post('/organizer/duplicates/plan',{
        start_path:$('#start').value.trim(),
        quarantine_dir:$('#qdir').value.trim()||null
      });
      $('#pid').value=data?.plan_id||'';
      renderResult(data);
    }catch(error){
      renderError(error);
    }
  });

  $('#ren').addEventListener('click',async()=>{
    try{
      const data=await post('/organizer/rename/plan',{
        start_path:$('#start').value.trim()
      });
      $('#pid').value=data?.plan_id||'';
      renderResult(data);
    }catch(error){
      renderError(error);
    }
  });

  $('#prev').addEventListener('click',async()=>{
    const id=$('#pid').value.trim();
    if(!id){
      alert('No plan id');
      return;
    }
    try{
      const data=await post(`/plans/${encodeURIComponent(id)}/preview`,{});
      renderResult(data);
    }catch(error){
      renderError(error);
    }
  });

  $('#commit').addEventListener('click',async()=>{
    const id=$('#pid').value.trim();
    if(!id){
      alert('No plan id');
      return;
    }
    try{
      const data=await post(`/plans/${encodeURIComponent(id)}/commit`,{});
      renderResult(data);
    }catch(error){
      renderError(error);
    }
  });
}

async function autoMount(){
  const root=document.getElementById('organizer-card');
  if(!root || root.dataset.mounted==='true') return;
  root.dataset.mounted='true';
  try{
    await mountOrganizer(root);
  }catch(error){
    console.error('Organizer card failed to mount:',error);
  }
}

document.addEventListener('bus:token-ready',()=>{ autoMount(); });
if(document.readyState==='complete' || document.readyState==='interactive'){
  autoMount();
}else{
  document.addEventListener('DOMContentLoaded',()=>{ autoMount(); });
}
