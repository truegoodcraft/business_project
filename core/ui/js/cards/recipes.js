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
let _active = null;

export async function mountRecipes() {
  await ensureToken();
  const container = document.querySelector('[data-tab-panel="recipes"]');
  if (!container) return;
  container.innerHTML = '';

  try {
    _items = await apiGet('/app/items');
    _recipes = await RecipesAPI.list();
  } catch (e) {
    container.textContent = 'Failed to load data.';
    return;
  }

  const grid = el('div', { style: 'display:grid;grid-template-columns:1fr 2fr;gap:20px;min-height:calc(100vh - 160px);' });
  const listPanel = el('div', { class: 'card', style: 'overflow:auto;background:#1e1f22;border-radius:10px;border:1px solid #2f3136;' });
  const editorPanel = el('div', { class: 'card', style: 'overflow:auto;background:#1e1f22;border-radius:10px;border:1px solid #2f3136;' });
  grid.append(listPanel, editorPanel);
  container.append(grid);

  renderList(listPanel, editorPanel);
  renderEmptyEditor(editorPanel);
}

export function unmountRecipes() {
  _items = [];
  _recipes = [];
  _active = null;
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

  const search = el('input', { type: 'search', placeholder: 'Filter…', style: 'width:100%;margin:6px 0 12px 0;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
  const list = el('div', { style: 'display:flex;flex-direction:column;gap:8px' });

  const paint = (term = '') => {
    list.innerHTML = '';
    const q = term.trim().toLowerCase();
    _recipes
      .filter(r => !q || r.name.toLowerCase().includes(q))
      .forEach(r => {
        const row = el('div', { class: 'recipe-row', style: 'padding:10px 12px;background:#23262b;border-radius:10px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;border:1px solid #2f3136;' }, [
          el('span', { text: r.name, style: 'color:#e6e6e6' }),
          el('span', { text: '→', style: 'color:#6b7280' })
        ]);
        row.onclick = async () => {
          container.querySelectorAll('.recipe-row').forEach(n => n.style.background = '#23262b');
          row.style.background = '#2f333b';
          _active = await RecipesAPI.get(r.id);
          renderEditor(editor, container);
        };
        list.append(row);
      });
  };

  search.addEventListener('input', (e) => paint(e.target.value));
  paint();
  container.append(header, search, list);
}

function renderEmptyEditor(right) {
  right.innerHTML = '';
  right.append(el('div', { style: 'color:#666;text-align:center;margin-top:50px' }, 'Select a recipe to edit.'));
}

function renderCreateForm(right, left) {
  right.innerHTML = '';
  right.append(el('h2', { text: 'Create New Recipe', style: 'margin-top:0' }));

  const name = el('input', { type: 'text', placeholder: 'Recipe Name', style: 'width:100%;margin-bottom:12px;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
  const save = el('button', { class: 'btn primary', text: 'Create', style: 'border-radius:10px;padding:10px 14px;' });

  save.onclick = async () => {
    if (!name.value.trim()) return;
    try {
      await RecipesAPI.create({ name: name.value.trim() });
      _recipes = await RecipesAPI.list();
      renderList(left, right);
      const created = _recipes.find(r => r.name === name.value.trim());
      if (created) {
        _active = await RecipesAPI.get(created.id);
        renderEditor(right, left);
      }
    } catch (e) {
      alert('Failed to create recipe');
    }
  };

  right.append(name, save);
}

function renderEditor(right, left) {
  right.innerHTML = '';
  if (!_active) return renderEmptyEditor(right);

  const nameRow = el('div', { style: 'display:flex;gap:10px;align-items:center;margin-bottom:8px' });
  const nameInput = el('input', { type: 'text', value: _active.name, style: 'flex:1;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
  const saveName = el('button', { class: 'btn small', text: 'Save', style: 'border-radius:10px;padding:9px 14px;' });
  saveName.onclick = async () => {
    try {
      await RecipesAPI.update(_active.id, { name: nameInput.value.trim() });
      _active = await RecipesAPI.get(_active.id);
      _recipes = await RecipesAPI.list();
      renderList(left, right);
      renderEditor(right, left);
    } catch (e) {
      alert('Failed to update name');
    }
  };
  nameRow.append(nameInput, saveName);

  const outRow = el('div', { style: 'display:flex;gap:10px;align-items:center;margin-bottom:14px' });
  const outLabel = el('label', {}, [el('div', { text: 'Output Item', style:'font-size:12px;color:#aaa;margin-bottom:4px' })]);
  const outSel = el('select', { style: 'min-width:280px;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
  outSel.append(el('option', { value: '' }, '— Select output —'));
  _items.forEach(i => outSel.append(el('option', { value: i.id, selected: String(i.id) === String(_active.output_item_id) ? 'selected' : undefined }, i.name)));
  outSel.addEventListener('change', async () => {
    try {
      const val = outSel.value ? Number(outSel.value) : null;
      await RecipesAPI.update(_active.id, { output_item_id: val });
      _active = await RecipesAPI.get(_active.id);
    } catch (e) {
      alert('Failed to set output item');
    }
  });
  outRow.append(outLabel, outSel);

  const table = el('table', { style: 'width:100%;border-collapse:collapse;margin-bottom:14px;background:#1e1f22;border:1px solid #2f3136;border-radius:10px;overflow:hidden;' });
  const thead = el('thead', { style:'background:#202226' }, el('tr', {}, [
    el('th', { style:'text-align:left;padding:10px;color:#e6e6e6', text: 'Item' }),
    el('th', { style:'text-align:right;padding:10px;color:#e6e6e6', text: 'Qty/Unit (qty_stored)' }),
    el('th', { style:'text-align:right;padding:10px;color:#e6e6e6', text: 'Role' }),
    el('th', { style:'width:40px' }),
  ]));
  const tbody = el('tbody');

  _active.items.forEach(ri => {
    const row = el('tr', { style:'border-bottom:1px solid #2f3136' });

    const roleSel = el('select', { style:'padding:8px 10px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
    roleSel.append(el('option', { value:'input', selected: ri.role === 'input' ? 'selected' : undefined }, 'Input'));
    roleSel.append(el('option', { value:'output', selected: ri.role === 'output' ? 'selected' : undefined }, 'Output'));

    const qty = el('input', { type:'number', value:String(ri.qty_stored), style:'width:140px;text-align:right;padding:8px 10px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });

    const saveBtn = el('button', { class:'btn small', text:'Save', style:'border-radius:10px;padding:8px 12px;' });
    saveBtn.onclick = async () => {
      const payload = { role: roleSel.value, qty_stored: parseFloat(qty.value) };
      if (!(payload.qty_stored > 0)) return alert('Qty must be > 0');
      try {
        await RecipesAPI.updateItem(_active.id, ri.item_id, payload);
        _active = await RecipesAPI.get(_active.id);
        renderEditor(right, left);
      } catch (e) {
        alert('Failed to update line');
      }
    };

    const delBtn = el('button', { style:'color:#ef4444;background:none;border:none;cursor:pointer;padding:0 6px;font-size:18px;line-height:1' }, '×');
    delBtn.onclick = async () => {
      if (!confirm('Remove this item?')) return;
      try {
        await RecipesAPI.removeItem(_active.id, ri.item_id);
        _active = await RecipesAPI.get(_active.id);
        renderEditor(right, left);
      } catch (e) {
        alert('Failed to remove line');
      }
    };

    row.append(
      el('td', { style:'padding:10px;color:#e6e6e6' }, ri.item?.name ?? `#${ri.item_id}`),
      el('td', { style:'padding:10px;text-align:right' }, qty),
      el('td', { style:'padding:10px;text-align:right' }, roleSel),
      el('td', { style:'padding:10px;text-align:right' }, el('div', { style:'display:flex;gap:6px;justify-content:flex-end' }, [saveBtn, delBtn]))
    );

    tbody.append(row);
  });

  table.append(thead, tbody);

  const addBox = el('div', { style:'background:#23262b;padding:14px;border-radius:10px;border:1px solid #2f3136' });
  addBox.append(el('h4', { text:'Add Ingredient/Output', style:'margin:0 0 8px 0;color:#e6e6e6' }));
  const row = el('div', { style:'display:flex;gap:10px;align-items:end;flex-wrap:wrap' });
  const itemSel = el('select', { style:'flex:2;min-width:200px;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
  itemSel.append(el('option', { value:'' }, '— Select Item —'));
  _items.forEach(i => itemSel.append(el('option', { value:i.id }, i.name)));
  const qty = el('input', { type:'number', placeholder:'Qty', style:'flex:1;min-width:120px;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
  const roleSel2 = el('select', { style:'flex:1;min-width:120px;padding:10px 12px;background:#2a2c30;border:1px solid #3a3d43;border-radius:10px;color:#e6e6e6' });
  roleSel2.append(el('option', { value:'input' }, 'Input'));
  roleSel2.append(el('option', { value:'output' }, 'Output'));
  const addBtn = el('button', { class:'btn primary', text:'Add', style:'border-radius:10px;padding:10px 14px;' });
  addBtn.onclick = async () => {
    const item_id = itemSel.value ? Number(itemSel.value) : null;
    const qtyv = qty.value ? parseFloat(qty.value) : NaN;
    const role = roleSel2.value;
    if (!item_id || !(qtyv > 0)) return;
    try {
      await RecipesAPI.addItem(_active.id, { item_id, role, qty_stored: qtyv });
      _active = await RecipesAPI.get(_active.id);
      renderEditor(right, left);
    } catch (e) {
      alert('Failed to add line');
    }
  };
  row.append(itemSel, qty, roleSel2, addBtn);
  addBox.append(row);

  right.append(nameRow, outRow, table, addBox);
}
