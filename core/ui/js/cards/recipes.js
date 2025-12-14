// SPDX-License-Identifier: AGPL-3.0-or-later
import { apiGet, ensureToken } from '../api.js';
import { RecipesAPI } from '../api/recipes.js';
import {
  toMetricBase,
  unitOptionsList,
  dimensionForUnit,
  norm,
  METRIC,
  IMPERIAL_TO_METRIC,
  DIM_DEFAULTS_METRIC,
} from '../lib/units.js';
import { preferredUnitForDimension } from '../lib/unit-preferences.js';

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

let _items = [];
let _recipes = [];
let _activeId = null;
let _draft = null;
let _unitsModeListenerBound = false;

function americanMode() {
  return !!(window.BUS_UNITS && window.BUS_UNITS.american);
}

function normalizeDimension(dim) {
  if (!dim) return null;
  const d = String(dim).toLowerCase();
  if (d === 'mass') return 'weight';
  if (['length', 'area', 'volume', 'weight', 'count'].includes(d)) return d;
  return null;
}

function findItem(itemId) {
  return _items.find((i) => String(i.id) === String(itemId));
}

function defaultUnitFor(itemOrDim) {
  const dim = normalizeDimension(itemOrDim?.dimension || itemOrDim) || 'count';
  return itemOrDim?.uom || itemOrDim?.unit || preferredUnitForDimension(dim);
}

function displayQtyFromBase(base, unit, dimension) {
  const dim = normalizeDimension(dimension) || 'count';
  const u = norm(unit);
  const imperialFactor = IMPERIAL_TO_METRIC[dim]?.[u];
  if (imperialFactor) return (Number(base) || 0) / imperialFactor;
  const factor = METRIC[dim]?.[u] || 1;
  if (!factor) return Number(base) || 0;
  return (Number(base) || 0) / factor;
}

function newRecipeDraft() {
  return {
    id: null,
    name: '',
    output_item_id: null,
    output_qty: 1,
    archived: false,
    notes: '',
    items: [],
  };
}

function blankRecipeItem(sort = 0) {
  return {
    item_id: null,
    qty_required: '',
    unit: null,
    dimension: null,
    optional: false,
    sort,
  };
}

function normalizeRecipe(data) {
  return {
    id: data.id,
    name: data.name || '',
    output_item_id: data.output_item_id ?? null,
    output_qty: data.output_qty || 1,
    archived: data.archived === true || data.is_archived === true,
    notes: data.notes || '',
    items: (data.items || []).map((it, idx) => {
      const meta = findItem(it.item_id) || it.item || {};
      const dim = normalizeDimension(it.dimension || meta.dimension) || 'count';
      const unit = defaultUnitFor(meta) || preferredUnitForDimension(dim);
      const qtyBase = it.qty_required !== undefined && it.qty_required !== null ? Number(it.qty_required) : null;
      const qtyDisplay = qtyBase !== null && Number.isFinite(qtyBase)
        ? displayQtyFromBase(qtyBase, unit, dim)
        : null;
      return {
        item_id: it.item_id ?? null,
        qty_required: qtyDisplay ?? '',
        unit,
        dimension: dim,
        optional: it.optional === true || it.is_optional === true,
        sort: Number.isFinite(it.sort ?? it.sort_order) ? (it.sort ?? it.sort_order) : idx,
      };
    }),
  };
}

async function refreshData() {
  _items = await apiGet('/app/items');
  _recipes = await RecipesAPI.list();
}

export async function mountRecipes() {
  await ensureToken();
  const container = document.querySelector('[data-tab-panel="recipes"]');
  if (!container) return;
  container.innerHTML = '';

  try {
    await refreshData();
  } catch (err) {
    container.textContent = 'Failed to load recipes.';
    return;
  }

  const grid = el('div', { style: 'display:grid;grid-template-columns:1fr 2fr;gap:20px;min-height:calc(100vh - 160px);' });
  const listPanel = el('div', { class: 'card', style: 'overflow:auto;background:#1e1f22;border-radius:10px;border:1px solid #2f3136;' });
  const editorPanel = el('div', { class: 'card', style: 'overflow:auto;background:#1e1f22;border-radius:10px;border:1px solid #2f3136;' });

  grid.append(listPanel, editorPanel);
  container.append(grid);

  renderList(listPanel, editorPanel);
  renderEmpty(editorPanel);
}

export function unmountRecipes() {
  _items = [];
  _recipes = [];
  _activeId = null;
  _draft = null;
  const container = document.querySelector('[data-tab-panel="recipes"]');
  if (container) container.innerHTML = '';
}

function renderList(container, editor) {
  container.innerHTML = '';

  const header = el('div', { style: 'display:flex;justify-content:space-between;align-items:center;margin-bottom:12px' }, [
    el('h2', { text: 'Recipes', style: 'margin:0;' }),
    el('button', { class: 'btn primary small', text: '+ New', style: 'border-radius:10px;padding:8px 12px;' })
  ]);
  header.lastChild.onclick = () => renderCreateForm(editor, container);

  const search = el('input', {
    type: 'search',
    placeholder: 'Filter…',
    style: 'width:100%;margin:6px 0 12px 0;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6'
  });
  const list = el('div', { style: 'display:flex;flex-direction:column;gap:8px' });

  const paint = (term = '') => {
    list.innerHTML = '';
    const q = term.trim().toLowerCase();
    _recipes
      .filter(r => !q || r.name.toLowerCase().includes(q))
      .forEach(r => {
        const row = el('div', {
          class: 'recipe-row',
          style: 'padding:10px 12px;background:#23262b;border-radius:10px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;border:1px solid #2f3136;'
        }, [
          el('span', { text: r.name, style: 'color:#e6e6e6' }),
          el('span', { text: '→', style: 'color:#6b7280' })
        ]);
        if (r.id === _activeId) {
          row.style.background = '#2f333b';
        }
        row.onclick = async () => {
          container.querySelectorAll('.recipe-row').forEach(n => n.style.background = '#23262b');
          row.style.background = '#2f333b';
          _activeId = r.id;
          _draft = normalizeRecipe(await RecipesAPI.get(r.id));
          renderEditor(editor, container);
        };
        list.append(row);
      });
  };

  search.addEventListener('input', (e) => paint(e.target.value));
  paint();
  container.append(header, search, list);
}

function renderEmpty(editor) {
  editor.innerHTML = '';
  editor.append(el('div', { style: 'color:#666;text-align:center;margin-top:50px' }, 'Select a recipe to edit.'));
}

function renderCreateForm(editor, leftPanel) {
  _activeId = null;
  _draft = newRecipeDraft();
  editor.innerHTML = '';

  const title = el('h2', { text: 'Create New Recipe', style: 'margin-top:0' });
  const name = el('input', {
    type: 'text',
    placeholder: 'Recipe Name',
    style: 'width:100%;margin-bottom:12px;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6'
  });
  const save = el('button', { class: 'btn primary', text: 'Create', style: 'border-radius:10px;padding:10px 14px;' });
  const status = el('div', { style: 'min-height:18px;font-size:13px;color:#aaa;margin-top:6px;' });

  save.onclick = async () => {
    const trimmed = name.value.trim();
    if (!trimmed) {
      status.textContent = 'Name is required.';
      status.style.color = '#ff6666';
      return;
    }
    _draft = newRecipeDraft();
    _draft.name = trimmed;
    renderEditor(editor, leftPanel);
  };

  editor.append(title, name, save, status);
}

function renderEditor(editor, leftPanel) {
  editor.innerHTML = '';
  if (!_draft) {
    renderEmpty(editor);
    return;
  }

  const status = el('div', { style: 'min-height:18px;font-size:13px;margin-bottom:6px;color:#9ca3af' });

  const nameRow = el('div', { style: 'display:flex;gap:10px;align-items:center;margin-bottom:10px' });
  const nameInput = el('input', {
    type: 'text',
    value: _draft.name,
    style: 'flex:1;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6'
  });
  nameInput.addEventListener('input', () => { _draft.name = nameInput.value; });
  nameRow.append(el('label', { text: 'Name', style: 'width:90px;color:#cdd1dc' }), nameInput);
  // (reserved) Code field intentionally not rendered; kept for future features and omitted from payloads.
  const outputRow = el('div', { style: 'display:flex;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap' });
  const outSel = el('select', {
    id: 'recipe-output',
    style: 'flex:1;min-width:200px;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6'
  });
  outSel.append(el('option', { value: '', disabled: 'true', selected: _draft.output_item_id == null ? 'selected' : undefined }, '— Output Item —'));
  _items.forEach((i) => {
    outSel.append(
      el('option', { value: String(i.id) }, i.name)
    );
  });
  if (_draft.output_item_id != null) {
    outSel.value = String(_draft.output_item_id);
  }
  outSel.addEventListener('change', () => {
    const parsed = parseInt(outSel.value, 10);
    _draft.output_item_id = Number.isFinite(parsed) ? parsed : null;
  });
  outputRow.append(
    el('label', { text: 'Output Item', style: 'width:90px;color:#cdd1dc' }),
    outSel,
  );

  const flagsRow = el('div', { style: 'display:flex;gap:16px;align-items:center;margin-bottom:10px' });
  const archivedToggle = el('input', { type: 'checkbox' });
  archivedToggle.checked = _draft.archived === true;
  archivedToggle.addEventListener('change', () => { _draft.archived = archivedToggle.checked; });
  flagsRow.append(archivedToggle, el('span', { text: 'Archived', style: 'color:#cdd1dc' }));

  const notes = el('textarea', {
    value: _draft.notes || '',
    placeholder: 'Notes',
    style: 'width:100%;min-height:80px;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6;margin-bottom:10px;'
  });
  notes.addEventListener('input', () => { _draft.notes = notes.value; });

  const itemsBox = el('div', { style: 'background:#23262b;padding:14px;border-radius:10px;border:1px solid #2f3136;margin-bottom:12px' });
  const itemsHeader = el('div', { style: 'display:flex;justify-content:space-between;align-items:center;margin-bottom:10px' }, [
    el('h4', { text: 'Input Items', style: 'margin:0;color:#e6e6e6' }),
    el('button', { class: 'btn small', text: '+ Add', style: 'border-radius:10px;padding:8px 12px;' })
  ]);

  const table = el('table', { style: 'width:100%;border-collapse:collapse;background:#1e1f22;border:1px solid #2f3136;border-radius:10px;overflow:hidden;' });
  const thead = el('thead', { style: 'background:#202226' }, el('tr', {}, [
    el('th', { style: 'text-align:left;padding:10px;color:#e6e6e6' }, 'Item'),
    el('th', { style: 'text-align:right;padding:10px;color:#e6e6e6' }, 'Qty + Unit'),
    el('th', { style: 'text-align:center;padding:10px;color:#e6e6e6' }, 'Optional'),
    el('th', { style: 'width:60px;text-align:right' }, '')
  ]));
  const tbody = el('tbody');
  table.append(thead, tbody);

  function buildUnitSelectForDimension(dim, current) {
    const select = el('select', {
      class: 'input',
      style: 'min-width:100px;padding:8px 10px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6',
    });
    unitOptionsList({ american: americanMode() }).forEach((g) => {
      if (g.dim !== dim && g.dim !== 'count') return;
      const og = document.createElement('optgroup');
      og.label = g.label;
      g.units.forEach((u) => {
        const opt = document.createElement('option');
        opt.value = u;
        opt.textContent = u.replace('_', '-');
        og.appendChild(opt);
      });
      select.appendChild(og);
    });
    if (current) select.value = current;
    return select;
  }

  function renderItemRows() {
    tbody.innerHTML = '';
    _draft.items.forEach((ri, idx) => {
      const row = el('tr', { style: 'border-bottom:1px solid #2f3136' });
      const itemSel = el('select', { style: 'width:100%;padding:8px 10px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
      itemSel.append(el('option', { value: '', selected: ri.item_id == null ? 'selected' : undefined }, '— Select —'));
      _items.forEach(i => {
        const opt = el('option', { value: i.id, selected: String(i.id) === String(ri.item_id) ? 'selected' : undefined }, i.name);
        if (i.dimension) opt.dataset.dimension = i.dimension;
        itemSel.append(opt);
      });
      itemSel.value = ri.item_id == null ? '' : String(ri.item_id);

      const itemMeta = findItem(ri.item_id) || {};
      const dim = normalizeDimension(ri.dimension || itemMeta.dimension || dimensionForUnit(ri.unit)) || 'count';
      ri.dimension = dim;
      ri.unit = ri.unit || defaultUnitFor(itemMeta || dim);

      const qtyInput = el('input', {
        type: 'number',
        min: '0.0001',
        step: '0.01',
        value: ri.qty_required ?? '',
        style: 'width:120px;text-align:right;padding:8px 10px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6'
      });
      qtyInput.addEventListener('input', () => {
        const parsed = parseFloat(qtyInput.value);
        ri.qty_required = Number.isFinite(parsed) ? parsed : null;
        renderPreview();
      });

      let unitSel = buildUnitSelectForDimension(dim, ri.unit);
      unitSel.addEventListener('change', () => {
        const prevDim = ri.dimension;
        ri.unit = unitSel.value;
        ri.dimension = normalizeDimension(dimensionForUnit(unitSel.value)) || ri.dimension;
        renderPreview();
        if (prevDim !== ri.dimension) setTimeout(renderItemRows, 0);
      });

      itemSel.addEventListener('change', () => {
        const prevDim = ri.dimension;
        ri.item_id = itemSel.value ? Number(itemSel.value) : null;
        const nextMeta = findItem(ri.item_id) || {};
        const nextDim = normalizeDimension(nextMeta.dimension) || ri.dimension || 'count';
        ri.dimension = nextDim;
        const nextUnit = defaultUnitFor(nextMeta) || preferredUnitForDimension(nextDim);
        ri.unit = nextUnit;
        const replacement = buildUnitSelectForDimension(nextDim, nextUnit);
        unitSel.replaceWith(replacement);
        unitSel = replacement;
        unitSel.addEventListener('change', () => {
          ri.unit = unitSel.value;
          ri.dimension = normalizeDimension(dimensionForUnit(unitSel.value)) || ri.dimension;
          renderPreview();
        });
        renderPreview();
        if (prevDim !== nextDim) setTimeout(renderItemRows, 0);
      });

      const qtyWrap = el('div', { style: 'display:flex;gap:8px;align-items:center;justify-content:flex-end;flex-wrap:wrap;' });
      qtyWrap.append(qtyInput, unitSel);

      let helper = null;
      if (ri.dimension === 'area') {
        const lenInput = el('input', { type: 'number', min: '0', step: 'any', placeholder: 'L', style: 'width:90px;padding:6px 8px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
        const widInput = el('input', { type: 'number', min: '0', step: 'any', placeholder: 'W', style: 'width:90px;padding:6px 8px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
        const baseSel = el('select', { style: 'min-width:80px;padding:6px 8px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
        (americanMode() ? ['in', 'ft'] : ['cm', 'm']).forEach((u) => baseSel.append(el('option', { value: u, text: u })));
        const applyBtn = el('button', { class: 'btn small', text: 'Apply', type: 'button', style: 'padding:6px 8px;border-radius:10px;' });
        helper = el('div', { style: 'display:flex;gap:6px;align-items:center;margin-top:6px;justify-content:flex-end;flex-wrap:wrap;' }, [
          el('span', { class: 'sub', text: 'L×W helper', style: 'opacity:0.8' }),
          lenInput,
          el('span', { text: '×', style: 'color:#9ca3af' }),
          widInput,
          baseSel,
          applyBtn,
        ]);
        applyBtn.addEventListener('click', () => {
          const L = parseFloat(lenInput.value || '0');
          const W = parseFloat(widInput.value || '0');
          if (!Number.isFinite(L) || !Number.isFinite(W) || L <= 0 || W <= 0) return;
          const unit = baseSel.value || 'cm';
          const area = L * W;
          const areaUnit = unit === 'in' ? 'in2' : unit === 'ft' ? 'ft2' : unit === 'm' ? 'm2' : 'cm2';
          qtyInput.value = area;
          ri.qty_required = area;
          ri.unit = areaUnit;
          ri.dimension = 'area';
          const replacement = buildUnitSelectForDimension('area', areaUnit);
          unitSel.replaceWith(replacement);
          unitSel = replacement;
          unitSel.addEventListener('change', () => {
            ri.unit = unitSel.value;
            ri.dimension = normalizeDimension(dimensionForUnit(unitSel.value)) || 'area';
            renderPreview();
          });
          renderPreview();
        });
      }

      const optBox = el('input', { type: 'checkbox', checked: ri.optional === true ? 'checked' : undefined });
      optBox.checked = ri.optional === true;
      optBox.addEventListener('change', () => { ri.optional = optBox.checked; });

      const delBtn = el('button', {
        class: 'btn danger btn-icon',
        type: 'button',
        text: '×',
        title: 'Remove input',
        'aria-label': 'Remove input',
      });
      delBtn.addEventListener('click', () => {
        _draft.items = _draft.items.filter((_, i) => i !== idx);
        renderItemRows();
      });

      const preview = el('div', { class: 'sub', style: 'margin-top:6px;color:#9ca3af;text-align:right;min-height:18px;' });

      function renderPreview() {
        const qtyVal = parseFloat(qtyInput.value || '0');
        const unit = ri.unit || unitSel.value;
        const dimNow = normalizeDimension(ri.dimension || dimensionForUnit(unit)) || 'count';
        if (!ri.item_id || !Number.isFinite(qtyVal) || qtyVal <= 0) {
          preview.textContent = '';
          return;
        }
        const converted = toMetricBase({ dimension: dimNow, qty: qtyVal, qtyUnit: unit, unitPrice: 0, priceUnit: unit });
        const baseQty = converted.qtyBase;
        let text = baseQty != null ? `Base: ${baseQty.toLocaleString()} (${unit} → ${DIM_DEFAULTS_METRIC[dimNow] || 'base'})` : '';
        const meta = findItem(ri.item_id);
        const fifoCents = meta?.fifo_unit_cost_cents;
        const priceUnit = meta?.stock_on_hand_display?.unit || meta?.uom || meta?.unit || unit;
        if (fifoCents != null && baseQty != null) {
          const pricePerUnit = fifoCents / 100;
          const costConv = toMetricBase({ dimension: dimNow, qty: 1, qtyUnit: priceUnit, unitPrice: pricePerUnit, priceUnit });
          const pricePerBase = costConv.pricePerBase ?? pricePerUnit;
          const est = baseQty * pricePerBase;
          if (Number.isFinite(est)) text += ` • est cost $${est.toFixed(2)}`;
        }
        preview.textContent = text;
      }

      const qtyCell = el('td', { style: 'padding:10px;text-align:right' });
      qtyCell.append(qtyWrap);
      if (helper) qtyCell.append(helper);
      qtyCell.append(preview);

      row.append(
        el('td', { style: 'padding:10px' }, itemSel),
        qtyCell,
        el('td', { style: 'padding:10px;text-align:center' }, optBox),
        el('td', { style: 'padding:10px;text-align:right' }, delBtn)
      );
      tbody.append(row);
      renderPreview();
    });
  }

  if (!_unitsModeListenerBound) {
    document.addEventListener('bus:units-mode', () => renderItemRows());
    _unitsModeListenerBound = true;
  }

  itemsHeader.lastChild.onclick = () => {
    _draft.items.push(blankRecipeItem(_draft.items.length));
    renderItemRows();
  };

  renderItemRows();
  itemsBox.append(itemsHeader, table);

  const actions = el('div', { style: 'display:flex;justify-content:space-between;gap:10px;align-items:center;margin-top:6px' });
  const saveBtn = el('button', { class: 'btn primary', text: 'Save Recipe', style: 'border-radius:10px;padding:10px 14px;' });
  const deleteBtn = el('button', {
    id: 'recipe-delete',
    class: 'btn',
    text: 'Delete',
    style: 'border-radius:10px;padding:10px 14px;background:#3a3d43;color:#e6e6e6;border:1px solid #2f3136',
  });
  deleteBtn.disabled = !_draft.id;

  function serializeDraft() {
    const nameVal = (_draft.name || '').trim();
    const notesVal = (_draft.notes || '').trim();
    const selectedOutput = (() => {
      const sel = document.getElementById('recipe-output');
      if (sel && sel.value) {
        const parsed = parseInt(sel.value, 10);
        _draft.output_item_id = Number.isFinite(parsed) ? parsed : null;
      }
      return _draft.output_item_id;
    })();

    const cleanedItems = (_draft.items || [])
      .map((it) => {
        const meta = findItem(it.item_id) || {};
        const dim = normalizeDimension(it.dimension || meta.dimension || dimensionForUnit(it.unit)) || 'count';
        const unit = it.unit || defaultUnitFor(meta) || preferredUnitForDimension(dim);
        const qtyVal = Number(it.qty_required);
        const converted = toMetricBase({ dimension: dim, qty: qtyVal, qtyUnit: unit, unitPrice: 0, priceUnit: unit });
        const qtyBase = converted?.qtyBase;
        return {
          item_id: it.item_id,
          qty_required: qtyBase,
          optional: it.optional === true || it.is_optional === true,
          unit,
          dimension: dim,
        };
      })
      .filter(it => it.item_id && Number.isFinite(it.qty_required) && it.qty_required > 0);

    const errors = [];
    if (!nameVal) errors.push('Name is required.');
    if (!selectedOutput) errors.push('Choose an output item.');
    if (cleanedItems.length === 0) errors.push('Add at least one input item with quantity.');
    if (errors.length) {
      throw new Error(errors.join(' '));
    }

    return {
      id: _draft.id,
      name: nameVal,
      output_item_id: Number(selectedOutput),
      output_qty: 1,
      archived: !!_draft.archived,
      notes: notesVal || null,
      items: cleanedItems.map((it, idx) => ({
        item_id: Number(it.item_id),
        qty_required: Number(it.qty_required),
        optional: it.optional === true,
        sort: idx,
      })),
    };
  }

  saveBtn.onclick = async () => {
    status.textContent = '';
    status.style.color = '#9ca3af';

    const archivedValue = !!archivedToggle.checked;
    _draft.archived = archivedValue;
    let payload;
    try {
      payload = serializeDraft();
    } catch (err) {
      status.textContent = err?.message || 'Please complete required fields.';
      status.style.color = '#ff6666';
      return;
    }

    try {
      await ensureToken();
      const saved = _draft.id
        ? await RecipesAPI.update(_draft.id, payload)
        : await RecipesAPI.create(payload);
      _draft = normalizeRecipe(saved || await RecipesAPI.get(_draft.id));
      _activeId = _draft.id;
      await refreshData();
      renderList(leftPanel, editor);
      status.textContent = 'Saved';
      status.style.color = '#4caf50';
    } catch (e) {
      status.textContent = (e?.data?.detail?.message || e?.message || 'Save failed');
      status.style.color = '#ff6666';
    }
  };

  deleteBtn.onclick = async () => {
    if (!_draft?.id) return;
    if (!confirm('Delete this recipe? This cannot be undone.')) return;
    status.textContent = '';
    status.style.color = '#9ca3af';
    deleteBtn.disabled = true;
    const resetLabel = deleteBtn.textContent;
    deleteBtn.textContent = 'Deleting…';
    try {
      await ensureToken();
      await RecipesAPI.delete(_draft.id);
      await refreshData();
      _activeId = null;
      _draft = null;
      renderList(leftPanel, editor);
      renderEmpty(editor);
      status.textContent = 'Deleted';
      status.style.color = '#4caf50';
    } catch (e) {
      status.textContent = (e?.detail?.message || e?.detail || e?.message || 'Delete failed');
      status.style.color = '#ff6666';
    } finally {
      deleteBtn.disabled = false;
      deleteBtn.textContent = resetLabel;
    }
  };

  actions.append(status, el('div', { style: 'display:flex;gap:8px;align-items:center' }, [deleteBtn, saveBtn]));

  editor.append(
    el('h2', { text: 'Edit Recipe', style: 'margin-top:0' }),
    nameRow,
    outputRow,
    flagsRow,
    notes,
    itemsBox,
    actions,
  );
}
