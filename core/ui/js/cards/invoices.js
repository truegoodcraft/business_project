// SPDX-License-Identifier: AGPL-3.0-or-later
import { apiDelete, apiGet, apiPatch, apiPost, ensureToken } from '../api.js';

const INVOICE_STATUSES = ['draft', 'issued', 'paid', 'void'];
const LINE_TYPES = ['product', 'service', 'fee', 'note'];
const UOM_OPTIONS = ['ea', 'hr', 'day', 'kg', 'g', 'lb', 'm', 'cm', 'mm', 'm2', 'cm2', 'l', 'ml'];
const INVOICE_ERROR_MESSAGES = {
  invoice_contact_required: 'Choose a contact before saving the invoice.',
  invoice_issue_requires_line: 'Add at least one line before issuing the invoice.',
  invoice_payment_requires_issue: 'Issue the invoice before marking it paid.',
  invoice_void_cannot_be_paid: 'Void invoices cannot be marked paid.',
  invoice_paid_cannot_be_void: 'Paid invoices cannot be voided.',
  invoice_edit_forbidden_after_paid: 'Paid invoices are read-only financially.',
  invoice_edit_forbidden_after_void: 'Void invoices are read-only financially.',
  invoice_edit_forbidden_after_issue: 'Issued invoices are read-only until paid or voided.',
  quantity_decimal_required: 'Enter a quantity or leave it blank.',
  quantity_decimal_invalid: 'Enter a valid quantity.',
  uom_required: 'Choose a unit when quantity is set.',
  uom_requires_quantity_decimal: 'Clear the unit or enter a quantity.',
  unit_price_cents_invalid: 'Enter a valid non-negative unit price.',
  invalid_invoice_line_type: 'Choose a valid invoice line type.',
  tax_rate_percent_invalid: 'Enter a valid tax percent.',
};

let state = newState();

function newState() {
  return {
    invoices: [],
    selectedId: null,
    selectedInvoice: null,
    contacts: [],
    jobs: [],
    search: '',
    status: '',
    lineEditId: null,
    busy: false,
  };
}

function host() {
  return document.querySelector('[data-role="invoices-root"]');
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'checked') node.checked = !!value;
    else if (key === 'disabled') node.disabled = !!value;
    else node.setAttribute(key, value);
  });
  for (const child of Array.isArray(children) ? children : [children]) {
    if (child === null || child === undefined) continue;
    node.append(child);
  }
  return node;
}

function safeError(error, fallback = 'Request failed.') {
  const detail = error?.payload?.detail ?? error?.data?.detail ?? error?.detail;
  const code = detail?.error || error?.payload?.error || error?.data?.error || error?.error;
  if (error?.status === 401) return 'Sign in again to view invoices.';
  if (error?.status === 403) {
    if (code === 'writes_disabled') return 'Writes are disabled. Turn writes back on to save invoice changes.';
    return 'Your account does not have permission for that invoice action.';
  }
  if (typeof detail === 'string') return INVOICE_ERROR_MESSAGES[detail] || detail.replaceAll('_', ' ');
  if (typeof code === 'string') return INVOICE_ERROR_MESSAGES[code] || code.replaceAll('_', ' ');
  if (typeof error?.message === 'string' && error.message && !error.message.includes('[object Object]')) {
    return error.message;
  }
  return fallback;
}

function toast(message, tone = 'ok') {
  const note = document.createElement('div');
  note.textContent = message;
  note.className = `invoice-toast invoice-toast--${tone === 'error' ? 'error' : 'ok'}`;
  document.body.appendChild(note);
  setTimeout(() => {
    note.classList.add('invoice-toast--hide');
    setTimeout(() => note.remove(), 280);
  }, 2400);
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

function formatDate(value, fallback = 'No date') {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatDateTime(value, fallback = 'Unknown time') {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function parseOptionalInt(value) {
  const raw = String(value ?? '').trim();
  if (!raw) return null;
  const numeric = Number(raw);
  return Number.isInteger(numeric) && numeric > 0 ? numeric : null;
}

function selectOptions(values, selected, labeler = (value) => value) {
  return values.map((value) => {
    const option = el('option', { value: String(value), text: labeler(value) });
    if (String(value) === String(selected ?? '')) option.selected = true;
    return option;
  });
}

function referenceOptions(entries, selected, placeholder, labeler = (entry) => entry.name || `#${entry.id}`) {
  const options = [el('option', { value: '', text: placeholder })];
  entries.forEach((entry) => {
    const option = el('option', { value: String(entry.id), text: labeler(entry) });
    if (String(entry.id) === String(selected ?? '')) option.selected = true;
    options.push(option);
  });
  return options;
}

function contactName(id) {
  if (id === null || id === undefined || id === '') return 'No contact';
  const found = state.contacts.find((entry) => String(entry.id) === String(id));
  return found?.name || `Contact #${id}`;
}

function jobName(id) {
  if (id === null || id === undefined || id === '') return 'No job';
  const found = state.jobs.find((entry) => String(entry.id) === String(id));
  return found?.title || `Job #${id}`;
}

function filteredInvoices() {
  const query = state.search.trim().toLowerCase();
  return state.invoices.filter((invoice) => {
    if (state.status && invoice.status !== state.status) return false;
    if (!query) return true;
    const haystack = [
      invoice.invoice_number,
      invoice.status,
      contactName(invoice.contact_id),
      jobName(invoice.job_id),
    ].join(' ').toLowerCase();
    return haystack.includes(query);
  });
}

function isDraft(invoice) {
  return invoice?.status === 'draft';
}

function isReadOnlyFinancial(invoice) {
  return invoice?.status === 'paid' || invoice?.status === 'void';
}

function setInvoiceRoute(id = null) {
  const nextHash = id ? `#/invoices/${encodeURIComponent(id)}` : '#/invoices';
  if (window.location.hash !== nextHash) {
    window.location.hash = nextHash;
  }
}

async function loadContacts() {
  const contacts = await apiGet('/app/contacts').catch(() => []);
  state.contacts = Array.isArray(contacts) ? contacts : [];
}

async function loadJobs() {
  const jobs = await apiGet('/app/jobs').catch(() => []);
  state.jobs = Array.isArray(jobs) ? jobs : [];
}

async function loadInvoices({ keepSelection = true } = {}) {
  state.invoices = await apiGet('/app/invoices');
  if (!Array.isArray(state.invoices)) state.invoices = [];
  const routeId = parseOptionalInt(window.BUS_ROUTE?.id);
  const routeExists = routeId ? state.invoices.some((invoice) => String(invoice.id) === String(routeId)) : false;
  if (routeExists) state.selectedId = routeId;
  const stillExists = state.invoices.some((invoice) => String(invoice.id) === String(state.selectedId));
  if (!keepSelection || !stillExists) {
    state.selectedId = routeExists ? routeId : (state.invoices[0]?.id || null);
  }
  if (state.selectedId) {
    await loadSelectedInvoice(state.selectedId, { rerender: false });
  } else {
    state.selectedInvoice = null;
  }
}

async function loadSelectedInvoice(invoiceId, { rerender = true } = {}) {
  state.selectedId = invoiceId;
  state.selectedInvoice = await apiGet(`/app/invoices/${invoiceId}`);
  if (rerender) render();
}

function lineQuantityLabel(line) {
  const quantity = String(line?.quantity_decimal ?? '').trim();
  const uom = String(line?.uom ?? '').trim();
  if (!quantity && !uom) return 'No quantity';
  if (!quantity) return uom;
  if (!uom) return quantity;
  return `${quantity} ${uom}`;
}

function render() {
  const root = host();
  if (!root) return;
  root.className = 'invoices-shell';
  root.replaceChildren(
    el('section', { class: 'invoices-header card' }, [
      el('div', { class: 'invoices-heading' }, [
        el('h1', { text: 'Invoices' }),
        el('p', { text: 'Create, issue, and mark paid local invoices' }),
      ]),
      el('button', { class: 'btn primary invoices-new-btn', type: 'button', text: 'New Invoice', 'data-action': 'new-invoice' }),
    ]),
    el('div', { class: 'invoices-layout' }, [
      renderListPanel(),
      renderDetailPanel(),
    ]),
  );
  root.querySelector('[data-action="new-invoice"]')?.addEventListener('click', () => {
    state.selectedId = null;
    state.selectedInvoice = null;
    state.lineEditId = null;
    setInvoiceRoute(null);
    render();
  });
}

function renderListPanel() {
  const rows = filteredInvoices();
  const panel = el('section', { class: 'card invoices-list-panel' });
  const search = el('input', {
    class: 'invoices-input invoices-search',
    type: 'search',
    placeholder: 'Search invoice number, contact, or job...',
    value: state.search,
  });
  const status = el('select', { class: 'invoices-input' }, [
    el('option', { value: '', text: 'All statuses' }),
    ...selectOptions(INVOICE_STATUSES, state.status),
  ]);
  const filters = el('div', { class: 'invoices-filters' }, [search, status]);
  const count = el('div', { class: 'invoices-list-count', text: `${rows.length} invoice${rows.length === 1 ? '' : 's'}` });
  const list = el('div', { class: 'invoices-list' });

  if (!rows.length) {
    list.append(
      el('div', { class: 'invoices-empty' }, [
        el('strong', { text: 'No invoices yet.' }),
        el('p', { text: 'Create a draft invoice manually or from a job. Payment records one local finance revenue event.' }),
      ]),
    );
  } else {
    rows.forEach((invoice) => list.append(renderInvoiceRow(invoice)));
  }

  search.addEventListener('input', () => {
    state.search = search.value;
    render();
  });
  status.addEventListener('change', () => {
    state.status = status.value;
    render();
  });

  panel.append(filters, count, list);
  return panel;
}

function renderInvoiceRow(invoice) {
  const row = el('button', { class: 'invoices-row', type: 'button', 'data-invoice-id': invoice.id });
  if (String(invoice.id) === String(state.selectedId)) row.classList.add('active');
  row.append(
    el('span', { class: 'invoices-row-number', text: invoice.invoice_number || `Invoice #${invoice.id}` }),
    el('span', { class: `invoices-badge invoices-badge--${invoice.status || 'draft'}`, text: invoice.status || 'draft' }),
    el('span', { class: 'invoices-row-meta', text: contactName(invoice.contact_id) }),
    el('span', { class: 'invoices-row-meta', text: invoice.job_id ? jobName(invoice.job_id) : 'Manual invoice' }),
    el('span', { class: 'invoices-row-meta', text: `Due ${formatDate(invoice.due_date, 'No due date')}` }),
    el('span', { class: 'invoices-row-total', text: moneyFromCents(invoice.total_cents) }),
  );
  row.addEventListener('click', async () => {
    try {
      state.lineEditId = null;
      setInvoiceRoute(invoice.id);
      await loadSelectedInvoice(invoice.id);
    } catch (error) {
      toast(safeError(error, 'Failed to load invoice.'), 'error');
    }
  });
  return row;
}

function renderDetailPanel() {
  const panel = el('section', { class: 'card invoices-detail-panel' });
  const invoice = state.selectedInvoice;
  panel.append(renderInvoiceForm(invoice));
  if (invoice) {
    panel.append(renderInvoiceSummary(invoice), renderInvoiceActions(invoice), renderLinesSection(invoice));
  }
  return panel;
}

function renderInvoiceForm(invoice) {
  const isNew = !invoice;
  const form = el('form', { class: 'invoices-form', 'data-role': 'invoice-form' });
  const readonly = !isNew && !isDraft(invoice);
  const contactSelect = el('select', { class: 'invoices-input', name: 'contact_id', disabled: readonly }, referenceOptions(state.contacts, invoice?.contact_id, 'Choose contact'));
  const jobSelect = el('select', { class: 'invoices-input', name: 'job_id', disabled: readonly }, referenceOptions(state.jobs, invoice?.job_id, 'No linked job', (entry) => entry.title || `Job #${entry.id}`));
  const dueDate = el('input', {
    class: 'invoices-input',
    name: 'due_date',
    type: 'date',
    value: invoice?.due_date ? String(invoice.due_date).slice(0, 10) : '',
    disabled: readonly,
  });
  const taxRate = el('input', {
    class: 'invoices-input',
    name: 'tax_rate_percent',
    type: 'number',
    min: '0',
    step: '0.01',
    value: invoice?.tax_rate_percent ?? '0',
    disabled: readonly,
  });
  const notes = el('textarea', {
    class: 'invoices-input invoices-textarea',
    name: 'notes',
    rows: '3',
    placeholder: 'Notes',
    disabled: readonly,
  });
  notes.value = invoice?.notes || '';

  const contactTools = el('div', { class: 'invoices-contact-control' }, [
    contactSelect,
    el('button', {
      class: 'btn secondary',
      type: 'button',
      text: '+ New Contact',
      'data-action': 'invoice-new-contact',
      disabled: readonly,
    }),
  ]);

  const headChildren = [
    el('div', {}, [
      el('h2', { text: isNew ? 'New Invoice' : (invoice.invoice_number || `Invoice #${invoice.id}`) }),
      el('p', {
        text: isNew
          ? 'Create a draft invoice linked to a contact and optionally a job.'
          : `Status ${invoice.status}. Payment records one local finance sale event only.`,
      }),
    ]),
  ];
  if (!isNew && invoice.job_id) {
    headChildren.push(el('span', { class: 'invoices-linked-job', text: `Linked to ${jobName(invoice.job_id)}` }));
  }

  const grid = el('div', { class: 'invoices-form-grid' }, [
    field('Contact', contactTools),
    field('Linked job', jobSelect),
    field('Due date', dueDate),
    field('Tax rate %', taxRate),
  ]);
  const error = el('div', { class: 'invoices-error hidden', 'data-role': 'invoice-form-error' });
  const actions = el('div', { class: 'invoices-action-row' }, [
    el('button', { class: 'btn primary', type: 'submit', text: isNew ? 'Create Invoice' : 'Save Invoice', disabled: readonly }),
    ...(!isNew
      ? [el('span', { class: 'invoices-muted', text: `Updated ${formatDateTime(invoice.updated_at)}` })]
      : []),
  ]);

  form.append(el('div', { class: 'invoices-detail-head' }, headChildren), grid, field('Notes', notes), error, actions);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    await saveInvoice(form, invoice);
  });
  form.querySelector('[data-action="invoice-new-contact"]')?.addEventListener('click', () => {
    openInvoiceContactModal({ form, contactSelect, existingInvoice: invoice });
  });
  return form;
}

function field(label, control) {
  return el('label', { class: 'invoices-field' }, [
    el('span', { class: 'invoices-label', text: label }),
    control,
  ]);
}

function showFormError(form, message) {
  const banner = form.querySelector('[data-role$="error"], [data-role="invoice-form-error"]');
  if (!banner) return;
  banner.textContent = message;
  banner.classList.remove('hidden');
}

function hideFormError(form) {
  const banner = form.querySelector('[data-role$="error"], [data-role="invoice-form-error"]');
  if (!banner) return;
  banner.textContent = '';
  banner.classList.add('hidden');
}

async function saveInvoice(form, existingInvoice) {
  hideFormError(form);
  const data = new FormData(form);
  const contactId = parseOptionalInt(data.get('contact_id'));
  if (!contactId) {
    showFormError(form, INVOICE_ERROR_MESSAGES.invoice_contact_required);
    return;
  }
  const payload = {
    contact_id: contactId,
    job_id: parseOptionalInt(data.get('job_id')),
    due_date: data.get('due_date') ? `${data.get('due_date')}T00:00:00` : null,
    tax_rate_percent: String(data.get('tax_rate_percent') || '0').trim() || '0',
    notes: String(data.get('notes') || '').trim() || null,
  };
  try {
    let saved;
    if (existingInvoice?.id) {
      saved = await apiPatch(`/app/invoices/${existingInvoice.id}`, payload);
      toast('Invoice saved.');
    } else {
      saved = await apiPost('/app/invoices', payload);
      toast('Invoice created.');
    }
    state.selectedId = saved.id;
    state.selectedInvoice = saved;
    setInvoiceRoute(saved.id);
    await loadInvoices({ keepSelection: true });
    render();
  } catch (error) {
    showFormError(form, safeError(error, 'Unable to save invoice.'));
  }
}

function renderInvoiceSummary(invoice) {
  return el('section', { class: 'invoices-summary-grid' }, [
    metricTile('Subtotal', moneyFromCents(invoice.subtotal_cents)),
    metricTile('Tax', moneyFromCents(invoice.tax_cents)),
    metricTile('Total', moneyFromCents(invoice.total_cents)),
    metricTile('Issue date', formatDate(invoice.issue_date, 'Not issued')),
    metricTile('Paid at', formatDate(invoice.paid_at, 'Not paid')),
    metricTile('Cash event', invoice.paid_cash_event_id ? `#${invoice.paid_cash_event_id}` : 'Not recorded'),
  ]);
}

function metricTile(label, value) {
  return el('div', { class: 'invoices-summary-tile' }, [
    el('span', { class: 'invoices-summary-name', text: label }),
    el('strong', { class: 'invoices-summary-value', text: value }),
  ]);
}

function renderInvoiceActions(invoice) {
  const section = el('section', { class: 'invoices-section invoices-actions-section' }, [
    el('div', { class: 'invoices-section-head' }, [
      el('h3', { text: 'Invoice actions' }),
      el('p', { text: 'Print opens a local printable invoice page. Mark Paid creates one local finance revenue event and does not touch stock or manufacturing.' }),
    ]),
  ]);
  const row = el('div', { class: 'invoices-action-row' });
  const printBtn = el('button', { class: 'btn secondary', type: 'button', text: 'Print' });
  printBtn.addEventListener('click', () => openInvoicePrint(invoice));

  if (invoice.status === 'draft') {
    const issueBtn = el('button', { class: 'btn primary', type: 'button', text: 'Issue Invoice' });
    const voidBtn = el('button', { class: 'btn secondary', type: 'button', text: 'Void Invoice' });
    issueBtn.addEventListener('click', () => issueInvoice(invoice));
    voidBtn.addEventListener('click', () => voidInvoice(invoice));
    row.append(printBtn, issueBtn, voidBtn);
  } else if (invoice.status === 'issued') {
    const paidBtn = el('button', { class: 'btn primary', type: 'button', text: 'Mark Paid' });
    const voidBtn = el('button', { class: 'btn secondary', type: 'button', text: 'Void Invoice' });
    paidBtn.addEventListener('click', () => markInvoicePaid(invoice));
    voidBtn.addEventListener('click', () => voidInvoice(invoice));
    row.append(printBtn, paidBtn, voidBtn);
  } else if (invoice.status === 'paid') {
    row.append(printBtn, el('span', { class: 'invoices-readonly-note', text: 'Paid invoices are read-only financially.' }));
  } else if (invoice.status === 'void') {
    row.append(printBtn, el('span', { class: 'invoices-readonly-note', text: 'Void invoices are read-only financially.' }));
  }

  section.append(row);
  return section;
}

function openInvoicePrint(invoice) {
  if (!invoice?.id) return;
  window.open(`/app/invoices/${encodeURIComponent(invoice.id)}/print`, '_blank', 'noopener');
}

async function issueInvoice(invoice) {
  try {
    await apiPost(`/app/invoices/${invoice.id}/issue`, {});
    await loadInvoices({ keepSelection: true });
    render();
    toast('Invoice issued.');
  } catch (error) {
    toast(safeError(error, 'Unable to issue invoice.'), 'error');
  }
}

async function markInvoicePaid(invoice) {
  const confirmed = window.confirm('Mark this invoice paid? BUS Core will record one local finance revenue event.');
  if (!confirmed) return;
  try {
    await apiPost(`/app/invoices/${invoice.id}/mark-paid`, {});
    await loadInvoices({ keepSelection: true });
    render();
    toast('Invoice marked paid.');
  } catch (error) {
    toast(safeError(error, 'Unable to mark invoice paid.'), 'error');
  }
}

async function voidInvoice(invoice) {
  const confirmed = window.confirm('Void this invoice? This keeps the invoice but prevents payment.');
  if (!confirmed) return;
  try {
    await apiPost(`/app/invoices/${invoice.id}/void`, {});
    await loadInvoices({ keepSelection: true });
    render();
    toast('Invoice voided.');
  } catch (error) {
    toast(safeError(error, 'Unable to void invoice.'), 'error');
  }
}

function renderLinesSection(invoice) {
  const section = el('section', { class: 'invoices-section' }, [
    el('div', { class: 'invoices-section-head' }, [
      el('h3', { text: 'Lines' }),
      el('p', { text: 'Invoice lines are billing records only. They do not control stock movement.' }),
    ]),
  ]);
  const list = el('div', { class: 'invoices-lines-list' });
  const lines = Array.isArray(invoice.lines) ? invoice.lines : [];
  if (!lines.length) {
    list.append(el('div', { class: 'invoices-empty invoices-empty--compact', text: 'No lines yet.' }));
  } else {
    lines.forEach((line) => list.append(renderLineRow(invoice, line)));
  }
  section.append(list);
  if (isDraft(invoice)) {
    section.append(renderLineForm(invoice));
  }
  return section;
}

function renderLineRow(invoice, line) {
  const row = el('div', { class: 'invoices-line-row' });
  row.append(
    el('div', { class: 'invoices-line-main' }, [
      el('strong', { text: line.description || 'Line' }),
      el('span', { text: `${line.line_type || 'line'} | ${lineQuantityLabel(line)}` }),
      el('span', { text: `${line.taxable ? 'Taxable' : 'Non-taxable'}${line.job_line_id ? ` | Job line #${line.job_line_id}` : ''}` }),
    ]),
    el('div', { class: 'invoices-line-value' }, [
      el('strong', { text: moneyFromCents(line.line_subtotal_cents) }),
      el('span', { text: line.unit_price_cents == null ? 'No unit price' : `${moneyFromCents(line.unit_price_cents)} each` }),
    ]),
  );
  if (isDraft(invoice)) {
    const actions = el('div', { class: 'invoices-line-actions' }, [
      el('button', { type: 'button', class: 'btn small', text: 'Edit' }),
      el('button', { type: 'button', class: 'btn small danger', text: 'Delete' }),
    ]);
    actions.children[0].addEventListener('click', () => {
      state.lineEditId = line.id;
      render();
    });
    actions.children[1].addEventListener('click', async () => {
      if (!window.confirm('Delete this invoice line?')) return;
      try {
        await apiDelete(`/app/invoices/${invoice.id}/lines/${line.id}`);
        state.lineEditId = null;
        await loadSelectedInvoice(invoice.id, { rerender: false });
        await loadInvoices({ keepSelection: true });
        render();
        toast('Line deleted.');
      } catch (error) {
        toast(safeError(error, 'Unable to delete line.'), 'error');
      }
    });
    row.append(actions);
  }
  return row;
}

function renderLineForm(invoice) {
  const editing = (invoice.lines || []).find((line) => String(line.id) === String(state.lineEditId));
  const form = el('form', { class: 'invoices-line-form', 'data-role': 'invoice-line-form' });
  const lineType = el('select', { class: 'invoices-input', name: 'line_type' }, selectOptions(LINE_TYPES, editing?.line_type || 'service'));
  const description = el('input', {
    class: 'invoices-input',
    name: 'description',
    required: 'true',
    value: editing?.description || '',
    placeholder: 'Description',
  });
  const quantity = el('input', {
    class: 'invoices-input',
    name: 'quantity_decimal',
    type: 'number',
    min: '0',
    step: '0.001',
    value: editing?.quantity_decimal || '',
    placeholder: 'Optional quantity',
  });
  const uom = el('select', { class: 'invoices-input', name: 'uom' }, [
    el('option', { value: '', text: 'No unit' }),
    ...selectOptions(UOM_OPTIONS, editing?.uom || ''),
  ]);
  const unitPrice = el('input', {
    class: 'invoices-input',
    name: 'unit_price',
    type: 'number',
    min: '0',
    step: '0.01',
    value: editing?.unit_price_cents != null ? String(Number(editing.unit_price_cents) / 100) : '',
    placeholder: 'Unit price',
  });
  const taxable = el('input', {
    type: 'checkbox',
    name: 'taxable',
    checked: editing?.taxable ?? true,
  });
  const sortOrder = el('input', {
    class: 'invoices-input',
    name: 'sort_order',
    type: 'number',
    step: '1',
    value: String(editing?.sort_order ?? 0),
  });
  const error = el('div', { class: 'invoices-error hidden', 'data-role': 'line-form-error' });

  const syncLineControls = () => {
    const note = lineType.value === 'note';
    quantity.disabled = note;
    uom.disabled = note;
    unitPrice.disabled = note;
    taxable.disabled = note;
    if (note) {
      quantity.value = '';
      uom.value = '';
      unitPrice.value = '';
      taxable.checked = false;
    }
  };
  lineType.addEventListener('change', syncLineControls);
  syncLineControls();

  form.append(
    el('div', { class: 'invoices-form-subhead' }, [
      el('h4', { text: editing ? 'Edit line' : 'Add line' }),
      el('p', { text: 'Tax applies only to lines marked taxable. Money stays in integer cents in the backend.' }),
    ]),
    el('div', { class: 'invoices-line-form-grid' }, [
      field('Type', lineType),
      field('Description', description),
      field('Quantity', quantity),
      field('UOM', uom),
      field('Unit price', unitPrice),
      field('Sort order', sortOrder),
      field('Taxable', el('label', { class: 'invoices-toggle' }, [taxable, el('span', { text: 'Apply invoice tax' })])),
    ]),
    error,
    el('div', { class: 'invoices-action-row' }, [
      el('button', { class: 'btn primary', type: 'submit', text: editing ? 'Save Line' : 'Add Line' }),
      ...(editing ? [el('button', { class: 'btn secondary', type: 'button', text: 'Cancel', 'data-action': 'cancel-line-edit' })] : []),
    ]),
  );

  form.querySelector('[data-action="cancel-line-edit"]')?.addEventListener('click', () => {
    state.lineEditId = null;
    render();
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    await saveLine(invoice, form, editing);
  });
  return form;
}

async function saveLine(invoice, form, editing) {
  hideFormError(form);
  const data = new FormData(form);
  const description = String(data.get('description') || '').trim();
  if (!description) {
    showFormError(form, 'Description is required.');
    return;
  }
  const quantity = String(data.get('quantity_decimal') || '').trim();
  const unitPriceCents = centsFromMoney(data.get('unit_price'));
  const payload = {
    line_type: String(data.get('line_type') || 'service'),
    description,
    quantity_decimal: quantity || null,
    uom: String(data.get('uom') || '').trim() || null,
    unit_price_cents: unitPriceCents,
    taxable: data.get('taxable') === 'on',
    sort_order: Number(data.get('sort_order') || 0),
  };
  if (payload.line_type === 'note') {
    payload.quantity_decimal = null;
    payload.uom = null;
    payload.unit_price_cents = null;
    payload.taxable = false;
  }
  try {
    if (editing?.id) {
      await apiPatch(`/app/invoices/${invoice.id}/lines/${editing.id}`, payload);
      toast('Line saved.');
    } else {
      await apiPost(`/app/invoices/${invoice.id}/lines`, payload);
      toast('Line added.');
    }
    state.lineEditId = null;
    await loadSelectedInvoice(invoice.id, { rerender: false });
    await loadInvoices({ keepSelection: true });
    render();
  } catch (error) {
    showFormError(form, safeError(error, 'Unable to save line.'));
  }
}

function openInvoiceContactModal({ form, contactSelect, existingInvoice }) {
  const overlay = el('div', { class: 'contacts-modal', role: 'dialog', 'aria-modal': 'true' });
  const box = el('div', { class: 'contacts-modal-box' });
  const name = el('input', {
    class: 'invoices-input',
    name: 'contact_name',
    required: 'true',
    placeholder: 'Name',
    autocomplete: 'name',
  });
  const contactInfo = el('input', {
    class: 'invoices-input',
    name: 'contact_info',
    placeholder: 'Email, phone, or preferred contact info',
    autocomplete: 'email',
  });
  const error = el('div', { class: 'invoices-error hidden', 'data-role': 'invoice-contact-error' });
  const save = el('button', { class: 'btn primary', type: 'submit', text: 'Create Contact' });
  const cancel = el('button', { class: 'btn secondary', type: 'button', text: 'Cancel' });
  const modalForm = el('form', { class: 'contacts-modal-form' }, [
    field('Name', name),
    field('Contact info', contactInfo),
    error,
    el('div', { class: 'contacts-modal-actions' }, [cancel, save]),
  ]);

  box.append(
    el('div', { class: 'contacts-modal-title-row' }, [
      el('div', { class: 'contacts-modal-title', text: 'New Contact' }),
      el('button', { class: 'btn ghost', type: 'button', text: 'Close', 'data-action': 'close-contact-modal' }),
    ]),
    el('p', { class: 'contacts-modal-body', text: 'Create a contact and keep working in invoices.' }),
    modalForm,
  );
  overlay.append(box);
  document.body.append(overlay);

  const close = () => overlay.remove();
  cancel.addEventListener('click', close);
  overlay.querySelector('[data-action="close-contact-modal"]')?.addEventListener('click', close);
  overlay.addEventListener('click', (event) => {
    if (event.target === overlay) close();
  });

  modalForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    hideFormError(modalForm);
    const contactNameValue = name.value.trim();
    const contactValue = contactInfo.value.trim();
    if (!contactNameValue) {
      showFormError(modalForm, 'Contact name is required.');
      name.focus();
      return;
    }
    save.disabled = true;
    try {
      const created = await apiPost('/app/contacts', {
        name: contactNameValue,
        contact: contactValue || null,
        is_vendor: false,
      });
      await loadContacts();
      const createdId = created?.id;
      contactSelect.replaceChildren(...referenceOptions(state.contacts, createdId, 'Choose contact'));

      if (existingInvoice?.id && createdId) {
        try {
          await apiPatch(`/app/invoices/${existingInvoice.id}`, { contact_id: createdId });
        } catch (linkError) {
          close();
          showFormError(
            form,
            `Contact "${contactNameValue}" was created, but it could not be linked to this invoice. Save Invoice to try linking it again. ${safeError(linkError, 'Unable to link contact.')}`,
          );
          toast('Contact created, but not linked.', 'error');
          return;
        }
        close();
        toast('Contact created and linked.');
        await loadInvoices({ keepSelection: true });
        render();
        return;
      }

      close();
      toast('Contact created and selected.');
    } catch (submitError) {
      showFormError(modalForm, safeError(submitError, 'Unable to create contact.'));
      save.disabled = false;
    }
  });

  name.focus();
}

async function initialRender(root) {
  root.className = 'invoices-shell';
  root.replaceChildren(el('div', { class: 'card invoices-loading', text: 'Loading invoices...' }));
  try {
    await ensureToken();
    await Promise.all([loadContacts(), loadJobs()]);
    await loadInvoices({ keepSelection: true });
    render();
  } catch (error) {
    root.replaceChildren(
      el('div', { class: 'card invoices-load-error' }, [
        el('h2', { text: 'Invoices unavailable' }),
        el('p', { text: safeError(error, 'Unable to load invoices.') }),
      ]),
    );
  }
}

export async function mountInvoices() {
  const root = host();
  if (!root) return;
  state = newState();
  const routeId = parseOptionalInt(window.BUS_ROUTE?.id);
  if (routeId) state.selectedId = routeId;
  await initialRender(root);
}

export function unmountInvoices() {
  const root = host();
  if (root) root.replaceChildren();
  state = newState();
}

export default mountInvoices;
