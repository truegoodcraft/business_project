// TGC BUS Core (Business Utility System Core)
// Copyright (C) 2025 True Good Craft
//
// This file is part of TGC BUS Core.
//
// TGC BUS Core is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// TGC BUS Core is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

(function(){
  if (!window.API || !window.Dom || !window.Modals) {
    console.error('Card missing API helpers: tasks');
    return;
  }

  const { el } = window.Dom;
  const API = window.API;

  function asArray(value){
    return Array.isArray(value) ? value : [];
  }

  function buildForm(state, refresh){
    const titleInput = el('input', { name: 'title', required: true, placeholder: 'Task title' });
    const statusSelect = el('select', { name: 'status' }, [
      el('option', { value: 'pending' }, 'Pending'),
      el('option', { value: 'in_progress' }, 'In Progress'),
      el('option', { value: 'done' }, 'Done'),
    ]);
    const dueInput = el('input', { name: 'due', type: 'date' });
    const itemSelect = el('select', { name: 'item_id' });
    const notesInput = el('textarea', { name: 'notes', placeholder: 'Notes' });
    const submit = el('button', { type: 'submit' }, 'Add Task');
    const cancel = el('button', { type: 'button', class: 'secondary' }, 'Cancel');

    function updateItems(){
      const items = asArray(state.items);
      itemSelect.innerHTML = '';
      itemSelect.appendChild(el('option', { value: '' }, '— No Item —'));
      items.forEach(item => {
        itemSelect.appendChild(el('option', { value: String(item.id) }, `${item.name || 'Item'} (#${item.id})`));
      });
    }

    function reset(){
      state.editingId = null;
      titleInput.value = '';
      statusSelect.value = 'pending';
      dueInput.value = '';
      itemSelect.value = '';
      notesInput.value = '';
      submit.textContent = 'Add Task';
      cancel.style.display = 'none';
    }

    function fill(task){
      state.editingId = task.id;
      titleInput.value = task.title || '';
      statusSelect.value = task.status || 'pending';
      dueInput.value = task.due || '';
      itemSelect.value = task.item_id ? String(task.item_id) : '';
      notesInput.value = task.notes || '';
      submit.textContent = 'Update Task';
      cancel.style.display = 'inline-flex';
    }

    const form = el('form', {}, [
      el('div', { class: 'section-title' }, state.editingId ? 'Edit Task' : 'Create Task'),
      el('div', { class: 'form-grid' }, [
        el('label', {}, ['Title', titleInput]),
        el('label', {}, ['Status', statusSelect]),
        el('label', {}, ['Due', dueInput]),
        el('label', {}, ['Item', itemSelect]),
      ]),
      el('label', {}, ['Notes', notesInput]),
      el('div', { class: 'actions' }, [submit, cancel]),
    ]);

    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!API) return;
      const payload = {
        title: titleInput.value.trim(),
        status: statusSelect.value,
        due: dueInput.value || null,
        item_id: itemSelect.value ? Number(itemSelect.value) : null,
        notes: notesInput.value.trim() || null,
      };
      if (!payload.title) return;
      try {
        if (state.editingId) {
          await API.put(`/tasks/${state.editingId}`, payload);
        } else {
          await API.post('/tasks', payload);
        }
        reset();
        await refresh();
      } catch (error) {
        state.status.textContent = 'Save failed: ' + (error && error.message ? error.message : String(error));
      }
    });

    cancel.addEventListener('click', () => reset());

    state.updateForm = fill;
    state.resetForm = reset;
    state.syncItems = updateItems;
    updateItems();
    reset();
    cancel.style.display = 'none';
    return form;
  }

  function buildTable(state, refresh){
    const table = el('table');
    const head = el('thead', {}, el('tr', {}, [
      el('th', {}, 'Title'),
      el('th', {}, 'Status'),
      el('th', {}, 'Due'),
      el('th', {}, 'Item'),
      el('th', {}, 'Actions'),
    ]));
    const body = el('tbody');
    table.appendChild(head);
    table.appendChild(body);

    function renderRows(){
      body.innerHTML = '';
      const items = new Map(asArray(state.items).map(item => [item.id, item]));
      asArray(state.tasks).forEach(task => {
        const related = items.get(task.item_id);
        const row = el('tr', {}, [
          el('td', {}, task.title || 'Untitled'),
          el('td', {}, task.status || 'pending'),
          el('td', {}, task.due || '—'),
          el('td', {}, related ? `${related.name || 'Item'} (#${related.id})` : '—'),
          el('td', {}, createActions(task)),
        ]);
        body.appendChild(row);
      });
    }

    function createActions(task){
      const edit = el('button', { type: 'button', class: 'secondary' }, 'Edit');
      const remove = el('button', { type: 'button', class: 'danger' }, 'Delete');
      edit.addEventListener('click', () => {
        if (state.updateForm) state.updateForm(task);
      });
      remove.addEventListener('click', () => {
        if (!window.Modals) return;
        window.Modals.confirm('Delete Task', `Delete ${task.title || 'this task'}?`, async () => {
          try {
            await API.delete(`/tasks/${task.id}`);
            await refresh();
          } catch (error) {
            state.status.textContent = 'Delete failed: ' + (error && error.message ? error.message : String(error));
          }
        });
      });
      return el('div', { class: 'actions' }, [edit, remove]);
    }

    state.renderRows = renderRows;
    return el('div', { class: 'table-wrapper' }, table);
  }

  async function render(container){
    if (!el || !API) {
      container.textContent = 'UI helpers unavailable.';
      return;
    }

    const state = { tasks: [], items: [], editingId: null, status: el('div', { class: 'status-box' }) };
    const title = el('h2', {}, 'Tasks');
    const table = buildTable(state, refresh);
    const form = buildForm(state, refresh);

    container.replaceChildren(title, table, form, state.status);

    async function refresh(){
      try {
        const [tasks, items] = await Promise.all([
          API.get('/tasks'),
          API.get('/items'),
        ]);
        state.tasks = asArray(tasks);
        state.items = asArray(items);
        if (state.syncItems) state.syncItems();
        if (state.renderRows) state.renderRows();
        state.status.textContent = `Loaded ${state.tasks.length} task(s).`;
      } catch (error) {
        state.status.textContent = 'Load failed: ' + (error && error.message ? error.message : String(error));
      }
    }

    await refresh();
  }

  function init() {}

  if (window.Cards && typeof window.Cards.register === 'function') {
    window.Cards.register('tasks', { init, render });
  }
})();
