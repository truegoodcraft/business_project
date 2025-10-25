import { apiCall } from './api.js';

export async function mountDev(root){
  if(!root) return;
  root.innerHTML='<h2>Dev Tools</h2><button id="ping">Ping Plugin</button><pre id="o" class="muted" style="margin-top:8px"></pre>';
  const button=root.querySelector('#ping');
  const out=root.querySelector('#o');

  button.addEventListener('click',async()=>{
    try{
      const data=await apiCall('/dev/ping_plugin');
      out.textContent=JSON.stringify(data,null,2);
    }catch(error){
      out.textContent='Error: '+error.message;
    }
  });
}

async function autoMount(){
  const root=document.getElementById('dev-card');
  if(!root || root.dataset.mounted==='true') return;
  root.dataset.mounted='true';
  try{
    await mountDev(root);
  }catch(error){
    console.error('Dev card failed to mount:',error);
  }
}

document.addEventListener('bus:token-ready',()=>{ autoMount(); });
if(document.readyState==='complete' || document.readyState==='interactive'){
  autoMount();
}else{
  document.addEventListener('DOMContentLoaded',()=>{ autoMount(); });
}
