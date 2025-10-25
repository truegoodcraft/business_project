let tokenRetryCount=0;

export async function apiCall(path,options={method:'GET'}){
  const method=(options.method||'GET').toUpperCase();
  const stored=localStorage.getItem('tgc_token');
  if(!stored) throw new Error('No token—reload page');
  let token=stored;
  if(typeof token==='string'){
    try{
      const parsed=JSON.parse(stored);
      if(parsed && typeof parsed.token==='string'){
        token=parsed.token;
      }
    }catch{}
  }else{
    try{
      const parsed=JSON.parse(String(stored));
      if(parsed && typeof parsed.token==='string'){
        token=parsed.token;
      }
    }catch{}
  }
  if(typeof token!=='string' || !token) throw new Error('Invalid token');
  const headers=new Headers({...(options.headers||{}),'X-Session-Token':token});
  if(method!=='GET') headers.set('Content-Type','application/json');
  let response;
  try{
    response=await fetch(path,{...options,method,headers});
  }catch(error){
    throw new Error(`Fetch error: ${error.message}`);
  }
  if(response.status===401){
    if(tokenRetryCount<1){
      tokenRetryCount+=1;
      localStorage.removeItem('tgc_token');
      if(typeof getToken==='function'){
        await getToken();
      }else if(typeof window!=='undefined' && typeof window.getToken==='function'){
        await window.getToken();
      }else if(typeof globalThis!=='undefined' && typeof globalThis.getToken==='function'){
        await globalThis.getToken();
      }
      throw new Error('Token refreshed—retry call');
    }
    tokenRetryCount=0;
    throw new Error('Auth failed');
  }
  tokenRetryCount=0;
  if(!response.ok){
    const errText=await response.text();
    throw new Error(`API ${response.status}: ${errText}`);
  }
  const contentType=response.headers.get('content-type')||'';
  if(contentType.includes('application/json')){
    try{
      return await response.json();
    }catch{
      return null;
    }
  }
  const raw=await response.text();
  if(!raw){
    return method==='GET'?null:{success:true};
  }
  try{
    return JSON.parse(raw);
  }catch{
    return method==='GET'?raw:{message:raw};
  }
}

async function get(path){
  return apiCall(path);
}

async function post(path,body){
  return apiCall(path,{method:'POST',body:JSON.stringify(body)});
}

async function put(path,body){
  return apiCall(path,{method:'PUT',body:JSON.stringify(body)});
}

async function del(path){
  return apiCall(path,{method:'DELETE'});
}

export {get,post,put,del};
