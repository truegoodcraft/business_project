import { ensureToken, apiGet, apiJson, apiGetJson } from "./js/token.js";
import { mountWrites }    from "./js/cards/writes.js";
import { mountOrganizer } from "./js/cards/organizer.js";
import { mountBackup, mountBackupExport }    from "./js/cards/backup.js";
import { mountInventory } from "./js/cards/inventory.js";
import { mountRfq }       from "./js/cards/rfq.js";
import { mountDev }       from "./js/cards/dev.js";
import { mountSettings }  from "./js/cards/settings.js";
import * as ContactsCard  from "./js/cards/vendors.js";

const app = document.getElementById("app");
let headerHost = null;
let cardHost = null;
let currentTab = "writes";
let sessionToken = "";
let licenseInfo = null;
let writesState = null;
let wBadge = null;
let tokenDisplay = null;
let toolsNavGroup = null;
let organizerMounted = false;
let contactsMounted = false;
let tabsInitialized = false;
let selectToolsTab = null;

const mountContacts =
  ContactsCard.mountContacts || ContactsCard.mount || ContactsCard.default;

const CONTACT_ROUTE_HASHES = new Set([
  '#/tools/contacts',
  '#/tools/vendors',
  '#/vendors',
  '#/contacts',
]);

const routeTable = new Map();
const router = {
  register(hash, handler) {
    if (handler === mountContacts && CONTACT_ROUTE_HASHES.has(hash)) {
      routeTable.set(hash, () => switchTab('tools-contacts'));
    } else {
      routeTable.set(hash, handler);
    }
  }
};

function currentHash() {
  return (location.hash || '#/').replace(/^#/, '');
}

function isToolsRoute() {
  const h = currentHash();
  return h === '/tools' || h.startsWith('/tools/');
}

function showToolsTabs(show) {
  const root = document.querySelector('[data-role="tools-tabs-root"]');
  if (!root) return;
  root.classList.toggle('hidden', !show);
}

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

router.register('#/tools',      () => switchTab('tools'));
router.register('#/inventory',  () => switchTab('inventory'));
router.register('#/tools/contacts', mountContacts);
router.register('#/tools/vendors',  mountContacts);
router.register('#/vendors',         mountContacts);
router.register('#/contacts',        mountContacts);

document.addEventListener('DOMContentLoaded', async () => {
  try {
    await ensureToken();        // wait for session token first
    if (document.querySelector('[data-role="main-tabs"]')) {
      await bootstrapMainShell();
    } else {
      await init();             // existing init logic unchanged
    }
    await onRouteChange();
    console.log('BOOT OK');
  } catch (e) {
    console.error('BOOT FAIL', e);
  }
});

window.addEventListener('hashchange', async () => {
  await onRouteChange();
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
    toolsNavGroup = document.querySelector('.nav-group[data-group="tools"]');
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

async function initLicenseBadge() {
  const el = document.querySelector('[data-role="license-badge"]');
  if (!el) return;
  try {
    const token = await ensureToken();
    const res = await fetch('/dev/license', {
      headers: { 'X-Session-Token': token },
    });
    if (!res.ok) throw new Error(String(res.status));
    const lic = await res.json();
    el.textContent = `License: ${lic?.tier || lic?.license || 'community'}`;
  } catch (err) {
    console.warn('license badge fetch failed', err);
    el.textContent = 'License: community';
  }
}

function initTabsScoped() {
  const scope = document.querySelector('[data-role="tools-tabs-root"]');
  if (!scope) return;
  const tabs = scope.querySelector('[data-role="main-tabs"]');
  const panels = scope.querySelectorAll('[data-tab-panel]');
  if (!tabs || !panels.length) return;

  if (tabsInitialized) {
    return;
  }
  tabsInitialized = true;

  const buttons = Array.from(tabs.querySelectorAll('[data-tab]'));
  const show = (name) => {
    panels.forEach((panel) => {
      const on = panel.getAttribute('data-tab-panel') === name;
      panel.classList.toggle('hidden', !on);
    });
    buttons.forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === name);
    });
  };

  tabs.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-tab]');
    if (!btn) return;
    show(btn.getAttribute('data-tab'));
  });

  selectToolsTab = show;
  show('manufacturing');
}

function initManufacturing() {
  const form = document.querySelector('[data-role="mfg-run-form"]');
  const btn = document.querySelector('[data-role="mfg-run-btn"]');
  const notes = form?.querySelector('#mfg-notes');
  const hint = document.querySelector('[data-role="mfg-hint"]');
  if (!form || !btn) return;
  if (form.dataset.mfgBound) return;
  form.dataset.mfgBound = '1';

  const originalText = btn.textContent || 'Run Manufacturing';
  let locked = false;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (locked) return;

    btn.disabled = true;
    btn.textContent = 'Running…';

    try {
      const body = {};
      const note = notes?.value?.trim();
      if (note) body.notes = note;
      const token = await ensureToken();
      const res = await fetch('/app/inventory/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': token,
        },
        body: JSON.stringify(body),
      });

      if (res.status === 501 || res.status === 403) {
        alert('Manufacturing not available on this tier.');
        locked = true;
        btn.disabled = true;
        btn.textContent = 'Unavailable';
        if (hint) {
          hint.textContent = 'Manufacturing not available on this tier.';
          hint.classList.remove('hidden');
        }
        return;
      }

      if (res.status === 404) {
        locked = true;
        btn.textContent = 'Unavailable';
        if (hint) {
          hint.textContent = 'Manufacturing not available on this tier.';
          hint.classList.remove('hidden');
        }
        return;
      }

      if (!res.ok) throw new Error(String(res.status));
      alert('Manufacturing run submitted.');
      if (notes) notes.value = '';
    } catch (err) {
      console.error('mfg run failed', err);
      alert('Could not run manufacturing.');
    } finally {
      if (locked) {
        btn.disabled = true;
      } else {
        btn.disabled = false;
        btn.textContent = originalText;
      }
      if (!locked && btn.textContent !== originalText) {
        btn.textContent = originalText;
      }
    }
  });
}

async function bootstrapMainShell() {
  await initLicenseBadge();
}

async function onRouteChange() {
  const tools = isToolsRoute();
  const hashValue = currentHash();
  showToolsTabs(tools);
  if (!tools) return;

  initTabsScoped();
  if (hashValue === '/tools') {
    selectToolsTab?.('manufacturing');
  }
  initManufacturing();
  mountBackupExport?.();

  if (typeof mountOrganizer === 'function') {
    const tasksHost = document.querySelector('[data-role="tasks-card"]');
    if (tasksHost && !organizerMounted) {
      try {
        await mountOrganizer(tasksHost);
        organizerMounted = true;
      } catch (err) {
        console.error('tasks init failed', err);
      }
    }
  }

  const contactsHost = document.querySelector('[data-view="contacts"]');
  if (contactsHost && typeof mountContacts === 'function' && !contactsMounted) {
    try {
      await mountContacts(contactsHost);
      contactsMounted = true;
    } catch (err) {
      console.error('contacts init failed', err);
    }
  }

  window.mountInventoryCard?.();
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
      } else if (tabId === 'tools') {
        if (window.location.hash !== '#/tools') {
          window.location.hash = '#/tools';
        } else {
          switchTab('tools');
          onRouteChange();
        }
      } else {
        const wasInventory = window.location.hash === '#/inventory';
        const wasContacts = CONTACT_ROUTE_HASHES.has(window.location.hash);
        const wasTools = isToolsRoute();
        if (wasInventory || wasContacts || wasTools) {
          history.replaceState(null, '', window.location.pathname + window.location.search);
          onRouteChange();
        }
        switchTab(tabId);
      }
    });
  });
}

async function switchTab(id) {
  if (!cardHost) return;
  if (id === 'tools' && window.location.hash !== '#/tools') {
    window.location.hash = '#/tools';
  }
  currentTab = id;
  document.querySelectorAll('.tab').forEach(tab => {
    const tabId = tab.dataset.tab;
    const isActive = tabId === id || (id === 'tools-contacts' && tabId === 'tools');
    tab.classList.toggle('active', isActive);
  });
  if (!toolsNavGroup) {
    toolsNavGroup = document.querySelector('.nav-group[data-group="tools"]');
  }
  const showTools = id === 'tools' || id === 'tools-contacts';
  if (toolsNavGroup) {
    toolsNavGroup.classList.toggle('open', showTools);
  }
  const hash = window.location.hash;
  const isInventoryHash = hash === '#/inventory';
  const isContactsHash = CONTACT_ROUTE_HASHES.has(hash);
  const isToolsHash = isToolsRoute();
  if (id !== 'inventory' && isInventoryHash) {
    history.replaceState(null, '', window.location.pathname + window.location.search);
  }
  if (id !== 'tools-contacts' && isContactsHash) {
    history.replaceState(null, '', window.location.pathname + window.location.search);
  }
  if (id !== 'tools' && id !== 'tools-contacts' && isToolsHash) {
    history.replaceState(null, '', window.location.pathname + window.location.search);
    showToolsTabs(false);
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
