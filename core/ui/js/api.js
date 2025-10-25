/* Minimal API helpers; fetch is already patched by token.js */

async function apiGet(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${url} ${r.status}`);
  return r.json();
}

async function apiPost(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {})
  });
  if (!r.ok) throw new Error(`${url} ${r.status}`);
  return r.json();
}

async function apiPut(url, body) {
  const r = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {})
  });
  if (!r.ok) throw new Error(`${url} ${r.status}`);
  return r.json();
}

async function apiDel(url) {
  const r = await fetch(url, { method: 'DELETE' });
  if (!r.ok) throw new Error(`${url} ${r.status}`);
  return r.json();
}

// Named + default (for backwards compatibility)
export { apiGet, apiPost, apiPut, apiDel };
export default { apiGet, apiPost, apiPut, apiDel };
