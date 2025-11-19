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

// ui/js/cards/inventory.js
// FREE inventory table with manual Add/Edit/Delete and Adjust.
// ESM. Uses existing API helpers that inject X-Session-Token.

import { apiGet, apiPost, apiPut, apiDelete, ensureToken } from '../api.js';
import { request as rawRequest } from '../token.js';

export async function _mountInventory(container) {
    await ensureToken();

    console.log(
        'Inventory endpoints:\n  Load: GET /app/items\n  Create: POST /app/items\n  Update: PUT /app/items/{id}\n  Delete: DELETE /app/items/{id}\n  Adjust primary: POST /app/inventory/adjust {item_id, delta, reason}\n  Adjust fallback: GET /app/items + PUT /app/items/{id} {qty}'
    );

    const UNIT_SETS = {
        ea: ['ea'],
        metric: ['mm', 'cm', 'm', 'km', 'g', 'kg', 'ml', 'l', 'm2', 'm3'],
        imperial: ['inch', 'ft', 'yd', 'mile', 'oz', 'lb', 'qt', 'gal', 'ft2', 'ft3']
    };

    const currencySelect = () => document.getElementById('price-currency');
    const unitSystemEl = () => document.getElementById('unit-system');
    const unitSelectEl = () => document.getElementById('unit-select');

    // currency symbol from UI preference
    function toNumber(x) {
        if (typeof x === 'number') return x;
        const s = String(x).replace(',', '.').trim();
        const n = Number(s);
        if (Number.isNaN(n)) throw new Error('Invalid number');
        return n;
    }
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
            <button id="bulk-import-btn" class="pro-btn" style="background:#1e1f22;color:#e6e6e6;border:1px solid #2a2c30;border-radius:10px;padding:6px 14px;">Bulk Import (Pro)</button>
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

                    <label>Type:
                        <select name="type" id="item-type">
                            <option value="">— select —</option>
                            <option value="material">material</option>
                            <option value="consumable">consumable</option>
                            <option value="product">product</option>
                            <option value="asset">asset</option>
                        </select>
                    </label><br>

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

        <!-- Bulk Import -->
        <div id="bulk-modal" class="modal" style="display:none">
            <div class="modal-content" style="background:#1e1f22;color:#e6e6e6;border-radius:10px;padding:24px;box-shadow:0 14px 40px rgba(0,0,0,0.55);width:520px;max-height:90vh;overflow:auto;">
                <h3 style="margin-top:0;">Bulk Import (Pro)</h3>
                <div class="bulk-section" style="margin-bottom:16px;">
                    <label style="display:block;margin-bottom:12px;">
                        Upload CSV or XLSX
                        <input type="file" id="bulk-file" accept=".csv,.xlsx" style="display:block;margin-top:8px;background:#2a2c30;color:#e6e6e6;border:1px solid #3a3c40;border-radius:10px;padding:8px;">
                    </label>
                    <button type="button" id="bulk-preview-btn" style="background:#2a2c30;color:#e6e6e6;border-radius:10px;border:1px solid #3a3c40;padding:8px 16px;">Generate Preview</button>
                </div>
                <div id="bulk-mapping" style="display:none;margin-top:10px;"></div>
                <div id="bulk-preview" style="display:none;margin-top:16px;">
                    <table id="bulk-preview-table" style="width:100%;border-collapse:collapse;background:#1e1f22;border:1px solid #2a2c30;border-radius:10px;overflow:hidden;">
                        <thead>
                            <tr id="bulk-preview-head"></tr>
                        </thead>
                        <tbody id="bulk-preview-body"></tbody>
                    </table>
                </div>
                <div id="bulk-status" style="display:none;margin-top:12px;color:#9cdcfe;font-size:0.9rem;"></div>
                <div class="bulk-actions" style="display:flex;gap:12px;margin-top:20px;justify-content:flex-end;">
                    <button type="button" id="bulk-commit-btn" style="background:#2a2c30;color:#e6e6e6;border-radius:10px;border:1px solid #3a3c40;padding:8px 18px;" disabled>Commit Import</button>
                    <button type="button" id="bulk-cancel-btn" style="background:#2a2c30;color:#e6e6e6;border-radius:10px;border:1px solid #3a3c40;padding:8px 18px;">Close</button>
                </div>
            </div>
        </div>
    `;

    const tbody = container.querySelector('#items-table tbody');
    let currentEditId = null;
    let itemsCache = [];

    const BULK_FIELDS = [
        { key: 'name', label: 'Name', required: true },
        { key: 'sku', label: 'SKU' },
        { key: 'qty', label: 'Quantity' },
        { key: 'unit', label: 'Unit' },
        { key: 'price', label: 'Price' },
        { key: 'vendor_id', label: 'Vendor ID' },
        { key: 'notes', label: 'Notes' }
    ];

    const bulkButton = container.querySelector('#bulk-import-btn');
    const bulkModal = container.querySelector('#bulk-modal');
    const bulkFileInput = container.querySelector('#bulk-file');
    const bulkPreviewBtn = container.querySelector('#bulk-preview-btn');
    const bulkCommitBtn = container.querySelector('#bulk-commit-btn');
    const bulkCancelBtn = container.querySelector('#bulk-cancel-btn');
    const bulkMapping = container.querySelector('#bulk-mapping');
    const bulkPreviewWrap = container.querySelector('#bulk-preview');
    const bulkPreviewHead = container.querySelector('#bulk-preview-head');
    const bulkPreviewBody = container.querySelector('#bulk-preview-body');
    const bulkStatus = container.querySelector('#bulk-status');

    const bulkState = {
        previewId: null,
        columns: [],
        previewRows: [],
        totalRows: 0
    };
    let bulkMappingSelects = [];

    function setBulkStatus(message, tone = 'info') {
        if (!bulkStatus) return;
        if (!message) {
            bulkStatus.style.display = 'none';
            bulkStatus.textContent = '';
            return;
        }
        bulkStatus.textContent = message;
        bulkStatus.style.display = '';
        bulkStatus.style.color = tone === 'error' ? '#ff7b7b' : '#9cdcfe';
    }

    function resetBulkModal() {
        bulkState.previewId = null;
        bulkState.columns = [];
        bulkState.previewRows = [];
        bulkState.totalRows = 0;
        bulkMappingSelects = [];
        if (bulkFileInput) bulkFileInput.value = '';
        if (bulkMapping) {
            bulkMapping.innerHTML = '';
            bulkMapping.style.display = 'none';
        }
        if (bulkPreviewHead) bulkPreviewHead.innerHTML = '';
        if (bulkPreviewBody) bulkPreviewBody.innerHTML = '';
        if (bulkPreviewWrap) bulkPreviewWrap.style.display = 'none';
        if (bulkCommitBtn) bulkCommitBtn.disabled = true;
        setBulkStatus('');
    }

    function renderBulkMapping(columns) {
        if (!bulkMapping) return;
        bulkMapping.innerHTML = '';
        bulkMappingSelects = [];
        if (!Array.isArray(columns) || columns.length === 0) {
            bulkMapping.style.display = 'none';
            return;
        }

        const grid = document.createElement('div');
        grid.style.display = 'grid';
        grid.style.gap = '10px';

        BULK_FIELDS.forEach(field => {
            const wrapper = document.createElement('label');
            wrapper.style.display = 'flex';
            wrapper.style.flexDirection = 'column';
            wrapper.style.gap = '6px';
            wrapper.style.color = '#e6e6e6';
            wrapper.style.fontSize = '0.9rem';

            const text = document.createElement('span');
            text.textContent = field.required ? `${field.label} *` : field.label;
            const select = document.createElement('select');
            select.dataset.field = field.key;
            select.style.background = '#2a2c30';
            select.style.color = '#e6e6e6';
            select.style.border = '1px solid #3a3c40';
            select.style.borderRadius = '10px';
            select.style.padding = '6px 10px';

            const emptyOpt = document.createElement('option');
            emptyOpt.value = '';
            emptyOpt.textContent = '— Not mapped —';
            select.appendChild(emptyOpt);

            let guess = '';
            const normalizedField = field.key.toLowerCase();
            columns.forEach(col => {
                const value = String(col);
                const opt = document.createElement('option');
                opt.value = value;
                opt.textContent = value;
                select.appendChild(opt);
                const lc = value.toLowerCase();
                if (!guess && (lc === normalizedField || lc.replace(/\s+/g, '') === normalizedField)) {
                    guess = value;
                }
            });
            if (!guess) {
                const normalizedVariants = [
                    normalizedField,
                    normalizedField.replace(/_/g, ' '),
                    normalizedField.replace(/_/g, '')
                ].filter(Boolean);
                guess = columns.find(col => {
                    const lc = String(col).toLowerCase();
                    return normalizedVariants.some(token => token && lc.includes(token));
                }) || '';
            }
            if (guess) select.value = guess;

            wrapper.appendChild(text);
            wrapper.appendChild(select);
            grid.appendChild(wrapper);
            bulkMappingSelects.push(select);
        });

        bulkMapping.appendChild(grid);
        bulkMapping.style.display = '';
    }

    function renderBulkPreviewTable(columns, rows) {
        if (!bulkPreviewHead || !bulkPreviewBody) return;
        bulkPreviewHead.innerHTML = '';
        bulkPreviewBody.innerHTML = '';
        if (!Array.isArray(columns) || columns.length === 0) {
            if (bulkPreviewWrap) bulkPreviewWrap.style.display = 'none';
            return;
        }

        columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            th.style.padding = '6px 10px';
            th.style.background = '#2b2d31';
            th.style.textAlign = 'left';
            bulkPreviewHead.appendChild(th);
        });

        const previewRows = Array.isArray(rows) ? rows : [];
        const limited = previewRows.slice(0, 10);
        if (limited.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.textContent = 'No preview rows available yet.';
            td.colSpan = columns.length;
            td.style.padding = '10px';
            td.style.textAlign = 'center';
            td.style.background = '#1e1f22';
            tr.appendChild(td);
            bulkPreviewBody.appendChild(tr);
        }
        limited.forEach(row => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid #2a2c30';
            columns.forEach(col => {
                const td = document.createElement('td');
                const value = row && Object.prototype.hasOwnProperty.call(row, col) ? row[col] : '';
                td.textContent = value === null || value === undefined ? '' : String(value);
                td.style.padding = '6px 10px';
                td.style.background = '#1e1f22';
                tr.appendChild(td);
            });
            bulkPreviewBody.appendChild(tr);
        });

        if (bulkPreviewWrap) bulkPreviewWrap.style.display = '';
    }

    function gatherBulkMapping() {
        const mapping = {};
        bulkMappingSelects.forEach(select => {
            if (select.value) {
                mapping[select.dataset.field] = select.value;
            }
        });
        return mapping;
    }

    function openBulkModal() {
        resetBulkModal();
        if (bulkModal) bulkModal.style.display = 'block';
        document.body.classList.add('modal-open');
    }

    function anyModalOpen() {
        const ids = ['item-modal', 'adjust-modal', 'bulk-modal'];
        return ids.some(id => {
            const el = document.getElementById(id);
            return el && el.style.display !== 'none';
        });
    }

    function hideBulkModal() {
        if (bulkModal) bulkModal.style.display = 'none';
        resetBulkModal();
        if (!anyModalOpen()) {
            document.body.classList.remove('modal-open');
        }
    }

    if (bulkModal) {
        bulkModal.addEventListener('click', (ev) => {
            if (ev.target === bulkModal) hideBulkModal();
        });
    }

    if (!document.body.dataset.bulkEscBound) {
        document.addEventListener('keydown', (ev) => {
            if (ev.key === 'Escape' && bulkModal && bulkModal.style.display === 'block') {
                hideBulkModal();
            }
        });
        document.body.dataset.bulkEscBound = '1';
    }

    if (bulkButton) {
        bulkButton.disabled = true;
        bulkButton.style.opacity = '0.4';
        bulkButton.title = 'Requires Pro license';
    }

    async function initBulkImport() {
        if (!bulkButton) return;
        try {
            const license = await apiGet('/dev/license');
            const enabled = Boolean(license?.features?.import_commit);
            if (enabled) {
                bulkButton.disabled = false;
                bulkButton.style.opacity = '1';
                bulkButton.title = '';
            } else {
                bulkButton.disabled = true;
                bulkButton.style.opacity = '0.4';
                bulkButton.title = 'Requires Pro license';
            }
        } catch {
            bulkButton.disabled = true;
            bulkButton.style.opacity = '0.4';
            bulkButton.title = 'Requires Pro license';
        }
    }

    if (bulkButton) {
        bulkButton.addEventListener('click', () => {
            if (bulkButton.disabled) return;
            openBulkModal();
        });
    }

    if (bulkCancelBtn) {
        bulkCancelBtn.onclick = () => hideBulkModal();
    }

    if (bulkPreviewBtn) {
        bulkPreviewBtn.onclick = async () => {
            if (!bulkFileInput || bulkFileInput.files.length === 0) {
                setBulkStatus('Select a CSV or XLSX file to continue.', 'error');
                return;
            }
            setBulkStatus('Generating preview…');
            bulkPreviewBtn.disabled = true;
            if (bulkCommitBtn) bulkCommitBtn.disabled = true;
            try {
                const formData = new FormData();
                formData.append('file', bulkFileInput.files[0]);
                const resp = await rawRequest('/app/items/bulk_preview', {
                    method: 'POST',
                    body: formData
                });
                const text = await resp.text();
                let data = {};
                if (text) {
                    try {
                        data = JSON.parse(text);
                    } catch {
                        data = { error: text };
                    }
                }
                if (!resp.ok) {
                    const msg = data?.detail || data?.error || data?.message || 'Preview failed';
                    throw new Error(msg);
                }

                const columns = Array.isArray(data.columns) ? data.columns : [];
                if (!columns.length) {
                    throw new Error('No columns detected in file.');
                }
                bulkState.previewId = data.preview_id;
                bulkState.columns = columns;
                bulkState.previewRows = Array.isArray(data.preview_rows) ? data.preview_rows : [];
                const totalRows = Number.parseInt(data.total_rows, 10);
                bulkState.totalRows = Number.isFinite(totalRows) ? totalRows : bulkState.previewRows.length;

                renderBulkMapping(columns);
                renderBulkPreviewTable(columns, bulkState.previewRows);

                const rowsLabel = bulkState.totalRows === 1 ? 'row' : 'rows';
                setBulkStatus(`Preview ready. ${bulkState.totalRows} ${rowsLabel} detected.`);
                if (bulkCommitBtn) bulkCommitBtn.disabled = false;
            } catch (err) {
                const msg = err?.message || 'Preview failed';
                if (msg === 'missing_openpyxl') {
                    setBulkStatus('XLSX preview requires openpyxl on the server.', 'error');
                } else {
                    setBulkStatus(msg, 'error');
                }
            } finally {
                bulkPreviewBtn.disabled = false;
            }
        };
    }

    if (bulkCommitBtn) {
        bulkCommitBtn.onclick = async () => {
            if (!bulkState.previewId) {
                setBulkStatus('Generate a preview before committing.', 'error');
                return;
            }
            const mapping = gatherBulkMapping();
            if (!mapping.name) {
                setBulkStatus('Map the Name column before committing.', 'error');
                return;
            }

            setBulkStatus('Committing import…');
            bulkCommitBtn.disabled = true;
            try {
                const result = await apiPost('/app/items/bulk_commit', {
                    preview_id: bulkState.previewId,
                    mapping
                });
                const created = result?.created ?? 0;
                const updated = result?.updated ?? 0;
                const skipped = result?.skipped ?? 0;
                alert(`Bulk import complete: ${created} created, ${updated} updated, ${skipped} skipped.`);
                hideBulkModal();
                await loadItems();
            } catch (err) {
                setBulkStatus('Commit failed: ' + (err?.error || err?.message || 'unknown'), 'error');
                bulkCommitBtn.disabled = false;
            }
        };
    }

    initBulkImport();

    async function loadItems() {
        try {
            const items = await apiGet('/app/items');
            const list = Array.isArray(items) ? items : [];
            itemsCache = list;
            renderTable(list);
        } catch (err) {
            alert('Failed to load items: ' + (err?.error || err?.message || 'unknown'));
        }
    }

    function renderTable(items) {
        const sym = currencySymbol();
        tbody.innerHTML = items.map(item => {
            const qty = item.qty ?? 0;
            const unit = safeUnit(item.unit);
            const qtyUnit = `${qty} ${unit ? unit.toUpperCase() : ''}`.trim();
            const vendor = item.vendor_id ? escapeHtml(String(item.vendor_id)) : '';
            let price = '';
            if (item.price !== undefined && item.price !== null && item.price !== '') {
                const priceNum = Number(item.price);
                if (!Number.isNaN(priceNum)) price = `${sym}${priceNum}`;
            }
            const loc = item.location ? escapeHtml(item.location) : 'Shop';
            const typeAttr = escapeHtml((item.type || '').toString().toLowerCase());
            return `
      <tr data-id="${item.id}" data-type="${typeAttr}">
        <td>${escapeHtml(item.name || '')}</td>
        <td>${escapeHtml(item.sku || '')}</td>
        <td>${escapeHtml(qtyUnit)}</td>
        <td>${vendor}</td>
        <td>${price ? escapeHtml(price) : ''}</td>
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
            type: (row.dataset.type || '').toLowerCase(),
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
        if (form.type) {
            form.type.value = (item.type || '').toLowerCase();
        }
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
        const itemModal = document.getElementById('item-modal');
        const adjustModal = document.getElementById('adjust-modal');
        if (itemModal) itemModal.style.display = 'none';
        if (adjustModal) adjustModal.style.display = 'none';
        if (!anyModalOpen()) {
            document.body.classList.remove('modal-open');
        }
    }

    async function deleteItem(id) {
        if (!confirm('Delete this item?')) return;
        try {
            await ensureToken();
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
            if (v === '' || v === null || v === undefined || Number.isNaN(v)) continue;
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
        const typeValue = (f.type?.value || '').trim().toLowerCase();

        // build base data from form
        let data = {
            name: f.name.value.trim(),
            sku: f.sku.value.trim() || null,
            qty: parseFloat(f.qty.value),
            unit: f.querySelector('input[name="unit"]').value || null,
            vendor_id: vendorVal ? parseInt(vendorVal, 10) : undefined,
            price: f.price.value ? parseFloat(f.price.value) : undefined,
            location: f.location.value.trim() || null,
            ...(typeValue ? { type: typeValue } : {}),
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
            await ensureToken();
            if (currentEditId) {
                try {
                    await apiPut(`/app/items/${currentEditId}`, data);
                } catch (err) {
                    try {
                        const resp = await rawRequest(`/app/items/${currentEditId}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(data)
                        });
                        if (!resp.ok) {
                            throw new Error(`PATCH failed: ${resp.status}`);
                        }
                    } catch {
                        await apiPost('/app/items', { id: currentEditId, ...data });
                    }
                }
            } else {
                await apiPost('/app/items', data);
            }
            closeModals();
            loadItems();
        } catch (err) {
            alert('Save failed: ' + (err?.error || err?.message || 'unknown'));
        }
    };

    document.getElementById('cancel-btn').onclick = () => {
        closeModals();
    };

    // ===== Adjust Qty — hybrid: try Pro journal, else PUT fallback =====
    document.getElementById('adjust-form').onsubmit = async (e) => {
        e.preventDefault();

        const form    = e.target;
        const item_id = parseInt(form.item_id.value, 10);
        const delta   = Number(form.delta.value);
        const reason  = String(form.reason.value || '').trim();

        if (!Number.isFinite(item_id) || Number.isNaN(delta)) {
            alert('Adjust requires a valid item and numeric delta.');
            return;
        }

        const payload = { item_id, delta, reason };

        async function fallbackAdjust(targetId, change) {
            let cur = null;
            try {
                const item = await apiGet(`/app/items/${targetId}`);
                cur = item?.qty ?? null;
            } catch {
                try {
                    const all = await apiGet('/app/items');
                    const hit = (Array.isArray(all) ? all : []).find((it) => String(it.id) === String(targetId));
                    cur = hit?.qty ?? null;
                } catch {
                    cur = null;
                }
            }
            if (cur == null) cur = 0;
            const newQty = Number(cur) + Number(change);

            try {
                return await apiPut(`/app/items/${targetId}`, { qty: newQty });
            } catch (e1) {
                try {
                    const token = await ensureToken();
                    const res = await fetch(`/app/items/${targetId}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json', 'X-Session-Token': token },
                        body: JSON.stringify({ qty: newQty }),
                    });
                    if (!res.ok) throw new Error(String(res.status));
                    return await res.json();
                } catch (e2) {
                    return await apiPost('/app/items', { id: targetId, qty: newQty });
                }
            }
        }

        async function adjust(body) {
            try {
                await apiPost('/app/inventory/adjust', body);
            } catch (err) {
                const status = err?.status || err?.response?.status || err?.code;
                if (status === 404 || status === 405) {
                    await fallbackAdjust(body.item_id, body.delta);
                } else {
                    throw err;
                }
            }
        }

        try {
            await adjust(payload);
        } catch (err) {
            alert('Adjust failed: ' + (err?.error || err?.message || 'unknown'));
            return;
        }

        // Close and refresh
        document.getElementById('adjust-modal').style.display = 'none';
        document.body.classList.remove('modal-open');
        await loadItems();
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

console.info(`Inventory endpoints:\n  Load: GET /app/items\n  Create: POST /app/items\n  Update: PUT /app/items/{id}\n  Delete: DELETE /app/items/{id}\n  Adjust primary: POST /app/inventory/adjust {item_id, delta, reason}\n  Adjust fallback: GET /app/items + PUT /app/items/{id} {qty}`);

if (!window.mountInventoryCard) {
    window.mountInventoryCard = function mountInventoryCard() {
        try {
            if (typeof initInventory === 'function') initInventory();
        } catch (e) {
            console.error('mountInventoryCard error', e);
        }
    };
}

// --- GLUE START (add at bottom of the existing Inventory file) ---

let __inventoryBooted = false;

export function mountInventory() {
    const home = document.querySelector('[data-role="home-screen"]');
    const inv  = document.querySelector('[data-role="inventory-screen"]');

    // Hide Home; show Inventory shell
    if (home) home.classList.add('hidden');
    if (inv)  inv.classList.remove('hidden');

    // One-time boot of whatever initializer already exists
    if (!__inventoryBooted) {
        __inventoryBooted = true;

        const host = document.querySelector('[data-role="inventory-root"]') || inv;

        // Call the existing initializer if present (do not create new logic)
        if (typeof initInventory === 'function')       initInventory();
        else if (typeof renderInventory === 'function') renderInventory();
        else if (typeof startInventory === 'function')  startInventory();
        else if (typeof setupInventory === 'function')  setupInventory();
        // If this module already exported a mount, call it once:
        else if (typeof _mountInventory === 'function' && host) _mountInventory(host);
        // If none of the above exist, do nothing (UI may be static).
    }
}

export function unmountInventory() {
    const inv = document.querySelector('[data-role="inventory-screen"]');
    if (inv) inv.classList.add('hidden');
}

// --- GLUE END ---
