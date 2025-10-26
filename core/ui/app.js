import { ensureToken, apiGet, apiPost } from "/ui/js/token.js";
import { mountWrites } from "/ui/js/cards/writes.js";
import { mountOrganizer } from "/ui/js/cards/organizer.js";
import { mountBackup } from "/ui/js/cards/backup.js";
import { mountInventory } from "/ui/js/cards/inventory.js";
import { mountRfq } from "/ui/js/cards/rfq.js";
import { mountDev } from "/ui/js/cards/dev.js";

const tabs = {
  writes: () => mountWrites(app),
  tools: () => {
    app.innerHTML = `
      <div class="card"><h2>Tools</h2><p>Select a tool:</p></div>
      <div class="card" onclick="window.bus.mountOrganizer()">Organizer</div>
      <div class="card" onclick="window.bus.mountBackup()">Backup</div>
      <div class="card" onclick="window.bus.mountInventory()">Inventory</div>
      <div class="card" onclick="window.bus.mountRfq()">RFQ</div>
    `;
  },
  dev: () => mountDev(app)
};

let currentTab = "writes";
const app = document.getElementById("app");

async function boot() {
  try {
    await ensureToken();
    const license = await apiGet("/dev/license");
    const writes = await apiGet("/dev/writes");

    const header = document.createElement("div");
    header.innerHTML = `
      <div style="margin-bottom:16px; padding-bottom:8px; border-bottom:1px solid #333; font-size:13px; color:#aaa;">
        License: <strong>${license.tier}</strong> | 
        Writes: <strong id="writes-status">${writes.enabled ? "ON" : "OFF"}</strong>
        <button id="toggle-writes" style="margin-left:8px; font-size:12px;">Toggle</button>
      </div>
    `;
    app.prepend(header);

    document.title = `BUS Core — ${license.tier}`;

    document.getElementById("toggle-writes").onclick = async () => {
      const next = await apiPost("/dev/writes", { enabled: !writes.enabled });
      writes.enabled = next.enabled;
      document.getElementById("writes-status").textContent = next.enabled ? "ON" : "OFF";
      if (currentTab === "writes") mountWrites(app);
    };

    document.querySelectorAll(".tab").forEach(tab => {
      tab.onclick = () => {
        document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        currentTab = tab.dataset.tab;
        app.innerHTML = "";
        app.appendChild(header.cloneNode(true));
        tabs[currentTab]();
        const btn = app.querySelector("#toggle-writes");
        if (btn) btn.onclick = document.getElementById("toggle-writes").onclick;
      };
    });

    tabs[currentTab]();

    window.bus = Object.freeze({
      mountWrites: () => { switchTab("writes"); },
      mountOrganizer: () => { switchTab("tools"); mountOrganizer(app); },
      mountBackup: () => { switchTab("tools"); mountBackup(app); },
      mountInventory: () => { switchTab("tools"); mountInventory(app); },
      mountRfq: () => { switchTab("tools"); mountRfq(app); },
      mountDev: () => { switchTab("dev"); }
    });

    function switchTab(id) {
      currentTab = id;
      document.querySelector(`[data-tab="${id}"]`).click();
    }

    console.log("BOOT OK");
  } catch (err) {
    console.error("BOOT FAILED", err);
    app.innerHTML = `<pre style="color:red;">${err}</pre>`;
  }
}

boot();
