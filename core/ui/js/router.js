// Copyright (C) 2025 BUS Core Authors
// SPDX-License-Identifier: AGPL-3.0-or-later

// core/ui/js/router.js

const registry = [];
const aliases = {
  'dashboard': 'home',
  'items': 'inventory'
};

export function registerRoute(pattern, callback) {
  // Convert string pattern to RegExp if it isn't one
  const regex = pattern instanceof RegExp ? pattern : new RegExp(pattern);
  registry.push({ regex, callback });
}

function render404() {
  const app = document.getElementById('app');
  if (app) {
    app.innerHTML = `
      <div class="card">
        <h2>404 - Not Found</h2>
        <p>The requested page could not be found.</p>
        <a href="#/home" class="btn">Go Home</a>
      </div>
    `;
  }
}

export function resolve(hash) {
  // Normalize hash (remove # and leading /)
  let path = (hash || '').replace(/^#\/?/, '');

  // Handle empty path -> inventory (default, though app.js might handle this too)
  // SoT doesn't explicitly say what empty hash does in router, but app.js handles it.
  // We'll let app.js pass the hash. If it's empty string, we might want to handle it or let app.js set default.
  // app.js currently does: if (!location.hash) location.hash = '#/inventory';
  // So path will likely not be empty.

  // Check for strict aliases
  if (aliases[path]) {
    location.hash = `#/${aliases[path]}`;
    return;
  }

  // Iterate patterns
  for (const route of registry) {
    const match = path.match(route.regex);
    if (match) {
      // Execute callback with extracted params (groups)
      // match[0] is full match, match[1...] are groups
      const params = match.slice(1);
      route.callback(...params);
      return;
    }
  }

  // If no match -> render 404 View
  render404();
}

export function navigate(path) {
  location.hash = `#/${path.replace(/^\//, '')}`;
}
