import { apiGet } from '../token.js';

export function mountDev(container) {
  container.innerHTML = `
    <div class="card">
      <button id="dev-ping" class="btn">Ping Plugin</button>
      <pre id="ping-result"></pre>
    </div>
  `;
  const out = container.querySelector('#ping-result');
  container.querySelector('#dev-ping').onclick = async () => {
    try {
      const j = await apiGet('/health');
      out.textContent = JSON.stringify(j, null, 2);
    } catch (e) {
      out.textContent = String(e);
    }
  };
}
