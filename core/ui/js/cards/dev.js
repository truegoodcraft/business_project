export function mountDev(container) {
  container.innerHTML = `
    <div class="card">
      <h2>Dev Tools</h2>
      <button id="ping">Ping Plugin</button>
      <pre id="out"></pre>
    </div>`;
  document.getElementById("ping").onclick = ping;
}

async function ping() {
  const out = document.getElementById("out");
  try {
    const { ensureToken } = await import("/ui/js/token.js");
    const token = await ensureToken();           // returns string
    const res = await fetch("/health", {
      headers: {
        "X-Session-Token": token,
        "Authorization": `Bearer ${token}`
      }
    });
    out.textContent = JSON.stringify(await res.json(), null, 2);
  } catch (e) {
    out.textContent = "Error: " + e;
  }
}
