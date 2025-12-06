// SPDX-License-Identifier: AGPL-3.0-or-later
// TGC BUS Core (Business Utility System Core)
// Copyright (C) 2025 True Good Craft

// core/ui/js/cards/dev.js
import { ensureToken, apiGet } from '../token.js';

export function mountDev(container) {
  container.innerHTML = `
    <div class="card">
      <h2>Settings</h2>
      <button id="btn-ping" class="btn">Ping Plugin</button>
      <pre id="ping-res" class="log"></pre>
      </div>`;
  wire();
}

async function wire() {
  document.getElementById('btn-ping').onclick = window.pingPlugin;
  // Writes toggle logic removed
}

// global for shell.html onclick compatibility
window.pingPlugin = async () => {
  const out = document.getElementById('ping-res');
  try {
    await ensureToken();
    const res = await apiGet('/health');
    out && (out.textContent = `status ${res.status}`);
    return res.status;
  } catch (e) {
    out && (out.textContent = 'error: ' + e);
    return 0;
  }
};
