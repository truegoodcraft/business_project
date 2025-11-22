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
import { mountBackupExport } from "./js/cards/backup.js";
import mountVendors, { mountContacts } from "./js/cards/vendors.js";
import { mountHome } from "./js/cards/home.js";
import "./js/cards/home_donuts.js";
import { mountInventory, unmountInventory } from "./js/cards/inventory.js";
import { settingsCard } from "./js/cards/settings.js";

const getRoute = () => {
  let route = location.hash.replace('#/', '');
  if (route === '' || route === 'home' || route === 'BUSCore') route = 'home';
  return route.split(/[\/?]/)[0] || 'home';
};

const setActiveNav = (route) => {
  document.querySelectorAll('[data-role="nav-link"]').forEach(a => {
    const is = a.getAttribute('data-route') === route;
    a.classList.toggle('active', !!is);
  });
};

function showScreen(name) {
  const home = document.querySelector('[data-role="home-screen"]');
  const tools = document.querySelector('[data-role="tools-screen"]');
  if (home)  home.classList.toggle('hidden',  name !== 'home');
  if (tools) tools.classList.toggle('hidden', name !== 'tools');
}

let contactsMounted = false;
let settingsMounted = false;

const ensureContactsMounted = async () => {
  if (contactsMounted) return;
  const host = document.querySelector('[data-view="contacts"]');
  if (!host) return;
  await mountVendors(host);
  contactsMounted = true;
};

const onRouteChange = async () => {
  const route = getRoute();
  setActiveNav(route);

  document.querySelector('[data-role="settings-screen"]')?.classList.add('hidden');

  if (route === 'contacts') {
    // Close Tools drawer if open
    document.querySelector('[data-role="tools-subnav"]')?.classList.add('hidden');

    // Hide legacy Tools screens if any
    document.querySelector('[data-role="tools-screen"]')?.classList.add('hidden');

    // Show Contacts page
    mountContacts();
    await ensureContactsMounted();
    return;
  }

  if (route === 'inventory') {
    // Show Inventory only
    document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
    mountInventory();
    return;
  }

  if (route === 'settings') {
    unmountInventory();
    document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
    showScreen(null);
    const settingsScreen = document.querySelector('[data-role="settings-screen"]');
    settingsScreen?.classList.remove('hidden');
    if (!settingsMounted) {
      const host = document.querySelector('[data-role="settings-root"]');
      if (host) {
        settingsCard(host);
        settingsMounted = true;
      }
    }
    return;
  }

  if (route === 'home' || route === '') {
    showScreen('home');   // show only Home
    mountHome();          // keep existing Home logic
    unmountInventory();   // ensure Inventory hides when returning Home
    document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
    return;
  }

  unmountInventory();
  document.querySelector('[data-role="contacts-screen"]')?.classList.add('hidden');
  showScreen(null);
  return;
};

const safeRouteChange = () => {
  onRouteChange().catch(err => console.error('route change failed', err));
};

window.addEventListener('hashchange', safeRouteChange);
window.addEventListener('load', safeRouteChange);

if (!location.hash) location.hash = '#/home';

document.addEventListener('DOMContentLoaded', async () => {
  try {
    await ensureToken();
    await initLicenseBadge();
    await onRouteChange();
    console.log('BOOT OK');
  } catch (e) {
    console.error('BOOT FAIL', e);
  }
});

// Tools drawer toggle + selection handling
(function initToolsDrawer() {
  const toolsToggle = document.querySelector('[data-action="toggle-tools"]');
  const drawer = document.querySelector('[data-role="tools-subnav"]');
  const inventoryLink = document.querySelector('[data-link="tools-inventory"]');
  const contactsLink = document.querySelector('[data-link="tools-contacts"], a[href="#/contacts"]');

  if (toolsToggle && drawer) {
    toolsToggle.addEventListener('click', (e) => {
      e.preventDefault();
      drawer.classList.toggle('hidden');
    });
  }

  if (inventoryLink && drawer) {
    inventoryLink.addEventListener('click', () => {
      drawer.classList.add('hidden');
    });
  }

  if (contactsLink && drawer) {
    contactsLink.addEventListener('click', () => drawer?.classList.add('hidden'));
  }

  window.addEventListener('hashchange', () => {
    if (drawer) drawer.classList.add('hidden');
  });
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
