// ui/js/cards/inventory.js
// FREE inventory table with manual Add/Edit/Delete and Adjust.
// ESM. Uses existing API helpers that inject X-Session-Token.

import { apiGet, apiPost, apiPut, apiDelete, ensureToken } from '../api.js';

export async function mountInventory(container) {
    await ensureToken();

    const UNIT_SETS = {
        ea: ['ea'],
        metric: ['mm', 'cm', 'm', 'km', 'g', 'kg', 'ml', 'l', 'm2', 'm3'],
        imperial: ['inch', 'ft', 'yd', 'mile', 'oz', 'lb', 'qt', 'gal', 'ft2', 'ft3']
    };

    const currencySelect = () => document.getElementById('price-currency');
    const unitSystemEl = () => document.getElementById('unit-system');
    const unitSelectEl = () => document.getElementById('unit-select');

    // cache used by adjust fallback
    let itemsCache = [];

    // currency symbol from UI preference
    function currencySymbol() {
        const cur = localStorage.getItem('priceCurrency') || 'USD';
        const map = { USD: '$', EUR: '€', GBP: '£', CAD: '$', AUD: '$', JPY: '¥', CNY: '¥' };
        return map[cur] || '$';
    }
    function safeUnit(u) { return (u || '').toString().toLowerCase(); }

    function fillUnitOptions(system, current) {
        const sel = unitSelectEl();
        sel.innerHTML = '';
        (UNIT_SETS[system] || []).forEach(u => {
            const opt = document.createElement('option');
            opt.value = u;
            opt.textContent = u.toUpperCase();
            if (current && current === u) opt.selected = true;
            sel.appendChild(opt);
        });
        sel.disabled = system === '' || system === 'ea';
        const hf = document.querySelector('input[name="unit"]');
        hf.value = system === 'ea' ? 'ea' : sel.value || '';
    }

    function initUnitSelectors(existingUnit) {
        const sysEl = unitSystemEl();
        const unitEl = unitSelectEl();
        const hiddenField = document.querySelector('input[name="unit"]');
        const normalizedUnit = existingUnit ? existingUnit.toLowerCase() : '';

        sysEl.value = '';
        unitEl.innerHTML = '';
        unitEl.disabled = true;
        hiddenField.value = '';

        if (normalizedUnit) {
            if (normalizedUnit === 'ea') {
                sysEl.value = 'ea';
                fillUnitOptions('ea', 'ea');
            } else if (UNIT_SETS.metric.includes(normalizedUnit)) {
                sysEl.value = 'metric';
                fillUnitOptions('metric', normalizedUnit);
            } else if (UNIT_SETS.imperial.includes(normalizedUnit)) {
                sysEl.value = 'imperial';
                fillUnitOptions('imperial', normalizedUnit);
            }
        }

        sysEl.onchange = () => fillUnitOptions(sysEl.value);
        unitEl.onchange = () => {
            hiddenField.value = sysEl.value === 'ea' ? 'ea' : unitEl.value;
        };

        fillUnitOptions(sysEl.value || '', normalizedUnit || undefined);
    }

    async function loadVendors() {
        const field = document.getElementById('vendor-field');
        const sel = document.getElementById('vendor-select');
        field.style.display = 'none';
        sel.innerHTML = '';

        try {
            const resp = await apiGet('/app/vendors');
            const list = Array.isArray(resp) ? resp : (resp?.items ?? []);
            if (!Array.isArray(list) || list.length === 0) return;

            field.style.display = '';
            sel.innerHTML = `<option value="">— none —</option>` + list.map(v => {
                const id = v.id ?? v.vendor_id ?? v.code;
                const name = v.name ?? v.title ?? String(id);
                return `<option value="${id}">${name}</option>`;
            }).join('');
        } catch {
            // hide if endpoint not available
        }
    }

    container.innerHTML = `
        <div class="inventory-controls">
            <button id="add-item-btn">+ Add Item</button>
            <button id="refresh-btn">Refresh</button>
        </div>
        <table id="items-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>SKU</th>
                    <th>Qty</th>
                    <th>Vendor</th>
                    <th>Price</th>
                    <th>Location</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>

        <!-- Edit/Create -->
        <div id="item-modal" class="modal" style="display:none">
            <div class="modal-content">
                <h3 id="modal-title">Add Item</h3>
                <form id="item-form">
                    <label>Name: <input name="name" required></label><br>
                    <label>SKU: <input name="sku"></label><br>

                    <label>Qty:
                        <input name="qty" type="number" step="0.01" required>
                    </label><br>

                    <label>Unit:
                        <div class="row-compact">
                            <select id="unit-system" required>
                                <option value="" disabled selected>Select</option>
                                <option value="ea">Each</option>
                                <option value="metric">Metric</option>
                                <option value="imperial">Imperial</option>
                            </select>
                            <select id="unit-select" required disabled></select>
                        </div>
                        <input type="hidden" name="unit">
                    </label><br>

                    <label id="vendor-field" style="display:none">Vendor:
                        <select name="vendor_id" id="vendor-select"></select>
                    </label><br>

                    <label>Price:
                        <div class="row-compact">
                            <select id="price-currency">
                                <option>USD</option><option>EUR</option><option>GBP</option>
                                <option>CAD</option><option>AUD</option><option>JPY</option>
                                <option>CNY</option>
                            </select>
                            <input name="price" type="number" step="0.01">
                        </div>
                    </label><br>

                    <label>Location: <input name="location"></label><br>

                    <input type="hidden" name="id">
                    <button type="submit" id="save-btn">Save</button>
                    <button type="button" id="cancel-btn">Cancel</button>
                </form>
            </div>
        </div>

        <!-- Adjust Qty -->
        <div id="adjust-modal" class="modal" style="display:none">
            <div class="modal-content">
                <h3>Adjust Quantity</h3>
                <form id="adjust-form">
                    <p>Current: <span id="current-qty"></span></p>
                    <label>Change:
                        <input name="delta" type="number" step="0.01" required placeholder="e.g. +5 or -2">
                    </label><br>
                    <label>Reason:
                        <input name="reason" required placeholder="e.g. Received shipment">
                    </label><br>
                    <input type="hidden" name="item_id">
                    <button type="submit">Apply</button>
                    <button type="button" id="cancel-adjust">Cancel</button>
                </form>
            </div>
        </div>
    `;

    const tbody = container.querySelector('#items-table tbody');
    let currentEditId = null;

    async function loadItems() {
        try {
            const items = await apiGet('/app/items');
            itemsCache = Array.isArray(items) ? items : [];
            renderTable(itemsCache);
        } catch (err) {
            alert('Failed to load items: ' + (err?.error || err?.message || 'unknown'));
        }
    }

    function renderTable(items) {
        const sym = currencySymbol();
        tbody.innerHTML = items.map(item => {
            const unit = safeUnit(item.unit);
            const qtyUnit = `${item.qty} ${unit || ''}`.trim();
            const vendor = item.vendor_id || '';
            const price = (item.price ?? '') === '' ? '' : `${sym}${item.price}`;
            const loc = item.location ? escapeHtml(item.location) : 'Shop';
            return `
      <tr data-id="${item.id}">
        <td>${escapeHtml(item.name || '')}</td>
        <td>${escapeHtml(item.sku || '')}</td>
        <td>${qtyUnit.toUpperCase()}</td>
        <td>${vendor}</td>
        <td>${price}</td>
        <td>${loc}</td>
        <td>
          <button class="edit-btn">Edit</button>
          <button class="adjust-btn">±</button>
          <button class="delete-btn">Delete</button>
        </td>
      </tr>
    `;
        }).join('');

        tbody.querySelectorAll('.edit-btn').forEach(btn => {
            btn.onclick = () => openEditModal(getItemFromRow(btn.closest('tr')));
        });
        tbody.querySelectorAll('.adjust-btn').forEach(btn => {
            btn.onclick = () => openAdjustModal(getItemFromRow(btn.closest('tr')));
        });
        tbody.querySelectorAll('.delete-btn').forEach(btn => {
            btn.onclick = () => deleteItem(getItemId(btn.closest('tr')));
        });
    }

    function getItemFromRow(row) {
        const id = row.dataset.id;
        const qtyUnit = row.cells[2].textContent.trim().split(/\s+/);
        const qty = parseFloat(qtyUnit[0] || '0');
        const unit = qtyUnit.slice(1).join(' ') || '';
        return {
            id: parseInt(id),
            name: row.cells[0].textContent,
            sku: row.cells[1].textContent,
            qty,
            unit: unit.toLowerCase(),
            vendor_id: row.cells[3].textContent ? parseInt(row.cells[3].textContent) : null,
            price: row.cells[4].textContent ? parseFloat(row.cells[4].textContent.replace(/[^\d.]/g, '')) : null,
            location: row.cells[5].textContent
        };
    }

    function getItemId(row) { return parseInt(row.dataset.id); }

    function openEditModal(item) {
        currentEditId = item.id || null;
        const form = document.getElementById('item-form');
        document.getElementById('modal-title').textContent = item.id ? 'Edit Item' : 'Add Item';
        form.name.value = item.name || '';
        form.sku.value = item.sku || '';
        form.qty.value = item.qty ?? 0;
        form.location.value = item.location || '';
        form.id.value = item.id ?? '';

        document.querySelector('input[name="unit"]').value = item.unit || '';
        initUnitSelectors(item.unit || '');

        const vendorField = document.getElementById('vendor-field');
        const vendorSelect = document.getElementById('vendor-select');
        if (vendorField && vendorSelect) {
            vendorField.style.display = 'none';
            vendorSelect.innerHTML = '';
        }

        loadVendors().then(() => {
            const sel = document.getElementById('vendor-select');
            if (sel) sel.value = item.vendor_id ? String(item.vendor_id) : '';
        });

        const savedCurrency = localStorage.getItem('priceCurrency') || 'USD';
        currencySelect().value = savedCurrency;

        form.price.value = item.price ?? '';

        document.getElementById('item-modal').style.display = 'block';
        document.body.classList.add('modal-open');
    }

    function openAdjustModal(item) {
        document.getElementById('current-qty').textContent = item.qty;
        const form = document.getElementById('adjust-form');
        form.item_id.value = item.id;
        form.delta.value = '';
        form.reason.value = '';
        document.getElementById('adjust-modal').style.display = 'block';
    }

    function closeModals() {
        document.getElementById('item-modal').style.display = 'none';
        document.getElementById('adjust-modal').style.display = 'none';
        document.body.classList.remove('modal-open');
    }

    async function deleteItem(id) {
        if (!confirm('Delete this item?')) return;
        try {
            await apiDelete(`/app/items/${id}`);
            loadItems();
        } catch (err) {
            alert('Delete failed: ' + (err?.error || err?.message || 'unknown'));
        }
    }

    document.getElementById('add-item-btn').onclick = () => openEditModal({});
    document.getElementById('refresh-btn').onclick = loadItems;

    function compactPayload(o) {
        const out = {};
        for (const [k, v] of Object.entries(o)) {
            if (v === '' || v === null || Number.isNaN(v)) continue;
            out[k] = v;
        }
        return out;
    }

    document.getElementById('item-form').onsubmit = async (e) => {
        e.preventDefault();
        const f = e.target;

        // remember UI currency, not sent to backend
        const curEl = document.getElementById('price-currency');
        if (curEl) localStorage.setItem('priceCurrency', curEl.value || 'USD');

        const vendorVal = document.getElementById('vendor-select')?.value || '';

        // build base data from form
        let data = {
            name: f.name.value.trim(),
            sku: f.sku.value.trim() || null,
            qty: parseFloat(f.qty.value),
            unit: f.querySelector('input[name="unit"]').value || null,
            vendor_id: vendorVal ? parseInt(vendorVal) : undefined,
            price: f.price.value ? parseFloat(f.price.value) : undefined,
            location: f.location.value.trim() || null
        };
        data = compactPayload(data);

        // create requires name; update must not send empty/undefined name
        if (!currentEditId) {
            if (!data.name) { alert('Name required'); return; }
        } else {
            // never send name on PUT; let backend keep existing
            delete data.name;
        }

        try {
            if (currentEditId) {
                await apiPut(`/app/items/${currentEditId}`, data);
            } else {
                await apiPost('/app/items', data);
            }
            document.getElementById('item-modal').style.display = 'none';
            document.body.classList.remove('modal-open');
            loadItems();
        } catch (err) {
            alert('Save failed: ' + (err?.error || err?.message || 'unknown'));
        }
    };

    document.getElementById('cancel-btn').onclick = () => {
        closeModals();
    };

    document.getElementById('adjust-form').onsubmit = async (e) => {
        e.preventDefault();
        const form = e.target;
        const item_id = parseInt(form.item_id.value);
        const delta = parseFloat(form.delta.value);
        const reason = form.reason.value.trim();

        const payload = { item_id, delta, reason };

        try {
            await apiPost('/app/inventory/adjust', payload);
            document.getElementById('adjust-modal').style.display = 'none';
            document.body.classList.remove('modal-open');
            loadItems();
            return;
        } catch (err) {
            const status = err?.status || err?.code;
            const msg = (err?.error || err?.message || '').toLowerCase();

            const missing = status === 404 || status === 405 || msg.includes('not found') || msg.includes('method not allowed');
            if (!missing) {
                alert('Adjust failed: ' + (err?.error || err?.message || 'unknown'));
                return;
            }

            try {
                let cur = itemsCache.find(x => x.id === item_id);
                if (!cur) {
                    const items = await apiGet('/app/items');
                    itemsCache = Array.isArray(items) ? items : [];
                    cur = itemsCache.find(x => x.id === item_id);
                }
                if (!cur) throw new Error('Item not found');

                const newQty = Number((Number(cur.qty) + delta).toFixed(4));
                await apiPut(`/app/items/${item_id}`, { qty: newQty });
                alert('Adjusted without journal (fallback).');
                document.getElementById('adjust-modal').style.display = 'none';
                document.body.classList.remove('modal-open');
                loadItems();
            } catch (e2) {
                alert('Adjust fallback failed: ' + (e2?.error || e2?.message || 'unknown'));
            }
        }
    };

    document.getElementById('cancel-adjust').onclick = () => {
        closeModals();
    };

    loadItems();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
