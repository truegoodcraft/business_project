// SPDX-License-Identifier: AGPL-3.0-or-later
// TGC BUS Core (Business Utility System Core)
// Copyright (C) 2025 True Good Craft

import { ensureToken } from "./js/token.js";
import { registerRoute, navigate } from "./js/router.js"; // Import router
import { mountBackupExport } from "./js/cards/backup.js";
import { mountAdmin } from "./js/cards/admin.js";
import mountVendors from "./js/cards/vendors.js";
import { mountHome } from "./js/cards/home.js";
import "./js/cards/home_donuts.js";
import { mountInventory, unmountInventory, openItemModal, openItemById } from "./js/cards/inventory.js";
import { mountManufacturing, unmountManufacturing } from "./js/cards/manufacturing.js";
import { mountRecipes, unmountRecipes } from "./js/cards/recipes.js";
import { settingsCard } from "./js/cards/settings.js";

// Note: router.js handles the hashchange event and calls these registered functions.
// We just need to register them.

registerRoute('/inventory', (target, id) => showInventory(id));
registerRoute('/manufacturing', (target, id) => showManufacturing(id));
registerRoute('/runs', (target, id) => showManufacturing(id)); // alias
registerRoute('/recipes', (target, id) => showRecipes(id));
registerRoute('/contacts', (target, id) => showContacts(id));
registerRoute('/settings', showSettings);
registerRoute('/admin', showAdmin);
registerRoute('/home', showHome);
registerRoute('/', showInventory);

const setActiveNav = (route) => {
  document.querySelectorAll('[data-role="nav-link"]').forEach(a => {
    // Route matching is simple string match for now
    const target = a.getAttribute('data-route');
    const is = target && route.includes(target); // loose match
    a.classList.toggle('active', !!is);
  });
};

function showScreen(name) {
  const home = document.querySelector('[data-role="home-screen"]');
  const tools = document.querySelector('[data-role="tools-screen"]');
  if (home)  home.classList.toggle('hidden',  name !== 'home');
  if (tools) tools.classList.toggle('hidden', name !== 'tools');
}

let settingsMounted = false;

const ensureContactsMounted = async () => {
  const host = document.querySelector('[data-view="contacts"]');
  if (!host) return;
  await mountVendors(host);
};

function clearCardHost() {
  // We rely on individual show functions to toggle visibility and mount/unmount.
  // We don't indiscriminately clear everything because some cards (like home) persist.
}

// Error Listener
window.addEventListener('bus-error', (event) => {
  const { type, message, status } = event.detail;
  const banner = document.getElementById('global-error-banner');
  if (banner) {
    banner.textContent = message || `Error ${status}`;
    banner.classList.remove('hidden');
    // Auto hide after 5s or add dismiss button? SoT says "Persistent error banner".
    // We'll leave it persistent for 5xx.
  }
});

// We no longer handle 'hashchange' here manually for routing, as router.js does it.
// BUT router.js `render` calls the registered function.
// We need to make sure `onRouteChange` logic (auth, nav state) still happens.
// We can hook into the functions themselves.

async function preRoute(hash) {
  await ensureToken();
  const route = hash.replace('#/', '').split('/')[0] || 'inventory';
  setActiveNav(route);
  document.querySelector('[data-role="settings-screen"]')?.classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    await ensureToken();
    console.log('BOOT OK');
  } catch (e) {
    console.error('BOOT FAIL', e);
  }
});

async function showContacts(id) {
  await preRoute('contacts');
  // Close Tools drawer if open
  document.querySelector('[data-role="tools-subnav"]')?.classList.remove('open');
  unmountInventory();
  unmountManufacturing();
  unmountRecipes();
  document.querySelector('[data-role="home-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="inventory-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="recipes-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="manufacturing-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="admin-screen"]')?.classList.add('hidden');
  const contactsScreen = document.querySelector('[data-role="contacts-screen"]');
  contactsScreen?.classList.remove('hidden');
  await ensureContactsMounted();

  if (id) {
    // If vendors.js exposes a way to open by ID, call it.
    // Assuming mountVendors returns or we can access a helper.
    // Currently vendors.js default export is mountContacts.
    // It doesn't easily expose the internal state.
    // We'll skip deep linking for Contacts for now unless we edit vendors.js significantly.
  }
}

async function showInventory(id) {
  await preRoute('inventory');
  document.querySelector('[data-role="home-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="settings-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="recipes-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="manufacturing-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="admin-screen"]')?.classList.add('hidden');
  unmountManufacturing();
  unmountRecipes();
  document.querySelector('[data-role="inventory-screen"]')?.classList.remove('hidden');
  await mountInventory(); // Await the mount

  if (id) {
    openItemById(id);
  }
}

async function showManufacturing(id) {
  await preRoute('manufacturing');
  document.querySelector('[data-role="home-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="settings-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="recipes-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="inventory-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="admin-screen"]')?.classList.add('hidden');
  const screen = document.querySelector('[data-role="manufacturing-screen"]');
  screen?.classList.remove('hidden');
  unmountInventory();
  unmountRecipes();
  await mountManufacturing();
}

async function showAdmin() {
  await preRoute('admin');
  document.querySelector('[data-role="home-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="settings-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="inventory-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="manufacturing-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="recipes-screen"]')?.classList.add('hidden');
  unmountInventory();
  unmountManufacturing();
  unmountRecipes();
  const adminScreen = document.querySelector('[data-role="admin-screen"]');
  adminScreen?.classList.remove('hidden');
  const host = document.querySelector('[data-role="admin-root"]');
  if (host) mountAdmin(host);
}

async function showSettings() {
  await preRoute('settings');
  unmountInventory();
  unmountManufacturing();
  unmountRecipes();
  document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
  showScreen(null);
  document.querySelector('[data-role="manufacturing-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="recipes-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="admin-screen"]')?.classList.add('hidden');
  const settingsScreen = document.querySelector('[data-role="settings-screen"]');
  settingsScreen?.classList.remove('hidden');
  if (!settingsMounted) {
    const host = document.querySelector('[data-role="settings-root"]');
    if (host) {
      settingsCard(host);
      settingsMounted = true;
    }
  }
}

async function showHome() {
  await preRoute('home');
  showScreen('home');   // show only Home
  mountHome();          // keep existing Home logic
  unmountInventory();   // ensure Inventory hides when returning Home
  document.querySelector('[data-role="inventory-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
  unmountManufacturing();
  unmountRecipes();
  document.querySelector('[data-role="manufacturing-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="admin-screen"]')?.classList.add('hidden');
}

async function showRecipes(id) {
  await preRoute('recipes');
  document.querySelector('[data-role="home-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="settings-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="inventory-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="manufacturing-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="admin-screen"]')?.classList.add('hidden');
  const recipesScreen = document.querySelector('[data-role="recipes-screen"]');
  recipesScreen?.classList.remove('hidden');
  unmountInventory();
  unmountManufacturing();
  await mountRecipes();
}

// Tools drawer: open on hover, click locks/unlocks
(function initToolsDrawer() {
  const navTools     = document.querySelector('[data-role="nav-tools"]');
  const toolsToggle  = document.querySelector('[data-action="toggle-tools"]');
  const drawer       = document.querySelector('[data-role="tools-subnav"]');
  const inventoryLink= document.querySelector('[data-link="tools-inventory"]');
  const manufacturingLink = document.querySelector('[data-link="tools-manufacturing"]');
  const recipesLink = document.querySelector('[data-link="tools-recipes"]');
  const contactsLink = document.querySelector('[data-link="tools-contacts"], a[href="#/contacts"]');

  if (!navTools || !drawer) return;

  let locked = false;

  // Hover behavior
  navTools.addEventListener('mouseenter', () => {
    drawer.classList.add('open');
  });
  navTools.addEventListener('mouseleave', () => {
    if (!locked) drawer.classList.remove('open');
  });

  // Click to lock/unlock (SoT-compatible)
  if (toolsToggle) {
    toolsToggle.addEventListener('click', (e) => {
      e.preventDefault();
      locked = !locked;
      drawer.classList.toggle('open', locked);
    });
  }

  // Navigating away always closes + unlocks
  const closeAndUnlock = () => { locked = false; drawer.classList.remove('open'); };
  if (inventoryLink) inventoryLink.addEventListener('click', closeAndUnlock);
  if (manufacturingLink) manufacturingLink.addEventListener('click', closeAndUnlock);
  if (recipesLink) recipesLink.addEventListener('click', closeAndUnlock);
  if (contactsLink)  contactsLink.addEventListener('click', closeAndUnlock);
  window.addEventListener('hashchange', closeAndUnlock);
})();

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

      if (res.status === 501) {
        alert('Manufacturing is unavailable.');
        locked = true;
        btn.disabled = true;
        btn.textContent = 'Unavailable';
        if (hint) {
          hint.textContent = 'Manufacturing is unavailable.';
          hint.classList.remove('hidden');
        }
        return;
      }

      if (res.status === 404) {
        locked = true;
        btn.textContent = 'Unavailable';
        if (hint) {
          hint.textContent = 'Manufacturing is unavailable.';
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
