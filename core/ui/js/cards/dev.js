import { apiGet } from "../token.js";

export function mountDev(container) {
  container.innerHTML = `
    <div class="card"><button id="btnPing">Ping Plugin</button>
    <pre id="ping-res"></pre></div>`;
  document.getElementById("btnPing").onclick = async () => {
    try {
      const j = await apiGet("/health");
      document.getElementById("ping-res").textContent = JSON.stringify(j, null, 2);
    } catch (e) {
      document.getElementById("ping-res").textContent = String(e);
    }
  };
}
