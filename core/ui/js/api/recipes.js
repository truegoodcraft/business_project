// core/ui/js/api/recipes.js
const BASE = '/app';

async function j(method, path, body) {
  const { ensureToken } = await import('../api.js');
  const token = await ensureToken();
  const headers = { 'Content-Type': 'application/json', 'X-Session-Token': token };
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'omit',
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${method} ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

export const RecipesAPI = {
  list() { return j('GET', '/recipes'); },
  get(id) { return j('GET', `/recipes/${id}`); },
  create(payload) { return j('POST', '/recipes', payload); },
  update(id, payload) { return j('PUT', `/recipes/${id}`, payload); },
  remove(id) { return j('DELETE', `/recipes/${id}`); },
  run(payload) { return j('POST', '/manufacturing/run', payload); },
};
