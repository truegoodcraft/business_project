async function getToken(){
  try{
    const response=await fetch('/session/token');
    if(!response.ok) throw new Error(`Token fetch failed: ${response.status}`);
    const data=await response.json();
    const token=typeof data?.token==='string'?data.token:null;
    if(!token) throw new Error('Token payload missing');
    localStorage.setItem('tgc_token',token);
    const event=new CustomEvent('bus:token-ready',{detail:{token}});
    document.dispatchEvent(event);
    console.log('Token ready:',token.substring(0,8)+'...');
    return token;
  }catch(error){
    console.error('Token error:',error);
    localStorage.removeItem('tgc_token');
    if(!document.getElementById('token-banner')){
      document.body.insertAdjacentHTML('afterbegin','<div id="token-banner" style="position:fixed;top:0;left:0;background:red;color:white;padding:1em;z-index:999;">Session expired—restart launcher</div>');
    }
  }
}

if(typeof window!=='undefined'){
  window.getToken=getToken;
}else if(typeof globalThis!=='undefined'){
  globalThis.getToken=getToken;
}

document.addEventListener('DOMContentLoaded',async()=>{
  const stored=localStorage.getItem('tgc_token');
  if(stored){
    let token=stored;
    try{
      const parsed=JSON.parse(stored);
      if(parsed && typeof parsed.token==='string'){
        token=parsed.token;
      }
    }catch{}
    if(typeof token!=='string'){
      await getToken();
      return;
    }
    const event=new CustomEvent('bus:token-ready',{detail:{token}});
    document.dispatchEvent(event);
    console.log('Stored token loaded:',token.substring(0,8)+'...');
  }else{
    await getToken();
  }
});

document.addEventListener('bus:token-ready',event=>{
  console.log('Event fired—cards should load');
});
