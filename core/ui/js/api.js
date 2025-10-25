async function apiCall(path,options={method:'GET'}){
  const token=localStorage.getItem('tgc_token');
  if(!token) throw new Error('No token—reload page');
  const headers=new Headers({...options.headers,'X-Session-Token':token});
  if(options.method!=='GET') headers.set('Content-Type','application/json');
  let response;
  try{
    response=await fetch(path,{...options,headers});
  }catch(error){
    throw new Error(`Fetch error: ${error.message}`);
  }
  if(response.status===401){
    localStorage.removeItem('tgc_token');
    await getToken();
    throw new Error('Token refreshed—retry');
  }
  if(!response.ok){
    const errText=await response.text();
    throw new Error(`API ${response.status}: ${errText}`);
  }
  return options.method==='GET' ? response.json() : response;
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

if(typeof module!=='undefined'){
  module.exports={apiCall,get,post,put,del};
}
