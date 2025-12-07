// Copyright (C) 2025 BUS Core Authors
// SPDX-License-Identifier: AGPL-3.0-or-later

// core/ui/js/router.js
const routes = {};

export function registerRoute(path, render) {
  routes[path] = render;
}

export function navigate(path) {
  if (location.hash !== `#${path}`) location.hash = `#${path}`;
  render();
}

function render() {
  const hash = location.hash.replace(/^#/, '');
  // Normalize: remove trailing slash
  let path = hash.replace(/\/$/, '');
  if (!path) path = '/inventory';

  // 1. Exact Match
  if (routes[path]) {
    routes[path](null, null); // Invoke handler, no DOM clearing
    return;
  }

  // 2. Regex / Deep Link Match
  const inventoryMatch = path.match(/^\/inventory\/(.+)$/);
  if (inventoryMatch && routes['/inventory']) {
    routes['/inventory'](null, inventoryMatch[1]);
    return;
  }

  const contactsMatch = path.match(/^\/contacts\/(.+)$/);
  if (contactsMatch && routes['/contacts']) {
    routes['/contacts'](null, contactsMatch[1]);
    return;
  }

  const recipesMatch = path.match(/^\/recipes\/(.+)$/);
  if (recipesMatch && routes['/recipes']) {
    routes['/recipes'](null, recipesMatch[1]);
    return;
  }

  const runsMatch = path.match(/^\/runs\/(.+)$/);
  if (runsMatch && routes['/runs']) {
    routes['/runs'](null, runsMatch[1]);
    return;
  }

  const mfgMatch = path.match(/^\/manufacturing\/(.+)$/);
  if (mfgMatch && routes['/manufacturing']) {
    routes['/manufacturing'](null, mfgMatch[1]);
    return;
  }

  // Fallback / 404
  console.warn('Route not found:', path);
  if (routes['/inventory']) {
     routes['/inventory']();
  }
}

window.addEventListener('hashchange', render);
window.addEventListener('DOMContentLoaded', render);
