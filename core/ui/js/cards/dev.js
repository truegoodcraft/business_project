// core/ui/js/cards/dev.js
import { ensureToken, apiGet, apiPost, apiJson } from '../token.js';

export function mountDev(container) {
  container.innerHTML = `
    <div class="card">
      <h2>Dev Tools</h2>
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
    const s = await apiJson('/dev/writes');           // { enabled: boolean }
    await apiPost('/dev/writes', { enabled: !s.enabled });
    updateWrites();
  };

  updateWrites();
}

async function updateWrites() {
  const s = await apiJson('/dev/writes');
  document.getElementById('writes-state').textContent = s.enabled ? 'writes: ON' : 'writes: OFF';
}

// global for shell.html onclick compatibility
window.pingPlugin = async () => {
  const out = document.getElementById('ping-res');
  try {
    await ensureToken();
    const res = await apiGet('/health');
    out && (out.textContent = `status ${res.status}`);
    return res.status;
  } catch (e) {
    out && (out.textContent = 'error: ' + e);
    return 0;
  }
};
