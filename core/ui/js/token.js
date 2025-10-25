const TOKEN_KEY = 'tgc_token';
const EVENT_NAME = 'bus:token-ready';
let pendingToken = null;

function readStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || '';
  } catch (err) {
    console.warn('[token] Unable to access localStorage', err);
    return '';
  }
}

function storeToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch (err) {
    console.warn('[token] Failed to store token', err);
  }
}

function dispatchToken(token) {
  const payload = token || '';
  console.log('[token] Token ready event', payload ? payload.slice(0, 8) + '…' : '(empty)');
  document.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: payload }));
  return payload;
}

async function requestToken() {
  try {
    console.log('[token] Fetching session token…');
    const response = await fetch('/session/token', { cache: 'no-store' });
    if (response.status === 401) {
      console.warn('[token] Token request returned 401');
      storeToken('');
      return '';
    }
    if (response.ok) {
      const token = (await response.text()).trim();
      if (token) {
        storeToken(token);
        return token;
      }
    }
    console.warn('[token] Unexpected response while fetching token', response.status);
  } catch (error) {
    console.error('Token fail:', error);
  }
  return '';
}

export async function getToken(forceRefresh = false) {
  if (forceRefresh) {
    storeToken('');
  }

  const cached = forceRefresh ? '' : readStoredToken();
  if (cached) {
    return dispatchToken(cached);
  }

  if (!pendingToken) {
    pendingToken = (async () => {
      const token = await requestToken();
      pendingToken = null;
      return dispatchToken(token);
    })();
  }

  return pendingToken;
}

export const Token = { get: getToken };

function init() {
  const cached = readStoredToken();
  if (cached) {
    dispatchToken(cached);
  }
  if (document.readyState === 'complete') {
    getToken();
  } else {
    window.addEventListener('load', () => getToken());
  }
}

init();
