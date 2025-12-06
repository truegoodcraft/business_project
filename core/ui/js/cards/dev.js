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

// core/ui/js/cards/dev.js
import { ensureToken, apiGet, apiJson, apiGetJson } from '../token.js';

export function mountDev(container) {
  container.innerHTML = `
    <div class="card">
      <h2>Settings</h2>
      <button id="btn-ping" class="btn">Ping Plugin</button>
      <pre id="ping-res" class="log"></pre>
      <div style="margin-top:12px">
        <span id="writes-state" class="badge"></span>
      </div>
    </div>`;
  wire();
}

async function wire() {
  document.getElementById('btn-ping').onclick = window.pingPlugin;
  updateWrites();
}

async function updateWrites() {
  const s = await apiGetJson('/dev/writes');
  document.getElementById('writes-state').textContent = s.enabled ? 'writes: ON' : 'writes: OFF';
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
