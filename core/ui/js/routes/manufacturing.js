// core/ui/js/routes/manufacturing.js
import { registerRoute, navigate } from '../router.js';
import { RecipesAPI } from '../api/recipes.js';
import { toDisplay } from '../utils/measurement.js';

registerRoute('/manufacturing', mount);

let state = { recipes: [], selected: null, multiplier: 1 };

function el(tag, attrs={}, ...children) {
  const n = document.createElement(tag);
  Object.entries(attrs).forEach(([k,v]) => {
    if (k === 'class') n.className = v; else if (k.startsWith('on')) n.addEventListener(k.substring(2).toLowerCase(), v); else n.setAttribute(k,v);
  });
  children.flat().forEach(c => n.append(c && c.nodeType ? c : document.createTextNode(String(c))));
  return n;
}

async function loadRecipes() {
  state.recipes = await RecipesAPI.list();
}

function zoneA(onSelect) {
  const list = el('div', { class: 'zoneA' }, el('h3', {}, 'Recipe Book'));
  const ul = el('ul');
  state.recipes.forEach(r => {
    const li = el('li', {}, el('button', { onClick: () => onSelect(r) }, r.name));
    ul.append(li);
  });
  list.append(ul);
  return list;
}

function zoneB() {
  const z = el('div', { class: 'zoneB' }, el('h3', {}, 'Job Deck'));
  if (!state.selected) {
    z.append(el('p', {}, 'Select a recipe to view inputs and outputs.'));
    return z;
  }
  const r = state.selected;
  const inputs = r.items.filter(i => i.role === 'input');
  const outputs = r.items.filter(i => i.role === 'output');
  const table = (title, items) => {
    const t = el('table');
    t.append(el('caption', {}, title));
    t.append(el('thead', {}, el('tr', {}, el('th', {}, 'Item'), el('th', {}, 'UOM'), el('th', {}, 'Qty (per recipe)'), el('th', {}, 'On Hand'), el('th', {}, 'Required'))));
    const tbody = el('tbody');
    items.forEach(it => {
      const onHand = it.item.qty_stored; // embedded by backend in GET /recipes/:id or list
      const req = it.qty_stored * state.multiplier;
      tbody.append(el('tr', {},
        el('td', {}, it.item.name),
        el('td', {}, it.item.uom),
        el('td', {}, String(toDisplay(it.qty_stored, it.item.uom))),
        el('td', {}, String(toDisplay(onHand, it.item.uom))),
        el('td', {}, String(toDisplay(req, it.item.uom))),
      ));
    });
    t.append(tbody);
    return t;
  };
  z.append(table('Inputs', inputs));
  z.append(table('Outputs', outputs));

  // Max craftable
  const perInputMax = inputs.map(it => Math.floor((it.item.qty_stored) / (it.qty_stored || 1)));
  const maxCraftable = perInputMax.length ? Math.min(...perInputMax) : 0;
  z.append(el('p', {}, `Max Craftable (by inputs): ${maxCraftable}`));
  return z;
}

function zoneC(onRun) {
  const z = el('div', { class: 'zoneC' }, el('h3', {}, 'Execution'));
  const m = el('input', { type: 'number', min: '1', value: String(state.multiplier), onInput: e => state.multiplier = parseInt(e.target.value || '1', 10) });
  const btn = el('button', { onClick: onRun }, 'Run Recipe');
  z.append(el('label', {}, 'Multiplier: ', m), btn);
  return z;
}

async function mount(root) {
  root.append(el('style', {}, `
    .zoneA,.zoneB,.zoneC{padding:8px;margin:4px;border:1px solid #2f3136;border-radius:8px;background:#2a2c30;color:#e6e6e6}
    .layout{display:grid;grid-template-columns:260px 1fr 320px;gap:8px}
    table{width:100%;border-collapse:collapse}th,td{border:1px solid #3a3d43;padding:4px;text-align:left}
    caption{font-weight:bold;margin-bottom:4px;color:#e6e6e6}
    button{background:#3a3d43;border:1px solid #4a4d55;color:#e6e6e6;border-radius:10px;padding:6px 10px}
    button:hover{background:#23262b}
    input{background:#1e1f22;color:#e6e6e6;border:1px solid #3a3d43;padding:6px 8px;border-radius:10px}
    ul{list-style:none;padding-left:0}
    ul li{margin-bottom:6px}
  `));

  await loadRecipes();
  const layout = el('div', { class: 'layout' });
  const A = zoneA(async (r) => {
    // fetch full recipe with items & embedded item records
    state.selected = await RecipesAPI.get(r.id);
    navigate('/manufacturing'); // re-render
  });
  const B = zoneB();
  const C = zoneC(async () => {
    if (!state.selected) return alert('Select a recipe first');
    await RecipesAPI.run({ recipe_id: state.selected.id, multiplier: state.multiplier });
    // Refresh selected recipe & list to reflect new inventory
    await loadRecipes();
    state.selected = await RecipesAPI.get(state.selected.id);
    navigate('/manufacturing');
  });
  layout.append(A,B,C);
  root.append(layout);
}
