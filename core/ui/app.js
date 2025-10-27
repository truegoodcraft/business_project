import { ensureToken, apiGet, apiPost } from "./js/token.js";
import { mountWrites }    from "/ui/js/cards/writes.js";
import { mountOrganizer } from "/ui/js/cards/organizer.js";
import { mountBackup }    from "/ui/js/cards/backup.js";
import { mountInventory } from "/ui/js/cards/inventory.js";
import { mountRfq }       from "/ui/js/cards/rfq.js";
import { mountDev }       from "/ui/js/cards/dev.js";

const app = document.getElementById("app");
let currentTab = "writes";

const tabs = {
  writes: () => mountWrites(app),
  tools:  () => {
    app.innerHTML = `
      <div class="card"><h2>Tools</h2><p>Select a tool:</p></div>
      <div class="card" onclick="window.bus.mountOrganizer()">Organizer</div>
      <div class="card" onclick="window.bus.mountBackup()">Backup</div>
      <div class="card" onclick="window.bus.mountInventory()">Inventory</div>
      <div class="card" onclick="window.bus.mountRfq()">RFQ</div>
    `;
  },
  dev: () => mountDev(app),
};

function bindTabs() {
  document.querySelectorAll(".tab").forEach(tab => {
    tab.onclick = () => {
      document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentTab = tab.dataset.tab;
      app.innerHTML = "";
      mountHeader().then(() => tabs[currentTab]());
    };
  });
}

async function mountHeader() {
  await ensureToken();
  const [license, writes] = await Promise.all([
    apiGet("/dev/license"),
    apiGet("/dev/writes")
  ]);
  const header = document.createElement("div");
  header.innerHTML = `
    <div style="margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #333;font-size:13px;color:#aaa;">
      License: <strong>${license.tier}</strong> |
      Writes: <strong id="writes-status">${writes.enabled ? "ON" : "OFF"}</strong>
      <button id="toggle-writes" style="margin-left:8px;font-size:12px;">Toggle</button>
    </div>
  `;
  app.prepend(header);
  header.querySelector("#toggle-writes").onclick = async () => {
    const next = await apiPost("/dev/writes",{enabled: !(writes.enabled)});
    writes.enabled = next.enabled;
    header.querySelector("#writes-status").textContent = next.enabled ? "ON" : "OFF";
    if (currentTab === "writes") mountWrites(app);
  };
}

window.bus = Object.freeze({
  mountWrites:    () => switchTab("writes"),
  mountOrganizer: () => { switchTab("tools"); mountOrganizer(app); },
  mountBackup:    () => { switchTab("tools"); mountBackup(app); },
  mountInventory: () => { switchTab("tools"); mountInventory(app); },
  mountRfq:       () => { switchTab("tools"); mountRfq(app); },
  mountDev:       () => switchTab("dev"),
});

function switchTab(id){
  const el = document.querySelector(`[data-tab="${id}"]`);
  if (el) el.click();
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    await ensureToken();
    try {
      await apiGet("/health");
      console.log("BOOT OK");
    } catch (e) {
      console.error(e);
    }
    await mountHeader();
    bindTabs();
    tabs[currentTab]();
  } catch (e) {
    console.error("BOOT FAILED", e);
    app.innerHTML = `<pre style="color:red;">${e}</pre>`;
  }
});
