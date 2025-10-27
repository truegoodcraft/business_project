import { ensureToken, apiGet } from "/ui/js/token.js";

export function mountDev(container){
  container.innerHTML = `
    <div class="card">
      <h2>Dev Tools</h2>
      <button id="ping">Ping Plugin</button>
      <pre id="out"></pre>
    </div>`;
  document.getElementById("ping").onclick = ping;
}

async function ping(){
  const out = document.getElementById("out");
  try{
    await ensureToken();
    const res = await apiGet("/health");
    out.textContent = JSON.stringify(res, null, 2);
  }catch(e){
    out.textContent = JSON.stringify(e, null, 2);
  }
}
