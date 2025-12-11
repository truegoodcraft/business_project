// SPDX-License-Identifier: AGPL-3.0-or-later
import { apiGet, ensureToken } from '../api.js';
import { RecipesAPI } from '../api/recipes.js';

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

function newRecipeDraft() {
  return {
    id: null,
    name: '',
    code: '',
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
    qty_required: null,
    optional: false,
    sort,
  };
}

function normalizeRecipe(data) {
  return {
    id: data.id,
    name: data.name || '',
    code: data.code || '',
    output_item_id: data.output_item_id ?? null,
    output_qty: data.output_qty || 1,
    archived: data.archived === true || data.is_archived === true,
    notes: data.notes || '',
    items: (data.items || []).map((it, idx) => ({
      item_id: it.item_id ?? null,
      qty_required: it.qty_required !== undefined && it.qty_required !== null
        ? Number(it.qty_required)
        : null,
      optional: it.optional === true || it.is_optional === true,
      sort: Number.isFinite(it.sort ?? it.sort_order) ? (it.sort ?? it.sort_order) : idx,
    })),
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

  const codeRow = el('div', { style: 'display:flex;gap:10px;align-items:center;margin-bottom:10px' });
  const codeInput = el('input', {
    type: 'text',
    value: _draft.code,
    placeholder: 'Optional code',
    style: 'flex:1;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6'
  });
  codeInput.addEventListener('input', () => { _draft.code = codeInput.value; });
  codeRow.append(el('label', { text: 'Code', style: 'width:90px;color:#cdd1dc' }), codeInput);

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
    el('h4', { text: 'Items', style: 'margin:0;color:#e6e6e6' }),
    el('button', { class: 'btn small', text: '+ Add', style: 'border-radius:10px;padding:8px 12px;' })
  ]);

  const table = el('table', { style: 'width:100%;border-collapse:collapse;background:#1e1f22;border:1px solid #2f3136;border-radius:10px;overflow:hidden;' });
  const thead = el('thead', { style: 'background:#202226' }, el('tr', {}, [
    el('th', { style: 'text-align:left;padding:10px;color:#e6e6e6' }, 'Item'),
    el('th', { style: 'text-align:right;padding:10px;color:#e6e6e6' }, 'Qty Required'),
    el('th', { style: 'text-align:center;padding:10px;color:#e6e6e6' }, 'Optional'),
    el('th', { style: 'text-align:right;padding:10px;color:#e6e6e6' }, 'Sort'),
    el('th', { style: 'width:60px' }, '')
  ]));
  const tbody = el('tbody');
  table.append(thead, tbody);

  function renderItemRows() {
    tbody.innerHTML = '';
    _draft.items
      .sort((a, b) => (a.sort ?? a.sort_order ?? 0) - (b.sort ?? b.sort_order ?? 0))
      .forEach((ri, idx) => {
        const row = el('tr', { style: 'border-bottom:1px solid #2f3136' });
        const itemSel = el('select', { style: 'width:100%;padding:8px 10px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
        itemSel.append(el('option', { value: '', disabled: 'true', selected: ri.item_id == null ? 'selected' : undefined }, '— Select —'));
        _items.forEach(i => itemSel.append(el('option', { value: i.id, selected: String(i.id) === String(ri.item_id) ? 'selected' : undefined }, i.name)));
        itemSel.addEventListener('change', () => {
          ri.item_id = itemSel.value ? Number(itemSel.value) : null;
        });

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
        });

        const optBox = el('input', { type: 'checkbox', checked: ri.optional === true ? 'checked' : undefined });
        optBox.checked = ri.optional === true;
        optBox.addEventListener('change', () => { ri.optional = optBox.checked; });

        const sortInput = el('input', {
          type: 'number',
          value: ri.sort ?? ri.sort_order ?? idx,
          style: 'width:70px;text-align:right;padding:8px 10px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6'
        });
        sortInput.addEventListener('input', () => { ri.sort = parseInt(sortInput.value || `${idx}`, 10); });

        const delBtn = el('button', { class: 'btn small', text: 'Remove', style: 'border-radius:10px;padding:6px 10px;background:#3a3d43;color:#e6e6e6;border:1px solid #2f3136' });
        delBtn.addEventListener('click', () => {
          _draft.items = _draft.items.filter((_, i) => i !== idx);
          renderItemRows();
        });

        row.append(
          el('td', { style: 'padding:10px' }, itemSel),
          el('td', { style: 'padding:10px;text-align:right' }, qtyInput),
          el('td', { style: 'padding:10px;text-align:center' }, optBox),
          el('td', { style: 'padding:10px;text-align:right' }, sortInput),
          el('td', { style: 'padding:10px;text-align:right' }, delBtn)
        );
        tbody.append(row);
      });
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
    const codeVal = (_draft.code || '').trim();
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
      .map((it, idx) => ({
        item_id: it.item_id,
        qty_required: it.qty_required,
        optional: it.optional === true || it.is_optional === true,
        sort: (it.sort ?? it.sort_order ?? idx)
      }))
      .filter(it => it.item_id && it.qty_required !== null && it.qty_required !== '' && Number(it.qty_required) > 0);

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
      code: codeVal || null,
      output_item_id: Number(selectedOutput),
      output_qty: 1,
      archived: !!_draft.archived,
      notes: notesVal || null,
      items: cleanedItems.map((it, idx) => ({
        item_id: Number(it.item_id),
        qty_required: Number(it.qty_required),
        optional: it.optional === true,
        sort: Number.isFinite(it.sort) ? it.sort : idx,
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
    codeRow,
    outputRow,
    flagsRow,
    notes,
    itemsBox,
    actions,
  );
}
