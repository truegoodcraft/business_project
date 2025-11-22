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

import { apiGet, apiPost, ensureToken } from '../api.js';

export function settingsCard(el) {
  el.innerHTML = '';

  const root = document.createElement('div');
  root.innerHTML = `
    <div class="card">
      <div class="card-title" style="margin-bottom:8px;">Settings</div>
      <label style="display:flex;align-items:center;gap:.5rem;">
        <input id="writesToggle" type="checkbox" />
        <span>Enable local writes</span>
      </label>
      <div id="writesStatus" class="muted"></div>
    </div>
    <div class="card" style="margin-top:12px;">
      <h3 style="margin-top:0;">Business Profile</h3>
      <div class="grid" style="display:grid;grid-template-columns:repeat(2,minmax(180px,1fr));gap:8px;">
        <input name="business_name" placeholder="Business name">
        <input name="logo_path" placeholder="C:\\Users\\You\\Pictures\\logo.png">
        <input name="address_line1" placeholder="Address line 1">
        <input name="address_line2" placeholder="Address line 2">
        <input name="city" placeholder="City">
        <input name="region" placeholder="State/Region">
        <input name="postal_code" placeholder="Postal code">
        <input name="country" placeholder="Country">
        <input name="phone" placeholder="Phone">
        <input name="email" placeholder="Email">
      </div>
      <div style="margin-top:10px;display:flex;align-items:center;gap:8px;">
        <button class="btn" id="bpSave">Save Business Profile</button>
        <span id="bpStatus" style="color:var(--text-muted);"></span>
      </div>
    </div>
  `;
  el.appendChild(root);

  const toggle = root.querySelector('#writesToggle');
  const status = root.querySelector('#writesStatus');

  async function refresh() {
    try {
      toggle.disabled = true;
      await ensureToken();
      const j = await apiGet('/dev/writes');
      toggle.checked = !!j.enabled;
      status.textContent = j.enabled ? 'Writes are enabled' : 'Writes are disabled';
    } catch (err) {
      status.textContent = 'Failed to load writes setting';
      console.error(err);
    } finally {
      toggle.disabled = false;
    }
  }

  toggle.addEventListener('change', async () => {
    toggle.disabled = true;
    try {
      await ensureToken();
      await apiPost('/dev/writes', { enabled: toggle.checked });
      await refresh();
    } catch (e) {
      toggle.checked = !toggle.checked;
      status.textContent = 'Failed to update writes setting';
      console.error(e);
      alert('Could not change writes setting. Check permissions and try again.');
    } finally {
      toggle.disabled = false;
    }
  });

  refresh();

  // ---- Business Profile wiring ----
  const inputs = root.querySelectorAll('[name]');
  const statusEl = root.querySelector('#bpStatus');
  const saveBtn = root.querySelector('#bpSave');

  (async () => {
    try {
      await ensureToken();
      const current = await apiGet('/app/business_profile');
      inputs.forEach((i) => {
        if (current[i.name] != null) i.value = current[i.name];
      });
    } catch (err) {
      console.warn('Could not load business profile', err);
    }
  })();

  saveBtn.onclick = async () => {
    try {
      await ensureToken();
      const payload = {};
      inputs.forEach((i) => {
        payload[i.name] = i.value || null;
      });
      await apiPost('/app/business_profile', payload);
      statusEl.textContent = 'saved';
      setTimeout(() => (statusEl.textContent = ''), 1200);
    } catch (err) {
      console.error('Failed to save business profile', err);
      statusEl.textContent = 'save failed';
    }
  };
}
