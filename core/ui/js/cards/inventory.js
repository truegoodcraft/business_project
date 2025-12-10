// SPDX-License-Identifier: AGPL-3.0-or-later
// Inventory card with smart input parsing.

import { apiGetJson, apiPost, apiPut, apiDelete, ensureToken } from '../api.js';

const UNIT_OPTIONS = {
  length: ['mm', 'cm', 'm'],
  area: ['mm2', 'cm2', 'm2'],
  volume: ['mm3', 'cm3', 'm3', 'ml'],
  weight: ['mg', 'g', 'kg'],
  count: ['ea'],
};

const BASE_UNIT_LABEL = {
  length: 'mm',
  area: 'mm²',
  volume: 'mm³',
  weight: 'mg',
  count: 'milli-units',
};

const UNIT_LABEL = {
  mm: 'mm',
  cm: 'cm',
  m: 'm',
  mm2: 'mm²',
  cm2: 'cm²',
  m2: 'm²',
  mm3: 'mm³',
  cm3: 'cm³',
  m3: 'm³',
  ml: 'ml',
  mg: 'mg',
  g: 'g',
  kg: 'kg',
  ea: 'ea',
};

const MULT = {
  length: { mm: 1, cm: 10, m: 1000 },
  area: { mm2: 1, cm2: 100, m2: 1_000_000 },
  volume: { mm3: 1, cm3: 1_000, m3: 1_000_000_000, ml: 1_000 },
  weight: { mg: 1, g: 1_000, kg: 1_000_000 },
  count: { ea: 1_000 },
};

// Keep delegated handler binding stable across route changes
let _rootEl = null;
let _clickBound = false;
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

export function mountInventory() {
  const container = document.querySelector('[data-role="inventory-root"]');
  if (!container) return;
  _rootEl = container;
  _mountInventory(container);
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
    const qtyText = (item.quantity_display?.value && item.quantity_display?.unit)
      ? `${item.quantity_display.value} ${item.quantity_display.unit}`
      : `${item.qty ?? 0} ${item.unit || ''}`.trim();
    row.append(
      el('td', { text: item.name || 'Item' }),
      el('td', { text: item.sku || '—' }),
      el('td', { text: qtyText }),
      el('td', { text: item.vendor || '—' }),
      el('td', { text: item.price != null ? `$${Number(item.price).toFixed(2)}` : '—' }),
      el('td', { text: item.location || '—' })
    );
    tbody.append(row);
  });
}

async function adjustQuantity(itemId) {
  const deltaStr = prompt('Adjust quantity by (e.g. -2 or 5):');
  if (deltaStr === null) return;
  const delta = Number(deltaStr);
  if (!Number.isFinite(delta)) return alert('Enter a valid number');
  await ensureToken();
  await apiPost('/app/inventory/run', { inputs: {}, outputs: { [itemId]: delta } });
}

export async function _mountInventory(container) {
  await ensureToken();
  const state = { items: [], tableBody: null };

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
            kv('Quantity', (item.quantity_display?.value && item.quantity_display?.unit)
              ? `${item.quantity_display.value} ${item.quantity_display.unit}`
              : `${item.qty ?? 0} ${item.unit || ''}`.trim()),
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
    // Keep UI simple; replace with nicer modal if desired
    return Promise.resolve(window.confirm('Delete this item? This cannot be undone.'));
  }

  await reloadInventory();
}

// ---------- Shallow/Deep Modal ----------
async function fetchVendors() {
  // Not specified in the SoT you've given me: exact vendor endpoint/shape.
  // Try /app/vendors first; fall back to /app/contacts.
  try {
    const v = await apiGetJson('/app/vendors?is_vendor=true');
    if (Array.isArray(v)) return v;
  } catch (_) {/* ignore */}
  try {
    const c = await apiGetJson('/app/contacts?is_vendor=true');
    if (Array.isArray(c)) {
      // Map into minimal { id, name } expected by dropdown
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

  const errorBanner = document.createElement('div');
  errorBanner.id = 'add-item-error';
  errorBanner.className = 'error-banner';
  errorBanner.hidden = true;
  card.appendChild(errorBanner);

  // FORM state
  let expanded = !!(item?.sku || item?.vendor_id || item?.notes);

  // Elements – Speed Surface
  const fName = inputRow('Name', 'text', item?.name ?? '', { autofocus: true });
  const dimensionSelect = createSelect('item-dimension', [
    ['length', 'Length'],
    ['area', 'Area'],
    ['volume', 'Volume'],
    ['weight', 'Weight'],
    ['count', 'Count'],
  ]);
  const dimensionRow = fieldRowWithElement('Dimension', dimensionSelect);

  const unitSelect = createSelect('item-unit');
  const unitRow = fieldRowWithElement('Unit', unitSelect);

  const qtyInput = document.createElement('input');
  qtyInput.type = 'number';
  qtyInput.id = 'item-qty-dec';
  qtyInput.setAttribute('step', '0.001');
  qtyInput.setAttribute('min', '0');
  qtyInput.required = true;
  const qtyRow = fieldRowWithElement('Quantity', qtyInput);

  const qtyPreview = document.createElement('div');
  qtyPreview.id = 'item-qty-preview';
  qtyPreview.className = 'muted';

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
  content.append(fName, dimensionRow, unitRow, qtyRow, qtyPreview, fPrice, fLocation, hinge, ledger, footer);
  card.appendChild(content);
  overlay.appendChild(card);
  document.body.appendChild(overlay);

  // Auto-focus and prefill qty badge if editing
  fName.querySelector('input')?.focus();
  initAddItemFormDefaults();

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

  function populateUnits(presetUnit = null) {
    const dim = dimensionSelect.value;
    const opts = UNIT_OPTIONS[dim] || [];
    unitSelect.innerHTML = opts.map((u) => `<option value="${u}">${UNIT_LABEL[u] || u}</option>`).join('');
    const targetUnit = (presetUnit && opts.includes(presetUnit)) ? presetUnit : opts[0];
    if (targetUnit) unitSelect.value = targetUnit;
    updatePreview();
  }

  function toBaseIntForPreview(value, unit, dim) {
    const n = Number(value);
    if (!Number.isFinite(n)) return 0;
    const mult = MULT[dim]?.[unit];
    if (!mult) return 0;
    return Math.floor(n * mult + 0.5);
  }

  function updatePreview() {
    const dim = dimensionSelect.value;
    const unit = unitSelect.value;
    const val = qtyInput.value;
    if (!dim || !unit || val === '') {
      qtyPreview.textContent = '';
      return;
    }
    const baseInt = toBaseIntForPreview(val, unit, dim);
    qtyPreview.textContent = `Will store: ${baseInt} ${BASE_UNIT_LABEL[dim]}`;
  }

  function initAddItemFormDefaults() {
    const defaultDim = item?.dimension || dimensionSelect.value || 'count';
    dimensionSelect.value = defaultDim;
    populateUnits(item?.quantity_display?.unit || item?.unit);
    const qtyVal = item?.quantity_display?.value ?? (item?.qty ?? '');
    if (qtyVal !== undefined && qtyVal !== null) qtyInput.value = qtyVal;
    updatePreview();
  }

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

  dimensionSelect.addEventListener('change', () => populateUnits());
  unitSelect.addEventListener('change', () => updatePreview());
  qtyInput.addEventListener('input', () => updatePreview());

  function fieldValue(rowSel) {
    return rowSel.querySelector('input,textarea,select')?.value ?? '';
  }

  function fieldRowWithElement(labelText, element) {
    const row = document.createElement('div');
    row.className = 'field-row';
    const label = document.createElement('label');
    label.textContent = labelText;
    const wrap = document.createElement('div');
    wrap.className = 'field-input';
    if (element) wrap.appendChild(element);
    row.append(label, wrap);
    return row;
  }

  function createSelect(id, options = []) {
    const select = document.createElement('select');
    if (id) select.id = id;
    select.required = true;
    options.forEach(([value, text]) => {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = text;
      select.appendChild(opt);
    });
    return select;
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

    if (errorBanner) {
      errorBanner.hidden = true;
      errorBanner.textContent = '';
    }

    // Client-side validation
    if (!name) return markInvalid(fName.querySelector('input'));

    const dimensionVal = dimensionSelect.value;
    const unitVal = unitSelect.value;
    const qtyVal = qtyInput.value;

    if (!dimensionVal) return markInvalid(dimensionSelect);
    if (!unitVal) return markInvalid(unitSelect);
    if (qtyVal === '') return markInvalid(qtyInput);

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
      dimension: dimensionVal,
      uom: unitVal,
      unit: unitVal,
      quantity_decimal: qtyVal,
    };

    const url = isEdit ? `/items/${item.id}` : '/items';
    const method = isEdit ? apiPut : apiPost;
    try {
      await ensureToken();
      await method(url, payload, { headers: { 'Content-Type': 'application/json' } });
      closeModalSafely();
      reloadInventory?.(); // existing function in this module to refresh table
    } catch (err) {
      const serverMsg = err?.detail?.message || err?.error || err?.message || 'Save failed.';
      if (errorBanner) {
        errorBanner.textContent = serverMsg;
        errorBanner.hidden = false;
      }
      markInvalid(saveBtn);
    }
  });
}

