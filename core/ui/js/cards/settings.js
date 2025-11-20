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

import { apiJson, apiGetJson, apiJsonJson } from '../token.js';
export async function mountSettings(el){
  el.innerHTML = `
    <h2>Settings</h2>
    <div style="margin-bottom:16px;">
      <label>Writes:</label>
      <button class="btn" id="writesBtn">toggle</button>
      <span id="writesLabel"></span>
    </div>
    <div class="card" style="padding:12px;">
      <h3>Business Profile</h3>
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
      <div style="margin-top:10px;">
        <button class="btn" id="bpSave">Save Business Profile</button>
        <span id="bpStatus" style="margin-left:8px;color:var(--text-muted);"></span>
      </div>
    </div>
  `;
  const btn = el.querySelector('#writesBtn');
  const lab = el.querySelector('#writesLabel');
  async function sync(){
    const s = await apiGetJson('/dev/writes');
    lab.textContent = s.enabled ? 'enabled' : 'disabled';
  }
  btn.onclick = async ()=>{
    const s = await apiGetJson('/dev/writes');
    await apiJson('/dev/writes', { enabled: !s.enabled });
    await sync();
  };
  await sync();

  // ---- Business Profile wiring ----
  const inputs = el.querySelectorAll('[name]');
  const statusEl = el.querySelector('#bpStatus');
  const saveBtn = el.querySelector('#bpSave');
  try {
    const current = await apiGetJson('/app/business_profile');
    inputs.forEach(i => { if (current[i.name] != null) i.value = current[i.name]; });
  } catch (_) { /* ignore */ }
  saveBtn.onclick = async () => {
    const payload = {};
    inputs.forEach(i => payload[i.name] = i.value || null);
    await apiJson('/app/business_profile', payload);
    statusEl.textContent = 'saved';
    setTimeout(() => statusEl.textContent = '', 1200);
  };
}
