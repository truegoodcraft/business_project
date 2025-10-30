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
        const candidates = ['/app/vendors', '/app/vendors/list', '/app/partners'];
        let list = [];
        for (const url of candidates) {
            try {
                list = await apiGet(url);
                if (Array.isArray(list) && list.length) break;
            } catch {}
        }
        const field = document.getElementById('vendor-field');
        const sel = document.getElementById('vendor-select');
        if (!Array.isArray(list) || list.length === 0) {
            field.style.display = 'none';
            sel.innerHTML = '';
            return;
        }
        field.style.display = '';
        sel.innerHTML = `<option value="">— none —</option>` + list.map(v => {
            const id = v.id ?? v.vendor_id ?? v.code;
            const name = v.name ?? v.title ?? `Vendor ${id}`;
            return `<option value="${id}">${name}</option>`;
        }).join('');
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
                    <th>Unit</th>
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
            renderTable(items);
        } catch (err) {
            alert('Failed to load items: ' + (err.error || err.message));
        }
    }

    function renderTable(items) {
        tbody.innerHTML = items.map(item => `
            <tr data-id="${item.id}">
                <td>${escapeHtml(item.name)}</td>
                <td>${escapeHtml(item.sku || '')}</td>
                <td>${item.qty}</td>
                <td>${escapeHtml(item.unit)}</td>
                <td>${item.vendor_id ?? ''}</td>
                <td>${item.price ?? ''}</td>
                <td>${escapeHtml(item.location || '')}</td>
                <td>
                    <button class="edit-btn">Edit</button>
                    <button class="adjust-btn">±</button>
                    <button class="delete-btn">Delete</button>
                </td>
            </tr>
        `).join('');

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
        return {
            id: parseInt(id),
            name: row.cells[0].textContent,
            sku: row.cells[1].textContent,
            qty: parseFloat(row.cells[2].textContent),
            unit: row.cells[3].textContent,
            vendor_id: row.cells[4].textContent ? parseInt(row.cells[4].textContent) : null,
            price: row.cells[5].textContent ? parseFloat(row.cells[5].textContent) : null,
            location: row.cells[6].textContent
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
        document.body.classList.add('modal-open');
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
            alert('Delete failed: ' + (err.error || err.message));
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
        localStorage.setItem('priceCurrency', currencySelect().value);

        const vendorVal = document.getElementById('vendor-select')?.value || '';
        const data = compactPayload({
            name: f.name.value.trim(),
            sku: f.sku.value.trim() || null,
            qty: parseFloat(f.qty.value),
            unit: f.querySelector('input[name="unit"]').value || null,
            vendor_id: vendorVal ? parseInt(vendorVal) : undefined,
            price: f.price.value ? parseFloat(f.price.value) : undefined,
            location: f.location.value.trim() || null
        });

        try {
            if (currentEditId) {
                await apiPut(`/app/items/${currentEditId}`, data);
            } else {
                await apiPost('/app/items', data);
            }
            closeModals();
            loadItems();
        } catch (err) {
            console.error('Save failed:', err);
            alert('Save failed: ' + (err?.error || err?.message || 'unknown'));
        }
    };

    document.getElementById('cancel-btn').onclick = () => {
        closeModals();
    };

    document.getElementById('adjust-form').onsubmit = async (e) => {
        e.preventDefault();
        const form = e.target;
        const payload = {
            item_id: parseInt(form.item_id.value),
            delta: parseFloat(form.delta.value),
            reason: form.reason.value.trim()
        };
        try {
            await apiPost('/app/inventory/adjust', payload);
            closeModals();
            loadItems();
        } catch (err) {
            alert('Adjust failed: ' + (err.error || err.message));
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
