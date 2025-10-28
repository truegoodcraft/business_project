// core/ui/js/cards/dev.js
import { ensureToken, apiGet, apiPost, apiJson } from '../token.js';

export function mountDev(container) {
  container.innerHTML = `
    <div class="card">
      <button id="btn-ping" class="btn">Ping Plugin</button>
      <pre id="ping-res" class="log"></pre>
      <div style="margin-top:12px">
        <button id="btn-writes" class="btn">Toggle Writes</button>
        <span id="writes-state" class="badge"></span>
      </div>
    </div>`;
  wire();
}

async function wire() {
  document.getElementById('btn-ping').onclick = window.pingPlugin;

  document.getElementById('btn-writes').onclick = async () => {
    const s = await apiJson('/dev/writes');    // {enabled:boolean}
    await apiPost('/dev/writes', { enabled: !s.enabled });
    updateWrites();
  };

  updateWrites();
}

async function updateWrites() {
  const s = await apiJson('/dev/writes');
  document.getElementById('writes-state').textContent =
    s.enabled ? 'writes: ON' : 'writes: OFF';
}

// keep inline onclick support but ensure headers are set
window.pingPlugin = async () => {
  try {
    const { ensureToken, request } = await import('/ui/js/token.js');
    await ensureToken();                           // guarantee token in storage
    const r = await request('/health', { method: 'GET' }); // injects both headers
    console.log('ping status', r.status);
    const out = document.getElementById('ping-res');
    if (out) out.textContent = `status ${r.status}`;
    return r.status;
  } catch (e) {
    console.error('ping failed', e);
    const out = document.getElementById('ping-res');
    if (out) out.textContent = 'error: ' + e;
    return 0;
  }
};
