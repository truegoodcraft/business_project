/* ESM dispatcher: tabs → card mounts, no router */
import { ensureToken, apiGet, apiPost } from "/ui/js/token.js";
import { mountWrites }    from "/ui/js/cards/writes.js";
import { mountOrganizer } from "/ui/js/cards/organizer.js";
import { mountBackup }    from "/ui/js/cards/backup.js";
import { mountInventory } from "/ui/js/cards/inventory.js";
import { mountRfq }       from "/ui/js/cards/rfq.js";
import { mountDev }       from "/ui/js/cards/dev.js";

const app = document.getElementById("app");

function renderShell(licenseTier, writesEnabled) {
  app.innerHTML = `
    <div class="layout">
      <nav id="sidebar" class="sidebar">
        <div class="brand">BUS Core</div>
        <button class="tab active" data-target="mountWrites">Writes</button>
        <button class="tab" data-target="mountOrganizer">Organizer</button>
        <button class="tab" data-target="mountInventory">Inventory</button>
        <button class="tab" data-target="mountRfq">RFQ</button>
        <button class="tab" data-target="mountBackup">Backup</button>
        <button class="tab" data-target="mountDev">Dev</button>
      </nav>
      <main class="main">
        <div class="header">
          <span>License: <b>${licenseTier}</b></span>
          <span style="margin-left:12px">Writes: <b id="writes-status">${writesEnabled ? "ON" : "OFF"}</b></span>
          <button id="toggle-writes" class="btn" style="margin-left:8px">Toggle</button>
        </div>
        <div id="main"></div>
      </main>
    </div>
  `;
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const target = btn.dataset.target;
      const container = document.getElementById("main");
      container.innerHTML = "";
      window.bus[target](container);
    };
  });
}

async function boot() {
  await ensureToken();
  const [license, writes] = await Promise.all([
    apiGet("/dev/license"),
    apiGet("/dev/writes")
  ]);

  renderShell(license.tier, writes.enabled);
  bindTabs();

  document.getElementById("toggle-writes").onclick = async () => {
    const next = await apiPost("/dev/writes", { enabled: !(document.getElementById("writes-status").textContent === "ON") });
    document.getElementById("writes-status").textContent = next.enabled ? "ON" : "OFF";
    if (document.querySelector('.tab.active')?.dataset.target === "mountWrites") {
      window.bus.mountWrites(document.getElementById("main"));
    }
  };

  // default mount
  window.bus.mountWrites(document.getElementById("main"));
  console.log("BOOT OK");
}

// expose mounts
window.bus = Object.freeze({
  mountWrites:    (el) => mountWrites(el),
  mountOrganizer: (el) => mountOrganizer(el),
  mountBackup:    (el) => mountBackup(el),
  mountInventory: (el) => mountInventory(el),
  mountRfq:       (el) => mountRfq(el),
  mountDev:       (el) => mountDev(el),
});

boot().catch(e => {
  console.error("BOOT FAILED", e);
  app.innerHTML = `<pre style="color:red">${String(e)}</pre>`;
});
