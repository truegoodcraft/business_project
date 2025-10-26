jslet TOKEN = null;

export async function getToken() {
  if (TOKEN) return TOKEN;
  const res = await fetch("/session/token");
  if (!res.ok) throw new Error("Token fetch failed");
  const data = await res.json();
  TOKEN = data.token;
  return TOKEN;
}

export async function apiGet(url) {
  await getToken();
  const res = await fetch(url, {
    headers: { "X-Session-Token": TOKEN }
  });
  if (!res.ok) throw new Error(`GET ${url}: ${res.status}`);
  return res.json();
}

export async function getLicense() {
  return apiGet("/dev/license");
}
