// SPDX-License-Identifier: AGPL-3.0-or-later
// Inventory card with smart input parsing.

import { apiGet, apiPost, apiPut, apiDelete, ensureToken } from '../api.js';
import { parseSmartInput } from '../utils/parser.js';

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else node.setAttribute(k, v);
  });
  (Array.isArray(children) ? children : [children]).forEach((child) => {
    if (child === null || child === undefined) return;
    node.append(child);
  });
  return node;
}

function badge(text) {
  return el('span', { class: 'badge-note' }, text);
}

function renderSmartPreview(inputEl, previewEl) {
  const parsed = parseSmartInput(inputEl.value);
  if (!parsed) {
    previewEl.textContent = 'Waiting for input…';
    previewEl.classList.remove('ok');
    return null;
  }
  previewEl.textContent = `Parsed: ${parsed.qty} ${parsed.unit || ''}`.trim();
  previewEl.classList.add('ok');
  return parsed;
}

async function mountModal(state, item = null) {
  const overlay = el('div', { class: 'modal', id: 'item-modal' });
  const form = el('form', { class: 'modal-content' });
  form.append(
    el('h3', { text: item ? 'Edit Item' : 'Add Item' }),
    el('label', {}, ['Name', el('input', { name: 'name', required: true, value: item?.name || '' })]),
    el('label', {}, ['SKU', el('input', { name: 'sku', value: item?.sku || '' })]),
    el('label', {}, [
      'Qty + Unit',
      el('input', { id: 'inv-smart', name: 'smart', placeholder: "e.g. 10 kg or 5'", value: item ? `${item.qty ?? ''} ${item.unit ?? ''}`.trim() : '' }),
      badge('Waiting for input…'),
    ]),
    el('label', {}, ['Vendor ID', el('input', { name: 'vendor_id', value: item?.vendor_id || '' })]),
    el('label', {}, ['Price', el('input', { name: 'price', type: 'number', step: '0.01', value: item?.price ?? '' })]),
    el('label', {}, ['Location', el('input', { name: 'location', value: item?.location || '' })]),
    el('label', {}, ['Notes', el('textarea', { name: 'notes' }, item?.notes || '')]),
    el('div', { class: 'actions' }, [
      el('button', { type: 'submit' }, 'Save'),
      el('button', { type: 'button', id: 'modal-cancel' }, 'Cancel'),
    ]),
  );

  const preview = form.querySelector('.badge-note');
  const smartInput = form.querySelector('#inv-smart');
  renderSmartPreview(smartInput, preview);
  smartInput.addEventListener('input', () => renderSmartPreview(smartInput, preview));

  overlay.append(form);
  document.body.append(overlay);

  return new Promise((resolve) => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const parsed = renderSmartPreview(smartInput, preview);
      if (!parsed) {
        preview.textContent = 'Enter a number with optional unit (e.g. 12 kg)';
        return;
      }
      const fd = new FormData(form);
      const payload = {
        name: fd.get('name') || 'Unnamed',
        sku: fd.get('sku') || null,
        qty: parsed.qty,
        unit: parsed.unit || 'EA',
        vendor_id: fd.get('vendor_id') || null,
        price: fd.get('price') ? Number(fd.get('price')) : null,
        location: fd.get('location') || null,
        notes: fd.get('notes') || null,
      };
      if (item?.id) payload.id = item.id;
      resolve(payload);
      overlay.remove();
    });

    form.querySelector('#modal-cancel')?.addEventListener('click', () => {
      overlay.remove();
      resolve(null);
    });
  });
}

async function fetchItems(state) {
  state.items = await apiGet('/app/items');
  return state.items;
}

function renderTable(state) {
  const tbody = state.tableBody;
  tbody.innerHTML = '';
  state.items.forEach((item) => {
    const row = el('tr');
    row.append(
      el('td', { text: item.name || 'Item' }),
      el('td', { text: item.sku || '—' }),
      el('td', { text: `${item.qty ?? 0} ${item.unit || ''}`.trim() }),
      el('td', { text: item.vendor || '—' }),
      el('td', { text: item.price != null ? `$${Number(item.price).toFixed(2)}` : '—' }),
      el('td', { text: item.location || '—' }),
      el('td', {}, [
        el('button', { type: 'button', 'data-action': 'edit', 'data-id': item.id }, 'Edit'),
        el('button', { type: 'button', 'data-action': 'adjust', 'data-id': item.id }, 'Adjust'),
        el('button', { type: 'button', 'data-action': 'delete', 'data-id': item.id, class: 'danger' }, 'Delete'),
      ]),
    );
    tbody.append(row);
  });
}

async function adjustQuantity(itemId) {
  const deltaStr = prompt('Adjust quantity by (e.g. -2 or 5):');
  if (deltaStr === null) return;
  const delta = Number(deltaStr);
  if (!Number.isFinite(delta)) return alert('Enter a valid number');
  await apiPost('/app/inventory/run', { inputs: {}, outputs: { [itemId]: delta } });
}

export async function _mountInventory(container) {
  await ensureToken();
  const state = { items: [], tableBody: null };

  container.innerHTML = '';
  const controls = el('div', { class: 'inventory-controls' }, [
    el('button', { id: 'add-item-btn' }, '+ Add Item'),
    el('button', { id: 'refresh-btn' }, 'Refresh'),
  ]);
  const table = el('table', { id: 'items-table' }, [
    el('thead', {}, [
      el('tr', {}, [
        el('th', { text: 'Name' }),
        el('th', { text: 'SKU' }),
        el('th', { text: 'Qty' }),
        el('th', { text: 'Vendor' }),
        el('th', { text: 'Price' }),
        el('th', { text: 'Location' }),
        el('th', { text: 'Actions' }),
      ]),
    ]),
    el('tbody'),
  ]);
  container.append(controls, table);
  state.tableBody = table.querySelector('tbody');

  controls.querySelector('#add-item-btn').addEventListener('click', async () => {
    const payload = await mountModal(state);
    if (!payload) return;
    const created = await apiPost('/app/items', payload);
    state.items.push(created);
    renderTable(state);
  });

  controls.querySelector('#refresh-btn').addEventListener('click', async () => {
    await fetchItems(state);
    renderTable(state);
  });

  table.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const id = Number(btn.getAttribute('data-id'));
    const action = btn.getAttribute('data-action');
    const item = state.items.find((it) => it.id === id);
    if (!item) return;
    if (action === 'edit') {
      const payload = await mountModal(state, item);
      if (!payload) return;
      const updated = await apiPut(`/app/items/${id}`, payload);
      Object.assign(item, updated);
      renderTable(state);
    }
    if (action === 'adjust') {
      await adjustQuantity(id);
      await fetchItems(state);
      renderTable(state);
    }
    if (action === 'delete') {
      await apiDelete(`/app/items/${id}`);
      state.items = state.items.filter((it) => it.id !== id);
      renderTable(state);
    }
  });

  await fetchItems(state);
  renderTable(state);
}

export function mountInventory() {
  const container = document.querySelector('[data-role="inventory-table"]');
  if (!container) return;
  _mountInventory(container);
}

export function unmountInventory() {}
