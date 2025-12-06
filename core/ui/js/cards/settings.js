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
      <p class="muted">No settings available in this version.</p>
    </div>
  `;
  el.appendChild(root);
}
