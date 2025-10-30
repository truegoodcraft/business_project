// ui/js/cards/inventory.js
// FREE inventory table with manual Add/Edit/Delete and Adjust.
// ESM. Uses existing API helpers that inject X-Session-Token.

import { apiGet, apiPost, apiPut, apiDelete, ensureToken } from '../api.js';

export async function mountInventory(container) {
    await ensureToken();

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
                    <label>Qty: <input name="qty" type="number" step="0.01" required></label><br>
                    <label>Unit: <input name="unit" required></label><br>
                    <label>Vendor ID: <input name="vendor_id" type="number"></label><br>
                    <label>Price: <input name="price" type="number" step="0.01"></label><br>
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
        form.unit.value = item.unit || '';
        form.vendor_id.value = item.vendor_id ?? '';
        form.price.value = item.price ?? '';
        form.location.value = item.location || '';
        form.id.value = item.id ?? '';
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

    document.getElementById('item-form').onsubmit = async (e) => {
        e.preventDefault();
        const form = e.target;
        const data = {
            name: form.name.value.trim(),
            sku: form.sku.value.trim() || null,
            qty: parseFloat(form.qty.value),
            unit: form.unit.value.trim(),
            vendor_id: form.vendor_id.value ? parseInt(form.vendor_id.value) : null,
            price: form.price.value ? parseFloat(form.price.value) : null,
            location: form.location.value.trim() || null
        };

        try {
            if (currentEditId) {
                await apiPut(`/app/items/${currentEditId}`, data);
            } else {
                await apiPost('/app/items', data);
            }
            closeModals();
            loadItems();
        } catch (err) {
            alert('Save failed: ' + (err.error || err.message));
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
