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

const LS_KEY = 'tasks.v1';

const load = () => {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const save = (arr) => {
  localStorage.setItem(LS_KEY, JSON.stringify(arr || []));
};

let tasksBound = false;
let tableBodyRef = null;
let titleInputRef = null;
let statusInputRef = null;

function buildRow(task, idx) {
  const tr = document.createElement('tr');

  const titleCell = document.createElement('td');
  const titleField = document.createElement('input');
  titleField.type = 'text';
  titleField.value = task.title || '';
  titleField.dataset.idx = String(idx);
  titleField.dataset.field = 'title';
  titleCell.appendChild(titleField);

  const statusCell = document.createElement('td');
  const statusField = document.createElement('select');
  statusField.dataset.idx = String(idx);
  statusField.dataset.field = 'status';
  ['todo', 'doing', 'done'].forEach((value) => {
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = value;
    if (task.status === value) opt.selected = true;
    statusField.appendChild(opt);
  });
  statusCell.appendChild(statusField);

  const actionCell = document.createElement('td');
  const delBtn = document.createElement('button');
  delBtn.type = 'button';
  delBtn.dataset.action = 'task-del';
  delBtn.dataset.idx = String(idx);
  delBtn.textContent = 'Delete';
  actionCell.appendChild(delBtn);

  tr.append(titleCell, statusCell, actionCell);
  return tr;
}

function refreshTable() {
  if (!tableBodyRef) return;
  const list = load();
  tableBodyRef.innerHTML = '';
  list.forEach((task, idx) => {
    tableBodyRef.appendChild(buildRow(task, idx));
  });
}

function addTask() {
  const title = (titleInputRef?.value || '').trim();
  const status = statusInputRef?.value || 'todo';
  if (!title) return;
  const list = load();
  list.push({ title, status });
  save(list);
  if (titleInputRef) titleInputRef.value = '';
  refreshTable();
}

function updateTask(idx, field, value) {
  const list = load();
  const i = Number(idx);
  if (!Number.isFinite(i) || !list[i]) return;
  list[i][field] = value;
  save(list);
}

function deleteTask(idx) {
  const list = load();
  const i = Number(idx);
  if (!Number.isFinite(i) || !list[i]) return;
  list.splice(i, 1);
  save(list);
  refreshTable();
}

export function mountOrganizer(container) {
  const scope = container instanceof HTMLElement ? container : document;

  if (container instanceof HTMLElement && !container.querySelector('[data-role="tasks-table"]')) {
    container.innerHTML = `
      <div class="card" data-role="tasks-card">
        <div class="toolbar" style="display:flex;gap:8px;align-items:center;margin-bottom:12px;">
          <input type="text" data-role="task-title-input" placeholder="New task title" style="flex:1;min-width:160px;">
          <select data-role="task-status-input">
            <option value="todo">todo</option>
            <option value="doing">doing</option>
            <option value="done">done</option>
          </select>
          <button type="button" data-action="task-add">Add Task</button>
        </div>
        <table class="table" data-role="tasks-table">
          <thead><tr><th>Title</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    `;
  }

  tableBodyRef = scope.querySelector('[data-role="tasks-table"] tbody');
  titleInputRef = scope.querySelector('[data-role="task-title-input"]');
  statusInputRef = scope.querySelector('[data-role="task-status-input"]');
  if (!tableBodyRef) return;

  refreshTable();

  const addBtn = scope.querySelector('[data-action="task-add"]');
  if (addBtn && !addBtn.dataset.taskAddBound) {
    addBtn.addEventListener('click', addTask);
    addBtn.dataset.taskAddBound = '1';
  }

  if (!tasksBound) {
    document.addEventListener('input', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const { idx, field } = target.dataset || {};
      if (idx == null || field == null) return;
      updateTask(idx, field, target.value);
    });

    document.addEventListener('change', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const { idx, field } = target.dataset || {};
      if (idx == null || field == null) return;
      updateTask(idx, field, target.value);
    });

    document.addEventListener('click', (event) => {
      const el = event.target instanceof HTMLElement ? event.target : null;
      if (!el) return;
      const delBtn = el.closest('[data-action="task-del"]');
      if (delBtn) {
        const { idx } = delBtn.dataset || {};
        if (idx != null) deleteTask(idx);
        return;
      }
    });

    tasksBound = true;
  }
}

export default mountOrganizer;
