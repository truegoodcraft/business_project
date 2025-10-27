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
    const r = await apiGet('/health');
    document.getElementById('ping-res').textContent = JSON.stringify({ status: r.status }, null, 2);
  };
  document.getElementById('btn-writes').onclick = async () => {
    const s = await apiJson('/dev/writes');
    const next = !s.enabled;
    await apiPost('/dev/writes', { enabled: next });
    await updateWrites();
  };
  await updateWrites();
}

async function updateWrites() {
  const s = await apiJson('/dev/writes');
  document.getElementById('writes-state').textContent = s.enabled ? 'writes: ON' : 'writes: OFF';
}
