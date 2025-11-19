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
import * as ContactsCard from "./js/cards/vendors.js";
import { mountHome } from "./js/cards/home.js";
import { mountTools } from "./js/cards/tools.js";
import "./js/cards/home_donuts.js";

const mountContacts =
  ContactsCard.mountContacts || ContactsCard.mount || ContactsCard.default;

const getRoute = () => {
  const h = (location.hash || '#/home').replace(/^#\/?/, '');
  const base = h.split(/[\/?]/)[0] || 'tools';
  return base;
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

const showToolsTabs = (show) => {
  const root = document.querySelector('[data-role="tools-tabs-root"]');
  if (!root) return;
  root.classList.toggle('hidden', !show);
  if (show) {
    const tabsNav = root.querySelector('[data-role="main-tabs"]');
    if (!tabsNav) return;
    const current = tabsNav.querySelector('[data-tab].active') || tabsNav.querySelector('[data-tab]');
    if (current) {
      const tab = current.getAttribute('data-tab');
      selectTab(tab);
    }
  }
};

const selectTab = (tab) => {
  const root = document.querySelector('[data-role="tools-tabs-root"]');
  if (!root) return;
  root.querySelectorAll('[data-role="main-tabs"] [data-tab]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === tab);
  });
  root.querySelectorAll('[data-tab-panel]').forEach(p => {
    p.classList.toggle('hidden', p.getAttribute('data-tab-panel') !== tab);
  });
};

document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-role="main-tabs"] [data-tab]');
  if (btn) {
    e.preventDefault();
    selectTab(btn.getAttribute('data-tab'));
  }
});

let contactsMounted = false;

const ensureContactsMounted = async () => {
  if (contactsMounted) return;
  const host = document.querySelector('[data-view="contacts"]');
  if (!host || typeof mountContacts !== 'function') return;
  await mountContacts(host);
  contactsMounted = true;
};

const onRouteChange = async () => {
  const route = getRoute();
  setActiveNav(route);

  if (route === 'home' || route === '') {
    showScreen('home');   // show only Home
    mountHome();          // keep existing Home logic
    return;
  }

  const isTools = (route === 'tools');
  showToolsTabs?.(isTools);

  if (!isTools) {
    showScreen(null);
    return;
  }

  showScreen('tools');
  mountTools();
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

// Toggle Tools subnav and avoid blue/bright active style
(function initToolsSubnav() {
  const toolsNav = document.querySelector('[data-role="nav-tools"] > a[data-link="tools"]');
  const subnav = document.querySelector('[data-role="tools-subnav"]');

  if (toolsNav && subnav) {
    toolsNav.addEventListener('click', () => {
      subnav.classList.remove('hidden');
    });

    window.addEventListener('hashchange', () => {
      const route = location.hash.replace('#/', '');
      if (route !== 'tools') {
        subnav.classList.add('hidden');
      }
    });
  }

  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-link]');
    if (!a) return;
    a.setAttribute('data-active-neutral', '1');
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
