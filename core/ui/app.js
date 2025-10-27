import { ensureToken, apiGet, apiPost, currentToken } from "./js/token.js";
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

document.addEventListener('DOMContentLoaded', init);

async function init() {
  try {
    console.log('BOOT OK');
    await ensureToken();

    // header writes toggle
    const hdr = document.getElementById('sidebar') || document.body;
    let bar = document.getElementById('bus-header');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'bus-header';
      bar.style.padding = '6px 10px';
      bar.style.display = 'flex';
      bar.style.gap = '8px';
      bar.style.alignItems = 'center';
      bar.style.fontSize = '12px';
      hdr.prepend(bar);
    }
    const wBadge = document.createElement('span');
    const wBtn   = document.createElement('button');
    wBtn.className = 'btn';
    wBtn.textContent = 'Toggle Writes';
    bar.replaceChildren(
      tokenSpan(), wBtn, wBadge
    );

    async function refreshWrites() {
      try {
        const s = await apiGet('/dev/writes');
        wBadge.textContent = s?.enabled ? 'WRITES: ON' : 'WRITES: OFF';
      } catch { wBadge.textContent = 'WRITES: ?'; }
    }
    wBtn.onclick = async () => {
      try {
        const s = await apiPost('/dev/writes', { enabled: undefined }); // backend flips or honors provided
        wBadge.textContent = s?.enabled ? 'WRITES: ON' : 'WRITES: OFF';
        if (currentTab === 'writes') mountWrites(app);
      } catch (e) { console.error(e); }
    };

    function tokenSpan() {
      const s = document.createElement('span');
      s.title = 'session token used for requests';
      s.textContent = 'token… ' + (currentToken().slice(0,8) || 'none');
      return s;
    }

    // sanity check: /health with token
    try {
      const r = await fetch('/health', {
        headers: {
          'X-Session-Token': currentToken(),
          'Authorization': 'Bearer ' + currentToken()
        }
      });
      console.log('health', r.status);
    } catch (e) { console.error('health error', e); }

    await refreshWrites();

    await mountHeader();
    bindTabs();
    tabs[currentTab]();
  } catch (e) {
    console.error('BOOT FAILED', e);
    app.innerHTML = `<pre style="color:red;">${e}</pre>`;
  }
}

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
  const license = await apiGet("/dev/license");
  const header = document.createElement("div");
  header.innerHTML = `
    <div style="margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #333;font-size:13px;color:#aaa;">
      License: <strong>${license.tier}</strong>
    </div>
  `;
  app.prepend(header);
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
