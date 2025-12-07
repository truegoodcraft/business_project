// SPDX-License-Identifier: AGPL-3.0-or-later
// Inventory card with smart input parsing.

import { apiGetJson, apiPost, apiPut, apiDelete, ensureToken } from '../api.js';
import { parseSmartInput } from '../utils/parser.js';

// Keep delegated handler binding stable across route changes
let _rootEl = null;
let _clickBound = false;
let _currentInventoryState = null; // Stored for deep linking

function _onRootClick(e) {
  const addBtn = e.target.closest('[data-role="btn-add-item"]');
  if (addBtn) {
    e.preventDefault();
    openItemModal(); // create mode
  }
}

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

let reloadInventory = null;

export async function mountInventory() {
  const container = document.querySelector('[data-role="inventory-root"]');
  if (!container) return;
  _rootEl = container;
  await _mountInventory(container); // Await this now
  // Bind once for delegated toolbar events
  if (!_clickBound) {
    _rootEl.addEventListener('click', _onRootClick);
    _clickBound = true;
  }
}

// Needed by app.js router; ensures route changes don’t leak handlers/modals
export function unmountInventory() {
  // Close any open modals from this card
  document.querySelectorAll('.modal-overlay').forEach((el) => {
    try {
      if (typeof el._inventoryCleanup === 'function') el._inventoryCleanup();
    } catch (_) {/* ignore */}
    el.remove();
  });
  // Remove delegated click binding
  if (_rootEl && _clickBound) {
    _rootEl.removeEventListener('click', _onRootClick);
    _clickBound = false;
  }
  _currentInventoryState = null;
}

// Exported for deep linking
export function openItemById(id) {
  if (!_currentInventoryState || !_currentInventoryState.items) return;
  // Try both number and string comparison
  const item = _currentInventoryState.items.find(i => i.id == id);
  if (item) {
    openItemModal(item);
  } else {
    console.warn(`Item ${id} not found in loaded inventory.`);
  }
}

async function fetchItems(state) {
  state.items = await apiGetJson('/app/items');
  return state.items;
}

function renderTable(state) {
  const tbody = state.tableBody;
  tbody.innerHTML = '';
  state.items.forEach((item) => {
    const row = el('tr', { 'data-role': 'item-row', 'data-id': item.id });
    row.append(
      el('td', { text: item.name || 'Item' }),
      el('td', { text: item.sku || '—' }),
      el('td', { text: `${item.qty ?? 0} ${item.unit || ''}`.trim() }),
      el('td', { text: item.vendor || '—' }),
      el('td', { text: item.price != null ? `$${Number(item.price).toFixed(2)}` : '—' }),
      el('td', { text: item.location || '—' })
    );
    tbody.append(row);
  });
}

export async function _mountInventory(container) {
  await ensureToken();
  const state = { items: [], tableBody: null };
  _currentInventoryState = state; // Store for deep access

  container.innerHTML = '';
  const controls = el('div', { class: 'inventory-controls toolbar' }, [
    el('button', { id: 'add-item-btn', class: 'btn', 'data-role': 'btn-add-item' }, '+ Add Item'),
  ]);
  const table = el('table', { id: 'items-table', class: 'table-clickable' }, [
    el('thead', {}, [
      el('tr', {}, [
        el('th', { text: 'Name' }),
        el('th', { text: 'SKU' }),
        el('th', { text: 'Qty' }),
        el('th', { text: 'Vendor' }),
        el('th', { text: 'Price' }),
        el('th', { text: 'Location' })
      ]),
    ]),
    el('tbody'),
  ]);
  container.append(controls, table);
  state.tableBody = table.querySelector('tbody');

  reloadInventory = async () => {
    await fetchItems(state);
    renderTable(state);
  };

  table.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    const row = e.target.closest('tr[data-role="item-row"]');
    // Toggle details when clicking a row (but not on buttons)
    if (row && !btn) {
      const id = Number(row.getAttribute('data-id'));
      const item = state.items.find((it) => it.id === id);
      if (!item) return;
      toggleDetailsRow(table, row, item);
      return;
    }
    if (!btn) return;
    const id = Number(btn.getAttribute('data-id')) || Number(btn.closest('[data-id]')?.getAttribute('data-id'));
    const action = btn.getAttribute('data-action');
    const item = state.items.find((it) => it.id === id);
    if (!item) return;
    if (action === 'edit') {
      openItemModal(item);
    }
    if (action === 'delete') {
      if (!(await confirmDelete())) return;
      await ensureToken();
      await apiDelete(`/app/items/${id}`);
      state.items = state.items.filter((it) => it.id !== id);
      renderTable(state);
    }
  });

  function kv(label, value) {
    return el('div', { class: 'kv' }, [ el('div', { class: 'k', text: label }), el('div', { class: 'v', text: value }) ]);
  }

  function toggleDetailsRow(tableEl, rowEl, item) {
    // Collapse if already open
    if (rowEl.nextElementSibling && rowEl.nextElementSibling.classList.contains('row-details')) {
      rowEl.nextElementSibling.remove();
      return;
    }
    // Close any other open details
    tableEl.querySelectorAll('.row-details').forEach((r) => r.remove());
    const colCount = tableEl.querySelector('thead tr').children.length || rowEl.children.length;
    const details = el('tr', { class: 'row-details' }, [
      el('td', { colspan: String(colCount) }, [
        el('div', { class: 'details' }, [
          el('div', { class: 'grid' }, [
            kv('SKU', item.sku || '—'),
            kv('Quantity', `${item.qty ?? 0} ${item.unit || ''}`.trim()),
            kv('Vendor', item.vendor || '—'),
            kv('Price', item.price != null ? `$${Number(item.price).toFixed(2)}` : '—'),
            kv('Location', item.location || '—'),
          ]),
          item.notes ? el('div', { class: 'notes', text: item.notes }) : null,
          el('div', { class: 'row-actions' }, [
            el('button', { type: 'button', 'data-action': 'edit', 'data-id': item.id }, 'Edit'),
            el('button', { type: 'button', 'data-action': 'delete', 'data-id': item.id, class: 'danger' }, 'Delete'),
          ]),
        ]),
      ]),
    ]);
    rowEl.after(details);
  }

  function confirmDelete() {
    return Promise.resolve(window.confirm('Delete this item? This cannot be undone.'));
  }

  await reloadInventory();
}

// ---------- Shallow/Deep Modal ----------
async function fetchVendors() {
  try {
    const v = await apiGetJson('/app/vendors?is_vendor=true');
    if (Array.isArray(v)) return v;
  } catch (_) {/* ignore */}
  try {
    const c = await apiGetJson('/app/contacts?is_vendor=true');
    if (Array.isArray(c)) {
      return c.map(x => ({ id: x.id ?? x.contact_id ?? x.uuid ?? null, name: x.name ?? x.display ?? '—' }))
              .filter(x => x.id != null);
    }
  } catch (_) {/* ignore */}
  return [];
}

export function openItemModal(item = null) {
  const isEdit = !!(item && item.id);

  // Container (modal)
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  const card = document.createElement('div');
  card.className = 'modal-card';
  card.style.maxWidth = '460px';           // spec width
  card.style.background = 'var(--surface)';
  card.style.border = '1px solid var(--border)';
  card.style.borderRadius = '10px';

  const title = document.createElement('div');
  title.className = 'modal-title';
  title.textContent = (isEdit ? 'Edit' : 'Add') + ' Item';
  card.appendChild(title);

  // FORM state
  let expanded = !!(item?.sku || item?.vendor_id || item?.notes);

  // Elements – Speed Surface
  const fName = inputRow('Name', 'text', item?.name ?? '', { autofocus: true });
  const qtyWrap = inputRow('Smart Qty', 'text', '', { placeholder: 'e.g. 10 kg or 5\'' });
  const qtyInput = qtyWrap.querySelector('input');
  const qtyBadge = document.createElement('span');
  qtyBadge.style.display = 'inline-block';
  qtyBadge.style.marginLeft = '8px';
  qtyBadge.style.padding = '2px 8px';
  qtyBadge.style.border = '1px solid var(--border)';
  qtyBadge.style.borderRadius = '8px';
  qtyBadge.style.opacity = '0.8';
  qtyBadge.style.fontSize = '12px';
  qtyBadge.textContent = 'Waiting for input…';
  qtyWrap.querySelector('.field-input').appendChild(qtyBadge);

  const fPrice = inputRow('Price', 'number', item?.price ?? '', { step: '0.01' });
  const fLocation = inputRow('Location', 'text', item?.location ?? '');

  // Elements – Hinge
  const hinge = document.createElement('button');
  hinge.type = 'button';
  hinge.className = 'link';
  hinge.textContent = '+ Add Details (SKU, Vendor, Notes)';
  hinge.style.margin = '8px 0';

  // Elements – Ledger Surface (hidden by default)
  const ledger = document.createElement('div');
  ledger.style.display = expanded ? 'block' : 'none';
  const fSku = inputRow('SKU', 'text', item?.sku ?? '');

  const vendorRow = document.createElement('div');
  vendorRow.className = 'field-row';
  const vendorLabel = document.createElement('label');
  vendorLabel.textContent = 'Vendor';
  vendorRow.appendChild(vendorLabel);
  const vendorInputWrap = document.createElement('div');
  vendorInputWrap.className = 'field-input';
  const vendorSelect = document.createElement('select');
  vendorSelect.style.width = '100%';
  vendorSelect.innerHTML = '<option value="">—</option>';
  vendorInputWrap.appendChild(vendorSelect);
  vendorRow.appendChild(vendorInputWrap);

  const typeRow = document.createElement('div');
  typeRow.className = 'field-row';
  const typeLabel = document.createElement('label');
  typeLabel.textContent = 'Item Type';
  const typeWrap = document.createElement('div');
  typeWrap.className = 'field-input';
  const typeSelect = document.createElement('select');
  typeSelect.innerHTML = `
    <option value="Product">Product</option>
    <option value="Material">Material</option>
    <option value="Component">Component</option>`;
  typeSelect.value = item?.type ?? 'Product';
  typeWrap.appendChild(typeSelect);
  typeRow.append(typeLabel, typeWrap);

  const notesRow = document.createElement('div');
  notesRow.className = 'field-row';
  const notesLabel = document.createElement('label');
  notesLabel.textContent = 'Notes';
  const notesWrap = document.createElement('div');
  notesWrap.className = 'field-input';
  const notes = document.createElement('textarea');
  notes.rows = 2;
  notes.value = item?.notes ?? '';
  notesWrap.appendChild(notes);
  notesRow.append(notesLabel, notesWrap);

  ledger.append(fSku, vendorRow, typeRow, notesRow);

  // Footer (Save/Cancel) – always visible
  const footer = document.createElement('div');
  footer.className = 'modal-actions';
  const saveBtn = document.createElement('button');
  saveBtn.type = 'button';
  saveBtn.className = 'btn primary';
  saveBtn.textContent = 'Save';
  const cancelBtn = document.createElement('button');
  cancelBtn.type = 'button';
  cancelBtn.className = 'btn';
  cancelBtn.textContent = 'Cancel';
  footer.append(saveBtn, cancelBtn);

  // Assemble card
  const content = document.createElement('div');
  content.className = 'modal-body';
  content.append(fName, qtyWrap, fPrice, fLocation, hinge, ledger, footer);
  card.appendChild(content);
  overlay.appendChild(card);
  document.body.appendChild(overlay);

  // Auto-focus and prefill qty badge if editing
  fName.querySelector('input')?.focus();
  if (item?.qty || item?.unit) {
    qtyInput.value = [item.qty ?? '', item.unit ?? ''].filter(Boolean).join(' ');
  }
  updateBadge();

  const populateVendors = (vendorsList, selectedId = null) => {
    vendorSelect.innerHTML = '<option value="">—</option>';
    vendorsList.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = v.name ?? `#${v.id}`;
      vendorSelect.appendChild(opt);
    });
    const createOpt = document.createElement('option');
    createOpt.value = '__create__';
    createOpt.textContent = 'Create new vendor…';
    vendorSelect.appendChild(createOpt);
    if (selectedId) {
      vendorSelect.value = String(selectedId);
    } else if (item?.vendor_id) {
      vendorSelect.value = String(item.vendor_id);
    }
  };

  const onContactSaved = async (ev) => {
    const saved = ev.detail;
    if (!saved?.id || !saved.is_vendor) return;
    const refreshed = await fetchVendors();
    if (!Array.isArray(refreshed) || !refreshed.length) return;
    populateVendors(refreshed, saved.id);
  };

  vendorSelect.addEventListener('change', () => {
    if (vendorSelect.value === '__create__') {
      window.dispatchEvent(new CustomEvent('open-contacts-modal', { detail: { prefill: { is_vendor: true, is_org: true } } }));
      vendorSelect.value = '';
    }
  });

  // Load vendors (async)
  (async () => {
    const vs = await fetchVendors();
    if (!vs.length) {
      vendorSelect.replaceWith(helpLinkToVendors());
      return;
    }
    populateVendors(vs);
    window.addEventListener('contacts:saved', onContactSaved);
  })();

  // Hinge toggle
  hinge.addEventListener('click', () => {
    expanded = !expanded;
    ledger.style.display = expanded ? 'block' : 'none';
    hinge.textContent = expanded ? '– Hide Details' : '+ Add Details (SKU, Vendor, Notes)';
  });

  // Guard against backdrop click + ESC closing; only Cancel closes
  const escBlocker = (e) => {
    if (e.key === 'Escape') {
      e.stopPropagation();
      e.preventDefault();
    }
  };
  document.addEventListener('keydown', escBlocker, true);

  const cleanup = () => {
    window.removeEventListener('contacts:saved', onContactSaved);
    document.removeEventListener('keydown', escBlocker, true);
  };

  const closeModalSafely = () => {
    cleanup();
    overlay.remove();
  };

  overlay._inventoryCleanup = closeModalSafely;

  cancelBtn.addEventListener('click', (e) => {
    e.preventDefault();
    closeModalSafely();
  });
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      e.stopPropagation();
    }
  }, true);
  card.addEventListener('click', (e) => e.stopPropagation());

  // Live parser feedback
  qtyInput.addEventListener('input', updateBadge);

  function updateBadge() {
    const parsed = parseSmartInput(qtyInput.value || '');
    if (parsed && typeof parsed.qty === 'number' && parsed.qty > 0) {
      qtyBadge.textContent = `Parsed: ${parsed.qty} | ${parsed.unit ?? ''}`.trim();
      qtyBadge.style.borderColor = 'var(--border)';
    } else {
      qtyBadge.textContent = 'Unrecognized';
      qtyBadge.style.borderColor = '#ef4444';
    }
  }

  function fieldValue(rowSel) {
    return rowSel.querySelector('input,textarea,select')?.value ?? '';
  }

  function inputRow(labelText, type, value = '', attrs = {}) {
    const row = document.createElement('div');
    row.className = 'field-row';
    const label = document.createElement('label');
    label.textContent = labelText;
    const wrap = document.createElement('div');
    wrap.className = 'field-input';
    const input = document.createElement(type === 'textarea' ? 'textarea' : 'input');
    if (type !== 'textarea') input.type = type;
    input.value = value;
    Object.entries(attrs).forEach(([k, v]) => { if (v != null) input.setAttribute(k, v); });
    wrap.appendChild(input);
    row.append(label, wrap);
    return row;
  }

  function helpLinkToVendors() {
    const a = document.createElement('a');
    a.href = '#/contacts';
    a.textContent = 'No vendors found. Go to Vendors.';
    a.className = 'link';
    return a;
  }

  function markInvalid(el) {
    el.style.borderColor = '#ef4444';
    setTimeout(() => { el.style.borderColor = 'var(--border)'; }, 1500);
  }

  // Save handler (works in collapsed or expanded)
  saveBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    const name = fieldValue(fName).trim();

    // Client-side validation
    if (!name) return markInvalid(fName.querySelector('input'));

    const priceVal = (() => {
      const n = parseFloat(fieldValue(fPrice));
      return Number.isFinite(n) ? n : 0;
    })();

    const payload = {
      name,
      sku: (fieldValue(fSku) || '').trim() || undefined,
      vendor_id: vendorSelect && vendorSelect.tagName === 'SELECT' ? (vendorSelect.value || undefined) : undefined,
      location: (fieldValue(fLocation) || '').trim() || undefined,
      price: priceVal,
      type: (expanded ? fieldValue(typeRow) : 'Product') || 'Product',
      notes: expanded ? (notes.value.trim() || undefined) : undefined,
    };

    const url = isEdit ? `/app/items/${item.id}` : '/app/items';
    const method = isEdit ? apiPut : apiPost;
    try {
      await ensureToken();
      await method(url, payload, { headers: { 'Content-Type': 'application/json' } });
      closeModalSafely();
      reloadInventory?.(); // existing function in this module to refresh table
    } catch (_) {
      markInvalid(saveBtn);
    }
  });
}
