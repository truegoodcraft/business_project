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
  const path = location.hash.replace(/^#/, '') || '/manufacturing';
  const target = document.getElementById('app');
  const fn = routes[path] || routes['/manufacturing'];
  target.innerHTML = '';
  fn(target);
}

window.addEventListener('hashchange', render);
window.addEventListener('DOMContentLoaded', render);
