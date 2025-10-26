export function mountDev(container) {
  container.innerHTML = `
    <div class="card">
      <h2>Dev Tools</h2>
      <button onclick="pingPlugin()">Ping Plugin</button>
      <pre id="ping-result"></pre>
    </div>
  `;
  window.pingPlugin = async () => {
    try {
      const res = await fetch("/health", { headers: { "X-Session-Token": (await import("/ui/js/token.js")).ensureToken() } });
      document.getElementById("ping-result").textContent = JSON.stringify(await res.json(), null, 2);
    } catch (e) {
      document.getElementById("ping-result").textContent = "Error: " + e;
    }
  };
}
