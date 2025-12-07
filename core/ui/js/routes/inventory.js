// Copyright (C) 2025 BUS Core Authors
// SPDX-License-Identifier: AGPL-3.0-or-later

// core/ui/js/routes/inventory.js
import { registerRoute } from '../router.js';

registerRoute('/inventory', (root) => {
  const wrap = document.createElement('div');
  wrap.innerHTML = `<h3 style="margin-top:0">Inventory</h3><p>Inventory management remains available in the legacy shell. Manufacturing now lives at <code>#/manufacturing</code>.</p>`;
  root.append(wrap);
});
