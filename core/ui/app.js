import { ensureToken, apiGet, apiJson, apiGetJson } from "./js/token.js";
import { mountWrites }    from "/ui/js/cards/writes.js";
import { mountOrganizer } from "/ui/js/cards/organizer.js";
import { mountBackup }    from "/ui/js/cards/backup.js";
import { mountInventory } from "/ui/js/cards/inventory.js";
import { mountRfq }       from "/ui/js/cards/rfq.js";
import { mountDev }       from "/ui/js/cards/dev.js";
import { mountSettings }  from "/ui/js/cards/settings.js";
import * as ContactsCard  from "/ui/js/cards/vendors.js";

const app = document.getElementById("app");
let headerHost = null;
let cardHost = null;
let currentTab = "writes";
let sessionToken = "";
let licenseInfo = null;
let writesState = null;
let wBadge = null;
let tokenDisplay = null;

const mountContacts =
  ContactsCard.mountContacts || ContactsCard.mount || ContactsCard.default;

const CONTACT_ROUTE_HASHES = new Set([
  '#/tools/contacts',
  '#/tools/vendors',
  '#/vendors',
  '#/contacts',
]);

const tabs = {
  writes: async (ctx) => mountWrites(cardHost, ctx),
  tools: async () => {
    cardHost.innerHTML = `
      <div class="card"><h2>Tools</h2><p>Select a tool:</p></div>
      <div class="card" onclick="window.bus.mountOrganizer()">Organizer</div>
      <div class="card" onclick="window.bus.mountBackup()">Backup</div>
      <div class="card" onclick="window.bus.mountInventory()">Inventory</div>
      <div class="card" onclick="window.bus.mountRfq()">RFQ</div>
      <div class="card" onclick="window.bus.mountSettings()">Settings</div>
    `;
  },
  dev: async () => mountDev(cardHost),
  inventory: async () => mountInventory(cardHost),
  'tools-contacts': async (ctx) => {
    if (typeof mountContacts === 'function') {
      await mountContacts(cardHost, ctx);
    }
  },
};

const routeTable = new Map([
  ["#/inventory", () => switchTab("inventory")],
  ["#/tools/contacts", () => switchTab("tools-contacts")],
  ["#/tools/vendors", () => switchTab("tools-contacts")],
  ["#/vendors", () => switchTab("tools-contacts")],
  ["#/contacts", () => switchTab("tools-contacts")],
]);

document.addEventListener('DOMContentLoaded', async () => {
  try {
    await ensureToken();        // wait for session token first
    await init();               // existing init logic unchanged
    console.log('BOOT OK');
  } catch (e) {
    console.error('BOOT FAIL', e);
  }
});

window.addEventListener('hashchange', () => {
  handleRoute(window.location.hash);
});

window.addEventListener('bus:token-ready', (event) => {
  sessionToken = event?.detail?.token || localStorage.getItem('bus.token') || '';
  updateTokenDisplay();
});

async function init() {
  try {
    setupSessionBar();
    headerHost = document.createElement('div');
    headerHost.id = 'card-header';
    cardHost = document.createElement('div');
    cardHost.id = 'card-host';
    app.replaceChildren(headerHost, cardHost);

    await refreshWrites();
    await checkHealth();
    bindTabs();
    if (!(await handleRoute(window.location.hash))) {
      await switchTab(currentTab);
    }
  } catch (e) {
    console.error('BOOT FAILED', e);
    app.innerHTML = `<pre style="color:red;">${e}</pre>`;
  }
}

function setupSessionBar() {
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
  const wBtn = document.createElement('button');
  wBtn.className = 'btn';
  wBtn.textContent = 'Toggle Writes';
  wBadge = document.createElement('span');
  tokenDisplay = document.createElement('span');
  tokenDisplay.title = 'session token used for requests';
  updateTokenDisplay();
  bar.replaceChildren(tokenDisplay, wBtn, wBadge);

  wBtn.onclick = async () => {
    try {
      const s = await apiGetJson('/dev/writes');
      await apiJson('/dev/writes', { enabled: !s.enabled });
      await refreshWrites();
      await renderView();
    } catch (err) {
      console.error(err);
    }
  };
}

function updateTokenDisplay() {
  if (!tokenDisplay) return;
  const token = sessionToken || localStorage.getItem('bus.token') || '';
  tokenDisplay.textContent = token ? `token… ${token.slice(0, 8)}` : 'token… none';
}

async function refreshWrites() {
  try {
    const s = await apiGetJson('/dev/writes');
    const enabled = Boolean(s?.enabled);
    writesState = { enabled };
    if (wBadge) wBadge.textContent = enabled ? 'WRITES: ON' : 'WRITES: OFF';
    document.body.dataset.writesEnabled = enabled ? 'true' : 'false';
  } catch (err) {
    writesState = null;
    if (wBadge) wBadge.textContent = 'WRITES: ?';
    document.body.dataset.writesEnabled = 'unknown';
    console.error(err);
  }
}

async function refreshLicense() {
  try {
    licenseInfo = await apiGetJson('/dev/license');
  } catch (err) {
    licenseInfo = null;
    console.error('license fetch failed', err);
  }
}

async function renderHeader() {
  if (!headerHost) return;
  headerHost.innerHTML = '';
  const header = document.createElement('div');
  header.innerHTML = `
    <div style="margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #333;font-size:13px;color:#aaa;">
      License: <strong>${licenseInfo?.tier ?? 'unknown'}</strong>
    </div>
  `;
  headerHost.append(header);
}

function bindTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', (event) => {
      event.preventDefault();
      const tabId = tab.dataset.tab;
      if (!tabId) return;
      if (tabId === 'inventory') {
        if (window.location.hash !== '#/inventory') {
          window.location.hash = '#/inventory';
        } else {
          switchTab('inventory');
        }
      } else if (tabId === 'tools-contacts') {
        if (!CONTACT_ROUTE_HASHES.has(window.location.hash)) {
          window.location.hash = '#/tools/contacts';
        } else {
          switchTab('tools-contacts');
        }
      } else {
        if (window.location.hash === '#/inventory' || CONTACT_ROUTE_HASHES.has(window.location.hash)) {
          history.replaceState(null, '', window.location.pathname + window.location.search);
        }
        switchTab(tabId);
      }
    });
  });
}

async function switchTab(id) {
  if (!cardHost) return;
  currentTab = id;
  document.querySelectorAll('.tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.tab === id);
  });
  const hash = window.location.hash;
  const isInventoryHash = hash === '#/inventory';
  const isContactsHash = CONTACT_ROUTE_HASHES.has(hash);
  if (id !== 'inventory' && isInventoryHash) {
    history.replaceState(null, '', window.location.pathname + window.location.search);
  }
  if (id !== 'tools-contacts' && isContactsHash) {
    history.replaceState(null, '', window.location.pathname + window.location.search);
  }
  await renderView();
}

async function renderView() {
  if (!cardHost) return;
  cardHost.innerHTML = '';
  await refreshLicense();
  await renderHeader();
  const ctx = { license: licenseInfo, writes: writesState };
  const fn = tabs[currentTab];
  if (fn) await fn(ctx);
}

async function checkHealth() {
  try {
    const res = await apiGet('/health');
    console.log('health', res.status);
  } catch (err) {
    console.error('health error', err);
  }
}

async function handleRoute(hash) {
  const handler = routeTable.get(hash);
  if (handler) {
    await handler();
    return true;
  }
  return false;
}

window.bus = Object.freeze({
  mountWrites:    () => switchTab('writes'),
  mountOrganizer: () => switchTab('tools').then(() => mountOrganizer(cardHost)),
  mountBackup:    () => switchTab('tools').then(() => mountBackup(cardHost)),
  mountInventory: () => {
    if (window.location.hash !== '#/inventory') {
      window.location.hash = '#/inventory';
    } else {
      switchTab('inventory');
    }
  },
  mountRfq:       () => switchTab('tools').then(() => mountRfq(cardHost)),
  mountSettings:  () => switchTab('tools').then(() => mountSettings(cardHost)),
  mountDev:       () => switchTab('dev'),
  mountContacts:  () => {
    if (!CONTACT_ROUTE_HASHES.has(window.location.hash)) {
      window.location.hash = '#/tools/contacts';
    } else {
      switchTab('tools-contacts');
    }
  },
});
