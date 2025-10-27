export function mountDev(container){
  container.innerHTML = `
    <div class="card">
      <h2>Dev Tools</h2>
      <button id="ping">Ping Plugin</button>
      <pre id="out"></pre>
    </div>`;
  document.getElementById("ping").onclick = async () => {
    try {
      const { ensureToken } = await import("/ui/js/token.js");
      const res = await fetch("/health", { headers: { "X-Session-Token": await ensureToken() }});
      document.getElementById("out").textContent = JSON.stringify(await res.json(), null, 2);
    } catch (e) {
      document.getElementById("out").textContent = "Error: " + e;
    }
  };
}
