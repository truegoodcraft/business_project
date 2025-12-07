// SPDX-License-Identifier: AGPL-3.0-or-later
// TGC BUS Core (Business Utility System Core)
// Copyright (C) 2025 True Good Craft
//
// This file is part of TGC BUS Core.
//
// TGC BUS Core is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// TGC BUS Core is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

import { ensureToken } from "./js/token.js";
import { registerRoute, resolve } from "./js/router.js";
import { mountBackupExport } from "./js/cards/backup.js";
import { mountAdmin } from "./js/cards/admin.js";
import mountVendors from "./js/cards/vendors.js";
import { mountHome } from "./js/cards/home.js";
import "./js/cards/home_donuts.js";
import { mountInventory, unmountInventory } from "./js/cards/inventory.js";
import { mountManufacturing, unmountManufacturing } from "./js/cards/manufacturing.js";
import { mountRecipes, unmountRecipes } from "./js/cards/recipes.js";
import { settingsCard } from "./js/cards/settings.js";

// --- Route Registration ---

// Home
registerRoute('^home$', showHome);

// Inventory
registerRoute('^inventory$', () => showInventory());
registerRoute('^inventory/([^/]+)$', (id) => showInventory(id));

// Contacts
registerRoute('^contacts$', () => showContacts());
registerRoute('^contacts/([^/]+)$', (id) => showContacts(id));

// Recipes
registerRoute('^recipes$', () => showRecipes());
registerRoute('^recipes/([^/]+)$', (id) => showRecipes(id));

// Runs (Manufacturing)
registerRoute('^runs$', () => showManufacturing());
registerRoute('^runs/([^/]+)$', (id) => showManufacturing(id));
registerRoute('^manufacturing$', () => showManufacturing()); // Alias/Compat

// Settings & Admin
registerRoute('^settings$', showSettings);
registerRoute('^admin$', showAdmin);
registerRoute('^import$', showSettings); // Mapping import to settings for now as no dedicated screen

// Default root
registerRoute('^$', () => showInventory());

// --- Navigation Logic ---

function getHash() {
  return window.location.hash || '';
}

const setActiveNav = (route) => {
  document.querySelectorAll('[data-role="nav-link"]').forEach(a => {
    // Basic active check - this might need refinement for regex routes
    // For now, we match if the route attribute matches part of the hash
    const target = a.getAttribute('data-route');
    const hash = window.location.hash.replace('#/', '');
    const is = target && hash.startsWith(target);
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
  const root = document.getElementById('card-root')
    || document.getElementById('tools-root')
    || document.getElementById('main-root');
  const inventoryHost = document.querySelector('[data-role="inventory-root"]');
  const contactsHost = document.querySelector('[data-view="contacts"]');
  const settingsHost = document.querySelector('[data-role="settings-root"]');
  const manufacturingHost = document.querySelector('[data-tab-panel="manufacturing"]');
  const recipesHost = document.querySelector('[data-tab-panel="recipes"]');
  const adminHost = document.querySelector('[data-role="admin-root"]');

  // Note: We don't necessarily want to clear innerHTML if the card handles its own mounting/unmounting efficiency.
  // But per existing logic, we clear or unmount.

  // Existing logic called unmount functions. We should continue that.
}

async function onRouteChange() {
  await ensureToken();
  const hash = getHash();

  // Update nav active state (heuristic)
  const routeName = hash.replace('#/', '').split('/')[0] || 'inventory';
  setActiveNav(routeName);

  document.querySelector('[data-role="settings-screen"]')?.classList.add('hidden');
  // clearCardHost(); // Handled by individual show functions via unmount*

  // Delegate to router
  resolve(hash);
}

window.addEventListener('hashchange', () => {
  onRouteChange().catch(err => console.error('route change failed', err));
});
window.addEventListener('load', () => {
  onRouteChange().catch(err => console.error('route change failed', err));
});

if (!location.hash) location.hash = '#/inventory';

// --- Error Handling ---

window.addEventListener('bus-error', (event) => {
  const { type, message, status } = event.detail;

  if (status >= 500 || type === 'network') {
    const banner = document.getElementById('global-error-banner');
    if (banner) {
      banner.classList.remove('hidden');
      const msgEl = banner.querySelector('.error-message');
      if (msgEl) msgEl.textContent = message || 'An unexpected error occurred.';
    }
  }
});

// Dismiss button logic is in the HTML onclick or we add listener here
document.addEventListener('DOMContentLoaded', () => {
  const dismissBtn = document.querySelector('[data-action="dismiss-error"]');
  if (dismissBtn) {
    dismissBtn.addEventListener('click', () => {
      document.getElementById('global-error-banner')?.classList.add('hidden');
    });
  }
});


document.addEventListener('DOMContentLoaded', async () => {
  try {
    await ensureToken();
    console.log('BOOT OK');
  } catch (e) {
    console.error('BOOT FAIL', e);
  }
});

// --- View Functions ---

async function showContacts(id) {
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
  // If ID is present, we might want to scroll to it or open it.
  // Assuming mountVendors or related logic handles it or we pass it down if supported.
}

async function showInventory(id) {
  document.querySelector('[data-role="home-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="settings-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="recipes-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="manufacturing-screen"]')?.classList.add('hidden');
  document.querySelector('[data-role="admin-screen"]')?.classList.add('hidden');
  unmountManufacturing();
  unmountRecipes();
  document.querySelector('[data-role="inventory-screen"]')?.classList.remove('hidden');
  mountInventory(id); // Pass ID
}

async function showManufacturing(id) {
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
  await mountManufacturing(id); // Pass ID
}

async function showAdmin() {
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
  await mountRecipes(id); // Pass ID
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
