// Copyright (C) 2025 BUS Core Authors
// SPDX-License-Identifier: AGPL-3.0-or-later

// core/ui/js/router.js
const routes = {};

export function registerRoute(path, render) {
  // Store exact path matches.
  // Path can be a string or regex logic in future, but for now we store by string key for direct lookups
  // and handle regex manually in render for deep links.
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

  const target = document.getElementById('app');

  // 1. Exact Match
  if (routes[path]) {
    // If route handler accepts args (target, id), we pass them.
    // For standard routes, it might be just (target) or nothing.
    routes[path](target, null);
    return;
  }

  // 2. Regex / Deep Link Match
  // We manually check known deep link patterns and invoke the registered base handler with the extracted ID.

  const inventoryMatch = path.match(/^\/inventory\/(.+)$/);
  if (inventoryMatch && routes['/inventory']) {
    routes['/inventory'](target, inventoryMatch[1]);
    return;
  }

  const contactsMatch = path.match(/^\/contacts\/(.+)$/);
  if (contactsMatch && routes['/contacts']) {
    routes['/contacts'](target, contactsMatch[1]);
    return;
  }

  const recipesMatch = path.match(/^\/recipes\/(.+)$/);
  if (recipesMatch && routes['/recipes']) {
    routes['/recipes'](target, recipesMatch[1]);
    return;
  }

  const runsMatch = path.match(/^\/runs\/(.+)$/);
  if (runsMatch && routes['/runs']) {
    routes['/runs'](target, runsMatch[1]);
    return;
  }

  const mfgMatch = path.match(/^\/manufacturing\/(.+)$/);
  if (mfgMatch && routes['/manufacturing']) {
    routes['/manufacturing'](target, mfgMatch[1]);
    return;
  }

  // Fallback / 404
  console.warn('Route not found:', path);
  if (routes['/inventory']) {
     routes['/inventory'](target);
  }
}

window.addEventListener('hashchange', render);
window.addEventListener('DOMContentLoaded', render);
