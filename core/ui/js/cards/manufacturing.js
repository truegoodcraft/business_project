// SPDX-License-Identifier: AGPL-3.0-or-later
// Visual ingredient builder for manufacturing runs.

import { apiGet, apiPost, ensureToken } from '../api.js';
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

function renderSmartBadge(inputEl, badgeEl) {
  const parsed = parseSmartInput(inputEl.value);
  if (!parsed) {
    badgeEl.textContent = 'Parsed: —';
    badgeEl.classList.remove('ok');
    return null;
  }
  badgeEl.textContent = `Parsed: ${parsed.qty} ${parsed.unit || ''}`.trim();
  badgeEl.classList.add('ok');
  return parsed;
}

function renderIngredientList(state) {
  state.listEl.innerHTML = '';
  if (!state.ingredients.length) {
    state.listEl.append(el('div', { class: 'badge-note' }, 'No ingredients added.'));
    return;
  }
  state.ingredients.forEach((ing, idx) => {
    const entry = el('div', { class: 'card row-compact' }, [
      el('div', { class: 'section-title' }, ing.name),
      el('div', { class: 'badge-note ok' }, `${ing.qty} ${ing.unit || ''}`.trim()),
      el('button', { type: 'button', 'data-index': idx, class: 'danger' }, 'Remove'),
    ]);
    state.listEl.append(entry);
  });
}

export async function mountManufacturing() {
  await ensureToken();
  const container = document.querySelector('[data-role="manufacturing-panel"]');
  if (!container) return;

  const state = { items: [], ingredients: [], listEl: null, statusEl: null };

  const itemSelect = el('select', { id: 'ingredient-item' });
  const qtyInput = el('input', { id: 'ingredient-qty', placeholder: "e.g. 10 kg or 5'" });
  const badge = el('span', { class: 'badge-note' }, 'Parsed: —');
  const addBtn = el('button', { type: 'button' }, 'Add');
  const saveBtn = el('button', { type: 'button' }, 'Save Recipe');
  const listArea = el('div', { class: 'stack' });
  const statusBox = el('div', { class: 'status-box' }, 'Build a recipe to save it.');

  addBtn.textContent = 'Add';
  const builder = el('div', { class: 'card' }, [
    el('h2', { text: 'Manufacturing' }),
    el('div', { class: 'form-grid' }, [
      el('label', {}, ['Item', itemSelect]),
      el('label', {}, ['Quantity', qtyInput, badge]),
      addBtn,
    ]),
    el('div', { class: 'actions' }, [saveBtn]),
    el('div', { class: 'section-title' }, 'Ingredients'),
    listArea,
    statusBox,
  ]);

  container.innerHTML = '';
  container.append(builder);
  state.listEl = listArea;
  state.statusEl = statusBox;

  qtyInput.addEventListener('input', () => renderSmartBadge(qtyInput, badge));

  addBtn.addEventListener('click', () => {
    const parsed = renderSmartBadge(qtyInput, badge);
    const selectedId = Number(itemSelect.value);
    const item = state.items.find((it) => it.id === selectedId);
    if (!parsed || !item) {
      statusBox.textContent = 'Choose an item and enter a valid quantity.';
      return;
    }
    state.ingredients.push({ id: item.id, name: item.name, qty: parsed.qty, unit: parsed.unit });
    renderIngredientList(state);
    qtyInput.value = '';
    renderSmartBadge(qtyInput, badge);
  });

  listArea.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const idx = Number(btn.getAttribute('data-index'));
    if (Number.isInteger(idx)) {
      state.ingredients.splice(idx, 1);
      renderIngredientList(state);
    }
  });

  saveBtn.addEventListener('click', async () => {
    if (!state.ingredients.length) {
      statusBox.textContent = 'Add at least one ingredient to save.';
      return;
    }
    const outputs = Object.fromEntries(state.ingredients.map((ing) => [ing.id, ing.qty]));
    const payload = { outputs, inputs: {}, note: JSON.stringify(state.ingredients) };
    await apiPost('/app/manufacturing/run', payload);
    statusBox.textContent = `Saved recipe: ${JSON.stringify(state.ingredients)}`;
    state.ingredients = [];
    renderIngredientList(state);
  });

  const items = await apiGet('/app/items');
  state.items = Array.isArray(items) ? items : [];
  itemSelect.innerHTML = '';
  state.items.forEach((it) => itemSelect.append(el('option', { value: it.id, text: `${it.name} (#${it.id})` })));
  renderSmartBadge(qtyInput, badge);
  renderIngredientList(state);
}

export function unmountManufacturing() {}
