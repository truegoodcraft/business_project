// SPDX-License-Identifier: AGPL-3.0-or-later
// Manufacturing Runs & History Card

import { apiGet, ensureToken } from '../api.js';
import { RecipesAPI } from '../api/recipes.js';

// DOM Helpers matching your other cards
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

let _state = {
  recipes: [],
  selectedRecipe: null,
  multiplier: 1,
  movements: []
};

export async function mountManufacturing() {
  await ensureToken();
  _state = { recipes: [], selectedRecipe: null, multiplier: 1, movements: [] };
  const container = document.querySelector('[data-tab-panel="manufacturing"]');
  if (!container) return;

  container.innerHTML = '';
  container.style.display = '';
  
  // 1. Layout Structure
  const grid = el('div', { class: 'grid-2-1', style: 'display:grid;grid-template-columns:2fr 1fr;gap:20px;' });
  
  const leftPanel = el('div', { class: 'panel-left' });
  const rightPanel = el('div', { class: 'panel-right' });
  
  grid.append(leftPanel, rightPanel);
  container.append(grid);

  // 2. Init Components
  await renderNewRunForm(leftPanel);
  await renderHistoryList(rightPanel);
}

export function unmountManufacturing() {
  _state = { recipes: [], selectedRecipe: null, multiplier: 1, movements: [] };
  const container = document.querySelector('[data-tab-panel="manufacturing"]');
  if (container) container.innerHTML = '';
}

// --- Left Panel: New Run Workflow ---

async function renderNewRunForm(parent) {
  // Fetch recipes
  try {
    const list = await RecipesAPI.list();
    _state.recipes = (list || []).filter(r => !r.archived);
  } catch (err) {
    parent.append(el('div', { class: 'error' }, 'Failed to load recipes.'));
    return;
  }

  const card = el('div', { class: 'card' });
  const headerRow = el('div', { style: 'display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;' }, [
    el('h2', { text: 'New Production Run' }),
    el('a', { href: '#/recipes', class: 'btn small', style: 'text-decoration:none;border-radius:10px;padding:8px 12px;' }, 'Manage Recipes')
  ]);
  
  // Controls
  const formGrid = el('div', { class: 'form-grid', style: 'display:grid;grid-template-columns:1fr 110px;gap:12px;align-items:end;margin-bottom:20px;' });
  
  const recipeSelect = el('select', { id: 'run-recipe', style: 'width:100%;background:#2a2c30;color:#e6e6e6;border:1px solid #3a3d43;border-radius:10px;padding:10px;' });
  recipeSelect.append(el('option', { value: '' }, '— Select Recipe —'));
  _state.recipes.forEach(r => {
    recipeSelect.append(el('option', { value: r.id }, r.name));
  });

  const multInput = el('input', { type: 'number', value: '1', min: '1', style: 'width:100%;background:#2a2c30;color:#e6e6e6;border:1px solid #3a3d43;border-radius:10px;padding:10px;' });
  
  formGrid.append(
    el('label', {}, [el('div', { text: 'Recipe', style:'margin-bottom:4px;font-size:12px;color:#aaa' }), recipeSelect]),
    el('label', {}, [el('div', { text: 'Multiplier', style:'margin-bottom:4px;font-size:12px;color:#aaa' }), multInput])
  );

  // Projection Table
  const tableContainer = el('div', { class: 'projection-table', style: 'background:#1e1f22;border-radius:10px;overflow:hidden;margin-bottom:20px;border:1px solid #2f3136;' });
  const table = el('table', { style: 'width:100%;font-size:13px;border-collapse:collapse;' });
  const thead = el('thead', {}, [
    el('tr', { style:'border-bottom:1px solid #333;text-align:left' }, [
      el('th', { style:'padding:8px', text: 'Item' }),
      el('th', { style:'padding:8px', text: 'Role' }),
      el('th', { style:'padding:8px;text-align:right', text: 'Stock' }),
      el('th', { style:'padding:8px;text-align:right', text: 'Change' }),
      el('th', { style:'padding:8px;text-align:right', text: 'Post-Run' })
    ])
  ]);
  const tbody = el('tbody');
  table.append(thead, tbody);
  tableContainer.append(table);
  
  const emptyMsg = el('div', { style:'padding:20px;text-align:center;color:#666', text: 'Select a recipe to view projection.' });
  tableContainer.append(emptyMsg);

  // Actions
  const btnRow = el('div', { style: 'display:flex;justify-content:flex-end;gap:10px' });
  const statusMsg = el('span', { style: 'margin-right:auto;font-size:13px;align-self:center;' });
  const runBtn = el('button', { class: 'btn primary', disabled: 'true', style: 'border-radius:10px;padding:10px 14px;' }, 'Run Production');
  
  btnRow.append(statusMsg, runBtn);
  card.append(headerRow, formGrid, tableContainer, btnRow);
  parent.append(card);

  // Logic
  const updateProjection = async () => {
    const rid = recipeSelect.value;
    const mult = parseInt(multInput.value, 10) || 0;
    
    if (!rid || mult < 1) {
      tbody.innerHTML = '';
      table.style.display = 'none';
      emptyMsg.style.display = 'block';
      runBtn.disabled = true;
      _state.selectedRecipe = null;
      return;
    }

    try {
      // Fetch full details (items + current stock)
      const fullRecipe = await RecipesAPI.get(rid);
      if (fullRecipe?.archived) {
        statusMsg.textContent = 'This recipe is archived and cannot be run.';
        statusMsg.style.color = '#ff4444';
        tbody.innerHTML = '';
        table.style.display = 'none';
        emptyMsg.style.display = 'block';
        runBtn.disabled = true;
        _state.selectedRecipe = null;
        return;
      }
      _state.selectedRecipe = fullRecipe;
      _state.multiplier = mult;

      tbody.innerHTML = '';
      table.style.display = 'table';
      emptyMsg.style.display = 'none';
      runBtn.disabled = false;

      const baseOutput = Number(fullRecipe.output_qty || 1);
      const multiplier = Number(mult) || 0;
      const outputQty = baseOutput * multiplier;
      const scale = outputQty / (baseOutput || 1);

      fullRecipe.items.forEach(ri => {
        const current = (ri.item?.qty_stored ?? 0);
        const change = -(Number(ri.qty_required || 0) * scale);
        const future = current + change;
        const uom = ri.item?.uom || '';

        const row = el('tr', { style: 'border-bottom:1px solid #2a2a2a' });

        let stockColor = '#eee';
        if (future < 0) stockColor = '#ff4444';

        row.append(
          el('td', { style:'padding:8px', text: ri.item?.name || `Item #${ri.item_id}` }),
          el('td', { style:'padding:8px;color:#aaa', text: (ri.optional ?? ri.is_optional) ? 'Optional' : 'Input' }),
          el('td', { style:'padding:8px;text-align:right', text: `${current} ${uom}` }),
          el('td', { style:'padding:8px;text-align:right', text: `${change.toFixed(2)}` }),
          el('td', { style:`padding:8px;text-align:right;color:${stockColor}`, text: `${future.toFixed(2)} ${uom}` })
        );
        tbody.append(row);
      });

      if (fullRecipe.output_item_id) {
        const outItem = fullRecipe.output_item;
        const outCurrent = outItem?.qty_stored || 0;
        const outChange = outputQty;
        const outFuture = outCurrent + outChange;
        const uom = outItem?.uom || '';
        const row = el('tr', { style: 'border-bottom:1px solid #2a2a2a' });
        row.append(
          el('td', { style:'padding:8px', text: outItem?.name || `Item #${fullRecipe.output_item_id}` }),
          el('td', { style:'padding:8px;color:#4caf50', text: 'Output' }),
          el('td', { style:'padding:8px;text-align:right', text: `${outCurrent} ${uom}` }),
          el('td', { style:'padding:8px;text-align:right', text: `+${outChange}` }),
          el('td', { style:'padding:8px;text-align:right;color:#4caf50', text: `${outFuture} ${uom}` })
        );
        tbody.append(row);
      }
    } catch (e) {
      console.error(e);
      statusMsg.textContent = 'Error calculating projection.';
      statusMsg.style.color = 'red';
    }
  };

  recipeSelect.addEventListener('change', updateProjection);
  multInput.addEventListener('input', updateProjection);

  runBtn.addEventListener('click', async () => {
    if (!_state.selectedRecipe) return;
    if (_state.selectedRecipe.archived) {
      statusMsg.textContent = 'This recipe is archived and cannot be run.';
      statusMsg.style.color = '#ff4444';
      return;
    }

    runBtn.disabled = true;
    runBtn.textContent = 'Processing...';
    statusMsg.textContent = '';

    try {
      await RecipesAPI.run({
        recipe_id: _state.selectedRecipe.id,
        output_qty: (_state.selectedRecipe.output_qty || 1) * (_state.multiplier || 1)
      });
      
      statusMsg.textContent = 'Run Complete!';
      statusMsg.style.color = '#4caf50';
      multInput.value = 1;
      
      // Refresh views
      await updateProjection();
      await refreshHistory(document.querySelector('.history-list'));
      runBtn.textContent = 'Run Production';
      runBtn.disabled = false;
      
    } catch (e) {
      if (e.status === 403) {
        statusMsg.textContent = 'Run blocked: unauthorized.';
      } else if (e.status === 400 && e.data && e.data.detail && e.data.detail.shortages) {
        const s = e.data.detail.shortages.map(x => `#${x.item_id}: need ${x.required}, have ${x.on_hand}, missing ${x.missing}`).join(' | ');
        statusMsg.textContent = `Insufficient stock → ${s}`;
      } else {
        statusMsg.textContent = e?.detail || e?.data?.detail || e?.data?.detail?.message || e?.message || 'Run failed.';
      }
      statusMsg.style.color = '#ff4444';
      runBtn.disabled = false;
      runBtn.textContent = 'Run Production';
    }
  });
}

// --- Right Panel: History (Ledger) ---

async function renderHistoryList(parent) {
  const card = el('div', { class: 'card' });
  card.append(el('h2', { text: 'Recent Activity' }));
  
  const list = el('div', { class: 'history-list', style: 'display:flex;flex-direction:column;gap:8px;' });
  card.append(list);
  parent.append(card);

  await refreshHistory(list);
}

async function refreshHistory(container) {
  if (!container) return;
  container.innerHTML = '<div style="color:#666;font-size:12px">Loading...</div>';

  try {
    const movements = await apiGet('/app/ledger/movements?limit=15');
    
    container.innerHTML = '';
    if (!movements || movements.length === 0) {
      container.append(el('div', { style:'color:#666;font-size:13px', text: 'No recent movements.' }));
      return;
    }

    movements.forEach(mov => {
      const isPos = mov.qty_change > 0;
      const row = el('div', { style: 'background:#2a2a2a;padding:8px;border-radius:8px;font-size:12px;display:flex;justify-content:space-between;' });
      
      const left = el('div');
      left.append(el('div', { style: 'font-weight:600;color:#eee', text: `Item #${mov.item_id}` }));
      left.append(el('div', { style: 'color:#888;font-size:11px', text: new Date(mov.created_at).toLocaleString() }));

      const right = el('div', { style: 'text-align:right' });
      right.append(el('div', { 
        text: `${isPos ? '+' : ''}${mov.qty_change}`, 
        style: `font-weight:bold;color:${isPos ? '#4caf50' : '#eee'}` 
      }));
      right.append(el('div', { style:'color:#666;font-size:10px', text: mov.source_kind || '—' }));

      row.append(left, right);
      container.append(row);
    });

  } catch (e) {
    container.innerHTML = '<div style="color:red;font-size:12px">Failed to load history.</div>';
  }
}
