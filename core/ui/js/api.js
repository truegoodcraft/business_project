export async function get(url){
  const r = await fetch(url, {cache:'no-store'});
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function post(url, body){
  const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body||{})});
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
