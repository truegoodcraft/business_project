// SPDX-License-Identifier: AGPL-3.0-or-later
import { apiDelete, apiGet, apiPatch, apiPost, ensureToken } from '../api.js';

const JOB_STATUSES = ['draft', 'active', 'blocked', 'ready', 'done', 'cancelled'];
const LINE_TYPES = ['product', 'service', 'fee', 'note'];
const LINE_STATUSES = ['pending', 'produced', 'delivered', 'cancelled'];

let state = newState();

function newState() {
  return {
    jobs: [],
    selectedId: null,
    selectedJob: null,
    contacts: [],
    items: [],
    recipes: [],
    search: '',
    status: '',
    lineEditId: null,
  };
}

function host() {
  return document.querySelector('[data-role="jobs-root"]');
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else node.setAttribute(key, value);
  });
  (Array.isArray(children) ? children : [children]).forEach((child) => {
    if (child === null || child === undefined) return;
    node.append(child);
  });
  return node;
}

function safeError(error, fallback = 'Request failed.') {
  const detail = error?.payload?.detail ?? error?.data?.detail ?? error?.detail;
  const code = detail?.error || error?.payload?.error || error?.data?.error || error?.error;
  if (error?.status === 401) return 'Sign in again to view Jobs.';
  if (error?.status === 403) {
    if (code === 'writes_disabled') return 'Writes are disabled. Turn writes back on to save job changes.';
    return 'Your account does not have permission for that Jobs action.';
  }
  if (typeof detail === 'string') return detail.replaceAll('_', ' ');
  if (typeof code === 'string') return code.replaceAll('_', ' ');
  if (typeof error?.message === 'string' && error.message && !error.message.includes('[object Object]')) {
    return error.message;
  }
  return fallback;
}

function toast(message, tone = 'ok') {
  const note = document.createElement('div');
  note.textContent = message;
  note.className = `jobs-toast jobs-toast--${tone === 'error' ? 'error' : 'ok'}`;
  document.body.appendChild(note);
  setTimeout(() => {
    note.classList.add('jobs-toast--hide');
    setTimeout(() => note.remove(), 280);
  }, 2200);
}

function moneyFromCents(cents) {
  const value = Number(cents || 0) / 100;
  return value.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
}

function centsFromMoney(value) {
  const raw = String(value ?? '').trim();
  if (!raw) return null;
  const numeric = Number(raw);
  if (!Number.isFinite(numeric)) return null;
  return Math.round(numeric * 100);
}

function formatDate(value) {
  if (!value) return 'No due date';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'No due date';
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatDateTime(value) {
  if (!value) return 'Unknown time';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown time';
  return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function dueTone(job) {
  if (!job?.due_date || ['done', 'cancelled'].includes(job.status)) return 'neutral';
  const due = new Date(job.due_date);
  if (Number.isNaN(due.getTime())) return 'neutral';
  const now = new Date();
  if (due < now) return 'danger';
  const soon = new Date(now);
  soon.setDate(now.getDate() + 7);
  return due <= soon ? 'warn' : 'neutral';
}

function contactName(id) {
  if (id === null || id === undefined || id === '') return 'No contact';
  const found = state.contacts.find((entry) => String(entry.id) === String(id));
  return found?.name || `Contact #${id}`;
}

function itemName(id) {
  if (id === null || id === undefined || id === '') return '';
  const found = state.items.find((entry) => String(entry.id) === String(id));
  return found?.name || `Item #${id}`;
}

function recipeName(id) {
  if (id === null || id === undefined || id === '') return '';
  const found = state.recipes.find((entry) => String(entry.id) === String(id));
  return found?.name || `Recipe #${id}`;
}

function parseOptionalInt(value) {
  const raw = String(value ?? '').trim();
  if (!raw) return null;
  const numeric = Number(raw);
  return Number.isInteger(numeric) && numeric > 0 ? numeric : null;
}

function selectOptions(values, selected, labeler = (value) => value) {
  return values.map((value) => {
    const opt = el('option', { value: String(value), text: labeler(value) });
    if (String(value) === String(selected ?? '')) opt.selected = true;
    return opt;
  });
}

function referenceOptions(entries, selected, placeholder) {
  const options = [el('option', { value: '', text: placeholder })];
  entries.forEach((entry) => {
    const opt = el('option', { value: String(entry.id), text: entry.name || `#${entry.id}` });
    if (String(entry.id) === String(selected ?? '')) opt.selected = true;
    options.push(opt);
  });
  return options;
}

async function loadReferenceData() {
  const [contacts, items, recipes] = await Promise.all([
    apiGet('/app/contacts').catch(() => []),
    apiGet('/app/items').catch(() => []),
    apiGet('/app/recipes').catch(() => []),
  ]);
  state.contacts = Array.isArray(contacts) ? contacts : [];
  state.items = Array.isArray(items) ? items : [];
  state.recipes = Array.isArray(recipes) ? recipes : [];
}

async function loadJobs({ keepSelection = true } = {}) {
  state.jobs = await apiGet('/app/jobs');
  if (!Array.isArray(state.jobs)) state.jobs = [];
  const selectedStillExists = state.jobs.some((job) => String(job.id) === String(state.selectedId));
  if (!keepSelection || !selectedStillExists) {
    state.selectedId = state.jobs[0]?.id ?? null;
  }
  if (state.selectedId) {
    await loadSelectedJob(state.selectedId, { rerender: false });
  } else {
    state.selectedJob = null;
  }
}

async function loadSelectedJob(jobId, { rerender = true } = {}) {
  state.selectedId = jobId;
  state.selectedJob = await apiGet(`/app/jobs/${jobId}`);
  if (rerender) render();
}

function filteredJobs() {
  const q = state.search.trim().toLowerCase();
  return state.jobs.filter((job) => {
    if (state.status && job.status !== state.status) return false;
    if (!q) return true;
    const haystack = [job.title, job.status, job.contact_display || contactName(job.contact_id)]
      .join(' ')
      .toLowerCase();
    return haystack.includes(q);
  });
}

function render() {
  const root = host();
  if (!root) return;
  root.className = 'jobs-shell';
  root.innerHTML = '';

  const header = el('section', { class: 'jobs-header card' }, [
    el('div', { class: 'jobs-heading' }, [
      el('h1', { text: 'Jobs' }),
      el('p', { text: 'Track work from request to ready/done without changing stock automatically.' }),
    ]),
    el('button', { class: 'btn primary jobs-new-btn', type: 'button', text: 'New Job', 'data-action': 'new-job' }),
  ]);

  const layout = el('div', { class: 'jobs-layout' }, [
    renderListPanel(),
    renderDetailPanel(),
  ]);

  root.append(header, layout);

  root.querySelector('[data-action="new-job"]')?.addEventListener('click', () => {
    state.selectedId = null;
    state.selectedJob = null;
    state.lineEditId = null;
    render();
  });
}

function renderListPanel() {
  const panel = el('section', { class: 'card jobs-list-panel' });
  const filters = el('div', { class: 'jobs-filters' });
  const search = el('input', {
    type: 'search',
    class: 'jobs-input jobs-search',
    placeholder: 'Search jobs or contacts...',
    value: state.search,
    'data-role': 'jobs-search',
  });
  const status = el('select', { class: 'jobs-input', 'data-role': 'jobs-status-filter' }, [
    el('option', { value: '', text: 'All statuses' }),
    ...selectOptions(JOB_STATUSES, state.status),
  ]);
  filters.append(search, status);

  const count = el('div', { class: 'jobs-list-count', text: `${filteredJobs().length} job${filteredJobs().length === 1 ? '' : 's'}` });
  const list = el('div', { class: 'jobs-list' });
  const rows = filteredJobs();
  if (!rows.length) {
    list.append(el('div', { class: 'jobs-empty' }, [
      el('strong', { text: 'No jobs yet.' }),
      el('p', { text: 'Create a draft job to capture work without affecting stock or finance.' }),
    ]));
  } else {
    rows.forEach((job) => list.append(renderJobRow(job)));
  }

  panel.append(filters, count, list);

  search.addEventListener('input', () => {
    state.search = search.value;
    render();
  });
  status.addEventListener('change', () => {
    state.status = status.value;
    render();
  });
  return panel;
}

function renderJobRow(job) {
  const row = el('button', { class: 'jobs-row', type: 'button', 'data-job-id': job.id });
  if (String(job.id) === String(state.selectedId)) row.classList.add('active');
  const due = dueTone(job);
  row.append(
    el('span', { class: 'jobs-row-title', text: job.title || `Job #${job.id}` }),
    el('span', { class: `jobs-badge jobs-badge--${job.status || 'draft'}`, text: job.status || 'draft' }),
    el('span', { class: `jobs-row-due jobs-row-due--${due}`, text: formatDate(job.due_date) }),
    el('span', { class: 'jobs-row-meta', text: job.contact_display || contactName(job.contact_id) }),
    el('span', { class: 'jobs-row-meta', text: `${job.line_count || 0} line${Number(job.line_count || 0) === 1 ? '' : 's'} | ${moneyFromCents(job.estimated_value_cents)}` }),
  );
  row.addEventListener('click', async () => {
    try {
      state.lineEditId = null;
      await loadSelectedJob(job.id);
    } catch (error) {
      toast(safeError(error, 'Failed to load job.'), 'error');
    }
  });
  return row;
}

function renderDetailPanel() {
  const panel = el('section', { class: 'card jobs-detail-panel' });
  const job = state.selectedJob;
  if (!job) {
    panel.append(renderJobForm(null));
    return panel;
  }

  panel.append(
    renderJobForm(job),
    renderStatusControls(job),
    renderLinesSection(job),
    renderEventsSection(job),
  );
  return panel;
}

function renderJobForm(job) {
  const isNew = !job;
  const form = el('form', { class: 'jobs-form', 'data-role': 'job-form' });
  const title = el('input', {
    class: 'jobs-input',
    name: 'title',
    required: 'true',
    value: job?.title || '',
    placeholder: 'Job title',
  });
  const status = el('select', { class: 'jobs-input', name: 'status' }, selectOptions(JOB_STATUSES, job?.status || 'draft'));
  const contact = el('select', { class: 'jobs-input', name: 'contact_id' }, referenceOptions(state.contacts, job?.contact_id, 'No contact'));
  const dueDate = el('input', {
    class: 'jobs-input',
    name: 'due_date',
    type: 'date',
    value: job?.due_date ? String(job.due_date).slice(0, 10) : '',
  });
  const priority = el('input', {
    class: 'jobs-input',
    name: 'priority',
    type: 'number',
    step: '1',
    value: String(job?.priority ?? 0),
  });
  const notes = el('textarea', {
    class: 'jobs-input jobs-textarea',
    name: 'notes',
    rows: '3',
    placeholder: 'Notes',
  });
  notes.value = job?.notes || '';

  const head = el('div', { class: 'jobs-detail-head' }, [
    el('div', {}, [
      el('h2', { text: isNew ? 'New Job' : 'Job Detail' }),
      el('p', { text: isNew ? 'Create a draft demand record. It will not change stock or finance.' : 'Edit job context. Status changes are handled separately below.' }),
    ]),
  ]);

  const grid = el('div', { class: 'jobs-form-grid' }, [
    field('Title', title),
    field('Contact', contact),
    field('Priority', priority),
    field('Due date', dueDate),
  ]);
  if (isNew) grid.append(field('Initial status', status));

  const error = el('div', { class: 'jobs-error hidden', 'data-role': 'job-form-error' });
  const actions = el('div', { class: 'jobs-action-row' }, [
    el('button', { class: 'btn primary', type: 'submit', text: isNew ? 'Create Job' : 'Save Job' }),
    ...(!isNew ? [el('span', { class: 'jobs-muted', text: `Created ${formatDateTime(job.created_at)}` })] : []),
  ]);

  form.append(head, grid, field('Notes', notes), error, actions);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    await saveJob(form, job);
  });
  return form;
}

function field(label, control) {
  return el('label', { class: 'jobs-field' }, [
    el('span', { class: 'jobs-label', text: label }),
    control,
  ]);
}

function showFormError(form, message) {
  const banner = form.querySelector('[data-role$="error"], [data-role="job-form-error"]');
  if (!banner) return;
  banner.textContent = message;
  banner.classList.remove('hidden');
}

async function saveJob(form, existingJob) {
  const data = new FormData(form);
  const title = String(data.get('title') || '').trim();
  if (!title) {
    showFormError(form, 'Title is required.');
    return;
  }
  const payload = {
    title,
    contact_id: parseOptionalInt(data.get('contact_id')),
    priority: Number(data.get('priority') || 0),
    due_date: data.get('due_date') ? `${data.get('due_date')}T00:00:00` : null,
    notes: String(data.get('notes') || '').trim() || null,
  };
  try {
    let saved;
    if (existingJob?.id) {
      saved = await apiPatch(`/app/jobs/${existingJob.id}`, payload);
      toast('Job saved.');
    } else {
      saved = await apiPost('/app/jobs', { ...payload, status: String(data.get('status') || 'draft') });
      toast('Job created.');
    }
    state.selectedId = saved.id;
    state.selectedJob = saved;
    await loadJobs({ keepSelection: true });
    render();
  } catch (error) {
    showFormError(form, safeError(error, 'Unable to save job.'));
  }
}

function renderStatusControls(job) {
  const wrap = el('section', { class: 'jobs-section jobs-status-section' });
  wrap.append(
    el('div', { class: 'jobs-section-head' }, [
      el('h3', { text: 'Job status' }),
      el('p', { text: 'Status only. No stock, payment, production, reservation, or delivery changes happen here.' }),
    ]),
  );
  const buttons = el('div', { class: 'jobs-status-buttons' });
  JOB_STATUSES.forEach((status) => {
    const btn = el('button', { class: 'jobs-status-btn', type: 'button', text: status, 'data-status': status });
    btn.classList.toggle('active', job.status === status);
    btn.addEventListener('click', async () => {
      if (job.status === status) return;
      try {
        state.selectedJob = await apiPost(`/app/jobs/${job.id}/status`, { status });
        await loadJobs({ keepSelection: true });
        render();
        toast('Job status updated.');
      } catch (error) {
        toast(safeError(error, 'Unable to update job status.'), 'error');
      }
    });
    buttons.append(btn);
  });
  wrap.append(buttons);
  return wrap;
}

function renderLinesSection(job) {
  const section = el('section', { class: 'jobs-section' }, [
    el('div', { class: 'jobs-section-head' }, [
      el('h3', { text: 'Lines' }),
      el('p', { text: 'Requested products, services, fees, and notes. Lines do not reserve stock or start production.' }),
    ]),
  ]);
  const list = el('div', { class: 'jobs-lines-list' });
  const lines = Array.isArray(job.lines) ? job.lines : [];
  if (!lines.length) {
    list.append(el('div', { class: 'jobs-empty jobs-empty--compact', text: 'No lines yet.' }));
  } else {
    lines.forEach((line) => list.append(renderLineRow(job, line)));
  }
  section.append(list, renderLineForm(job));
  return section;
}

function renderLineRow(job, line) {
  const row = el('div', { class: 'jobs-line-row' });
  const refs = [itemName(line.item_id), recipeName(line.recipe_id)].filter(Boolean).join(' | ') || 'No item or recipe link';
  row.append(
    el('div', { class: 'jobs-line-main' }, [
      el('strong', { text: line.description || 'Line' }),
      el('span', { text: refs }),
      el('span', { text: `${line.line_type || 'line'} | ${line.status || 'pending'}${line.display_uom ? ` | uom ${line.display_uom}` : ''}` }),
    ]),
    el('div', { class: 'jobs-line-value', text: line.unit_price_cents == null ? '-' : moneyFromCents(line.unit_price_cents) }),
  );
  const actions = el('div', { class: 'jobs-line-actions' }, [
    el('button', { type: 'button', class: 'btn small', text: 'Edit' }),
    el('button', { type: 'button', class: 'btn small danger', text: 'Delete' }),
  ]);
  actions.children[0].addEventListener('click', () => {
    state.lineEditId = line.id;
    render();
  });
  actions.children[1].addEventListener('click', async () => {
    if (!confirm('Delete this job line? This only removes it from the job.')) return;
    try {
      await apiDelete(`/app/jobs/${job.id}/lines/${line.id}`);
      await loadSelectedJob(job.id, { rerender: false });
      await loadJobs({ keepSelection: true });
      render();
      toast('Line deleted.');
    } catch (error) {
      toast(safeError(error, 'Unable to delete line.'), 'error');
    }
  });
  row.append(actions);
  return row;
}

function renderLineForm(job) {
  const editing = (job.lines || []).find((line) => String(line.id) === String(state.lineEditId));
  const form = el('form', { class: 'jobs-line-form', 'data-role': 'job-line-form' });
  const lineType = el('select', { class: 'jobs-input', name: 'line_type' }, selectOptions(LINE_TYPES, editing?.line_type || 'product'));
  const description = el('input', {
    class: 'jobs-input',
    name: 'description',
    required: 'true',
    value: editing?.description || '',
    placeholder: 'Description',
  });
  const itemSelect = el('select', { class: 'jobs-input', name: 'item_id' }, referenceOptions(state.items, editing?.item_id, 'No item'));
  const recipeSelect = el('select', { class: 'jobs-input', name: 'recipe_id' }, referenceOptions(state.recipes, editing?.recipe_id, 'No recipe'));
  const quantity = el('input', {
    class: 'jobs-input',
    name: 'quantity_decimal',
    type: 'number',
    min: '0',
    step: '0.001',
    placeholder: editing ? 'Leave blank to keep quantity' : 'Optional quantity',
  });
  const uom = el('input', { class: 'jobs-input', name: 'uom', placeholder: 'uom, e.g. ea or kg', value: editing?.display_uom || '' });
  const price = el('input', {
    class: 'jobs-input',
    name: 'unit_price',
    type: 'number',
    min: '0',
    step: '0.01',
    value: editing?.unit_price_cents != null ? String(Number(editing.unit_price_cents) / 100) : '',
    placeholder: 'Unit price',
  });
  const status = el('select', { class: 'jobs-input', name: 'status' }, selectOptions(LINE_STATUSES, editing?.status || 'pending'));
  const error = el('div', { class: 'jobs-error hidden', 'data-role': 'line-form-error' });

  itemSelect.addEventListener('change', () => {
    const found = state.items.find((item) => String(item.id) === String(itemSelect.value));
    if (found?.uom && !uom.value.trim()) uom.value = found.uom;
  });

  form.append(
    el('div', { class: 'jobs-form-subhead' }, [
      el('h4', { text: editing ? 'Edit line' : 'Add line' }),
      el('p', { text: 'Quantity is sent as entered. BUS Core stores the backend base quantity.' }),
    ]),
    el('div', { class: 'jobs-line-form-grid' }, [
      field('Type', lineType),
      field('Description', description),
      field('Item', itemSelect),
      field('Recipe', recipeSelect),
      field('Quantity', quantity),
      field('UOM', uom),
      field('Unit price', price),
      field('Line status', status),
    ]),
    error,
    el('div', { class: 'jobs-action-row' }, [
      el('button', { class: 'btn primary', type: 'submit', text: editing ? 'Save Line' : 'Add Line' }),
      ...(editing ? [el('button', { class: 'btn', type: 'button', text: 'Cancel', 'data-action': 'cancel-line-edit' })] : []),
    ]),
  );

  form.querySelector('[data-action="cancel-line-edit"]')?.addEventListener('click', () => {
    state.lineEditId = null;
    render();
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    await saveLine(job, form, editing);
  });
  return form;
}

async function saveLine(job, form, editing) {
  const data = new FormData(form);
  const description = String(data.get('description') || '').trim();
  if (!description) {
    showFormError(form, 'Description is required.');
    return;
  }
  const quantity = String(data.get('quantity_decimal') || '').trim();
  const payload = {
    line_type: String(data.get('line_type') || 'product'),
    description,
    item_id: parseOptionalInt(data.get('item_id')),
    recipe_id: parseOptionalInt(data.get('recipe_id')),
    unit_price_cents: centsFromMoney(data.get('unit_price')),
    status: String(data.get('status') || 'pending'),
  };
  if (quantity) {
    payload.quantity_decimal = quantity;
    payload.uom = String(data.get('uom') || '').trim();
  } else if (!editing && String(data.get('uom') || '').trim()) {
    payload.uom = String(data.get('uom') || '').trim();
  }
  try {
    if (editing?.id) {
      await apiPatch(`/app/jobs/${job.id}/lines/${editing.id}`, payload);
      toast('Line saved.');
    } else {
      await apiPost(`/app/jobs/${job.id}/lines`, payload);
      toast('Line added.');
    }
    state.lineEditId = null;
    await loadSelectedJob(job.id, { rerender: false });
    await loadJobs({ keepSelection: true });
    render();
  } catch (error) {
    showFormError(form, safeError(error, 'Unable to save line.'));
  }
}

function renderEventsSection(job) {
  const section = el('section', { class: 'jobs-section' }, [
    el('div', { class: 'jobs-section-head' }, [
      el('h3', { text: 'Timeline' }),
      el('p', { text: 'Manual notes and job memory only. Source records stay authoritative where they belong.' }),
    ]),
  ]);
  const timeline = el('div', { class: 'jobs-timeline' });
  const events = Array.isArray(job.events) ? job.events : [];
  if (!events.length) {
    timeline.append(el('div', { class: 'jobs-empty jobs-empty--compact', text: 'No events yet.' }));
  } else {
    events.forEach((event) => {
      timeline.append(el('div', { class: 'jobs-event' }, [
        el('span', { class: 'jobs-event-time', text: formatDateTime(event.created_at) }),
        el('strong', { text: event.event_type || 'note' }),
        el('p', { text: event.message || '' }),
      ]));
    });
  }
  section.append(timeline, renderEventForm(job));
  return section;
}

function renderEventForm(job) {
  const form = el('form', { class: 'jobs-event-form', 'data-role': 'job-event-form' });
  const message = el('textarea', {
    class: 'jobs-input jobs-textarea',
    name: 'message',
    rows: '2',
    required: 'true',
    placeholder: 'Add a job note...',
  });
  const error = el('div', { class: 'jobs-error hidden', 'data-role': 'event-form-error' });
  form.append(
    field('New note', message),
    error,
    el('div', { class: 'jobs-action-row' }, [
      el('button', { class: 'btn primary', type: 'submit', text: 'Add Note' }),
    ]),
  );
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const text = String(new FormData(form).get('message') || '').trim();
    if (!text) {
      showFormError(form, 'Message is required.');
      return;
    }
    try {
      await apiPost(`/app/jobs/${job.id}/events`, { event_type: 'note', message: text });
      await loadSelectedJob(job.id, { rerender: false });
      render();
      toast('Note added.');
    } catch (error) {
      showFormError(form, safeError(error, 'Unable to add note.'));
    }
  });
  return form;
}

async function initialRender(root) {
  root.className = 'jobs-shell';
  root.innerHTML = '<div class="card jobs-loading">Loading jobs...</div>';
  try {
    await ensureToken();
    await loadReferenceData();
    await loadJobs({ keepSelection: true });
    render();
  } catch (error) {
    root.innerHTML = `<div class="card jobs-load-error"><h2>Jobs unavailable</h2><p>${safeError(error, 'Unable to load Jobs.')}</p></div>`;
  }
}

export async function mountJobs() {
  const root = host();
  if (!root) return;
  state = newState();
  await initialRender(root);
}

export function unmountJobs() {
  const root = host();
  if (root) root.innerHTML = '';
  state = newState();
}

export default mountJobs;