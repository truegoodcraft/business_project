import { apiGet, apiPost } from '../token.js';

export async function mountDev(el) {
  el.innerHTML = `
    <h2>Dev</h2>
    <div style="margin:8px 0;">
      <button class="btn" id="ping">Ping /health</button>
      <span id="pingResult"></span>
    </div>
    <div style="margin:8px 0;">
      <button class="btn" id="toggleWrites">Toggle Writes</button>
      <span id="writesState"></span>
    </div>
  `;

  const pingBtn = el.querySelector('#ping');
  const pingRes = el.querySelector('#pingResult');
  pingBtn.onclick = async () => {
    try { await apiGet('/health'); pingRes.textContent = 'OK'; }
    catch (e) { pingRes.textContent = 'FAIL'; console.error(e); }
  };

  const wBtn = el.querySelector('#toggleWrites');
  const wState = el.querySelector('#writesState');

  async function refreshWrites() {
    try {
      const s = await apiGet('/dev/writes');
      wState.textContent = s.enabled ? 'enabled' : 'disabled';
    } catch (e) {
      wState.textContent = 'unknown';
      console.error(e);
    }
  }
  wBtn.onclick = async () => {
    try {
      const s = await apiGet('/dev/writes');
      await apiPost('/dev/writes', { enabled: !s.enabled });
      await refreshWrites();
    } catch (e) { console.error(e); }
  };

  refreshWrites();
}
