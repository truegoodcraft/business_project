import { apiGet, apiPost, apiJson } from '../token.js';

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
  document.getElementById('btn-ping').onclick = async () => {
    try {
      const r = await apiGet('/health');
      document.getElementById('ping-res').textContent = `status ${r.status}`;
    } catch (e) {
      document.getElementById('ping-res').textContent = 'error: ' + e;
    }
  };

  document.getElementById('btn-writes').onclick = async () => {
    const s = await apiJson('/dev/writes');
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
