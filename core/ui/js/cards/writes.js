import { apiCall, post } from './api.js';

export async function mountWrites(root){
  if(!root) return;
  root.innerHTML='<label>Writes: <input type="checkbox" id="writes-toggle"></label><pre id="writes-out" class="muted" style="margin-top:8px"></pre>';
  const toggle=root.querySelector('#writes-toggle');
  const out=root.querySelector('#writes-out');

  async function refreshWrites(){
    try{
      const data=await apiCall('/dev/writes');
      toggle.checked=!!data?.enabled;
      out.textContent=JSON.stringify(data,null,2);
    }catch(error){
      out.textContent='Error: '+error.message;
    }
  }

  toggle.addEventListener('change',async()=>{
    try{
      const payload={enabled:toggle.checked};
      const data=await post('/dev/writes',payload);
      out.textContent=JSON.stringify(data,null,2);
      await refreshWrites();
    }catch(error){
      out.textContent='Error: '+error.message;
    }
  });

  await refreshWrites();
}

async function autoMount(){
  const root=document.getElementById('writes-card');
  if(!root || root.dataset.mounted==='true') return;
  root.dataset.mounted='true';
  try{
    await mountWrites(root);
  }catch(error){
    console.error('Writes card failed to mount:',error);
  }
}

document.addEventListener('bus:token-ready',()=>{ autoMount(); });
if(document.readyState==='complete' || document.readyState==='interactive'){
  autoMount();
}else{
  document.addEventListener('DOMContentLoaded',()=>{ autoMount(); });
}
