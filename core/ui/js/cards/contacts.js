// core/ui/js/cards/contacts.js
import { apiGet, apiPost, apiPut, apiDelete, ensureToken } from '../api.js';

export async function mountContacts(container) {
  container.innerHTML = '';
  container.style.background = '#0f1115';
  container.style.color = '#e5e7eb';
  container.style.padding = '16px';
  container.style.borderRadius = '14px';

  const header = document.createElement('div');
  header.style.display = 'flex';
  header.style.justifyContent = 'space-between';
  header.style.alignItems = 'center';
  header.style.marginBottom = '12px';

  const title = document.createElement('h2');
  title.textContent = 'Contacts';
  title.style.fontSize = '18px';
  title.style.margin = '0';

  const newBtn = document.createElement('button');
  newBtn.textContent = 'New Contact';
  styleBtn(newBtn);

  header.append(title, newBtn);

  const table = document.createElement('table');
  table.style.width = '100%';
  table.style.borderCollapse = 'separate';
  table.style.borderSpacing = '0';
  table.style.background = '#111318';
  table.style.borderRadius = '12px';
  table.style.overflow = 'hidden';

  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th style="text-align:left;padding:10px;">Name</th>
      <th style="text-align:left;padding:10px;">Type</th>
      <th style="text-align:left;padding:10px;">Email</th>
      <th style="text-align:left;padding:10px;">Phone</th>
      <th style="text-align:left;padding:10px;">Lead Time</th>
      <th style="text-align:left;padding:10px;">Material</th>
      <th style="text-align:left;padding:10px;">Notes</th>
      <th style="text-align:left;padding:10px;">Actions</th>
    </tr>`;
  thead.querySelectorAll('th').forEach(th => th.style.background = '#1a1f2b');
  const tbody = document.createElement('tbody');
  table.append(thead, tbody);

  const modal = createModal();
  document.body.appendChild(modal.root);

  newBtn.addEventListener('click', () => {
    openModal(modal, {
      id: null,
      name: '',
      type: 'vendor',
      email: '',
      phone: '',
      lead_time_days: '',
      material_specialty: '',
      notes: ''
    });
  });

  modal.onSubmit = async (model) => {
    await ensureToken();
    if (model.id == null) {
      await apiPost('/app/contacts', model);
    } else {
      await apiPut(`/app/contacts/${model.id}`, model);
    }
    await load();
    modal.close();
  };

  async function load() {
    const rows = await apiGet('/app/contacts');
    renderRows(rows);
  }

  function renderRows(rows) {
    tbody.innerHTML = '';
    for (const r of rows) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="padding:10px;border-top:1px solid #222733;">${escapeHtml(r.name)}</td>
        <td style="padding:10px;border-top:1px solid #222733;">${escapeHtml(r.type)}</td>
        <td style="padding:10px;border-top:1px solid #222733;">${escapeHtml(r.email || '')}</td>
        <td style="padding:10px;border-top:1px solid #222733;">${escapeHtml(r.phone || '')}</td>
        <td style="padding:10px;border-top:1px solid #222733;">${r.lead_time_days ?? ''}</td>
        <td style="padding:10px;border-top:1px solid #222733;">${escapeHtml(r.material_specialty || '')}</td>
        <td style="padding:10px;border-top:1px solid #222733;max-width:280px;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(r.notes || '')}</td>
        <td style="padding:10px;border-top:1px solid #222733;">
          <div style="display:flex;gap:8px;">
            <button class="edit">Edit</button>
            <button class="del">Delete</button>
          </div>
        </td>
      `;
      tr.querySelectorAll('button').forEach(styleBtn);

      tr.querySelector('.edit').addEventListener('click', () => {
        openModal(modal, {
          id: r.id,
          name: r.name,
          type: r.type,
          email: r.email || '',
          phone: r.phone || '',
          lead_time_days: r.lead_time_days ?? '',
          material_specialty: r.material_specialty || '',
          notes: r.notes || ''
        });
      });

      tr.querySelector('.del').addEventListener('click', async () => {
        if (!confirm(`Delete ${r.name}?`)) return;
        await ensureToken();
        await apiDelete(`/app/contacts/${r.id}`);
        await load();
      });

      tbody.appendChild(tr);
    }
  }

  container.append(header, table);
  await load();
}

function styleBtn(btn) {
  btn.style.background = '#23293a';
  btn.style.color = '#e5e7eb';
  btn.style.border = '1px solid #2b3246';
  btn.style.padding = '8px 10px';
  btn.style.borderRadius = '10px';
  btn.style.cursor = 'pointer';
  btn.onmouseenter = () => btn.style.background = '#2a3146';
  btn.onmouseleave = () => btn.style.background = '#23293a';
}

function createModal() {
  const root = document.createElement('div');
  root.style.position = 'fixed';
  root.style.inset = '0';
  root.style.display = 'none';
  root.style.alignItems = 'center';
  root.style.justifyContent = 'center';
  root.style.background = 'rgba(0,0,0,0.55)';
  root.style.zIndex = '999';

  const panel = document.createElement('div');
  panel.style.background = '#0f1115';
  panel.style.border = '1px solid #2b3246';
  panel.style.borderRadius = '14px';
  panel.style.padding = '16px';
  panel.style.minWidth = '320px';
  panel.style.maxWidth = '90%';
  panel.style.width = '560px';
  panel.style.boxShadow = '0 8px 28px rgba(0,0,0,0.6)';
  panel.addEventListener('click', (e) => e.stopPropagation());

  const title = document.createElement('h3');
  title.textContent = 'Contact';
  title.style.margin = '0 0 12px 0';

  const form = document.createElement('form');
  form.style.display = 'grid';
  form.style.gridTemplateColumns = '1fr 1fr';
  form.style.gap = '10px';

  const inputs = {};
  const labels = {};

  const fieldDefs = [
    { key: 'name', label: 'Name', create: () => createInput('text') },
    {
      key: 'type',
      label: 'Type',
      create: () => {
        const select = document.createElement('select');
        select.name = 'type';
        select.innerHTML = `
          <option value="vendor">Vendor</option>
          <option value="customer">Customer</option>
        `;
        styleInput(select);
        return select;
      },
    },
    { key: 'email', label: 'Email', create: () => createInput('email') },
    { key: 'phone', label: 'Phone', create: () => createInput('text') },
    {
      key: 'lead_time_days',
      label: 'Lead Time (days)',
      create: () => {
        const input = createInput('number');
        input.min = '0';
        return input;
      },
    },
    {
      key: 'material_specialty',
      label: 'Material Specialty',
      create: () => createInput('text'),
    },
  ];

  fieldDefs.forEach((def) => {
    const wrap = document.createElement('div');
    wrap.style.display = 'grid';
    wrap.style.gap = '6px';
    wrap.style.fontSize = '12px';
    wrap.dataset.field = def.key;

    const labelEl = document.createElement('label');
    labelEl.textContent = def.label;
    const inputId = `contact-${def.key}`;
    labelEl.htmlFor = inputId;

    const inputEl = def.create();
    inputEl.name = def.key;
    inputEl.id = inputId;

    inputs[def.key] = inputEl;
    labels[def.key] = labelEl;

    wrap.append(labelEl, inputEl);

    if (def.key === 'type') {
      form.insertBefore(wrap, form.children[1] || null);
    } else {
      form.appendChild(wrap);
    }
  });

  if (labels['lead_time_days']) labels['lead_time_days'].textContent = 'Lead Time (days)';
  if (labels['material_specialty']) labels['material_specialty'].textContent = 'Material Specialty';

  const notesWrap = document.createElement('div');
  notesWrap.style.display = 'grid';
  notesWrap.style.gap = '6px';
  notesWrap.style.gridColumn = '1 / span 2';
  notesWrap.style.fontSize = '12px';
  notesWrap.dataset.field = 'notes';

  const notesLabel = document.createElement('label');
  notesLabel.textContent = 'Notes';
  const notesId = 'contact-notes';
  notesLabel.htmlFor = notesId;

  const notes = document.createElement('textarea');
  notes.id = notesId;
  notes.name = 'notes';
  notes.rows = 3;
  styleInput(notes);

  inputs['notes'] = notes;
  labels['notes'] = notesLabel;

  notesWrap.append(notesLabel, notes);
  form.appendChild(notesWrap);

  const vendorFields = ['lead_time_days', 'material_specialty'];
  function updateVendorFields() {
    const isVendor = inputs['type'].value === 'vendor';
    vendorFields.forEach((field) => {
      const fieldWrap = inputs[field].closest('[data-field]');
      if (fieldWrap) {
        fieldWrap.style.display = isVendor ? 'grid' : 'none';
      }
    });
  }

  const actions = document.createElement('div');
  actions.style.display = 'flex';
  actions.style.justifyContent = 'flex-end';
  actions.style.gap = '10px';
  actions.style.marginTop = '10px';

  const cancel = document.createElement('button');
  cancel.type = 'button';
  cancel.textContent = 'Cancel';
  styleBtn(cancel);

  const save = document.createElement('button');
  save.type = 'submit';
  save.textContent = 'Save';
  styleBtn(save);

  actions.append(cancel, save);

  panel.append(title, form, actions);
  root.appendChild(panel);

  const api = {
    root,
    open(data) {
      for (const key in inputs) {
        const value = data[key] ?? '';
        inputs[key].value = value;
      }
      updateVendorFields();
      api._current = data;
      root.style.display = 'flex';
      setTimeout(() => document.addEventListener('keydown', escCloser));
    },
    close() {
      root.style.display = 'none';
      document.removeEventListener('keydown', escCloser);
    },
    onSubmit: null,
  };

  inputs['type'].addEventListener('change', updateVendorFields);

  Object.values(inputs).forEach((inputEl) => {
    inputEl.style.outline = 'none';
    inputEl.addEventListener('focus', () => {
      inputEl.style.borderColor = '#4a5568';
    });
    inputEl.addEventListener('blur', () => {
      inputEl.style.borderColor = '#2b3246';
    });
  });

  function escCloser(e) {
    if (e.key === 'Escape') api.close();
  }

  root.addEventListener('click', () => api.close());
  cancel.addEventListener('click', () => api.close());

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const model = { id: api._current?.id ?? null };
    for (const key in inputs) {
      let value = inputs[key].value;
      if (key === 'lead_time_days' && value !== '') {
        value = Number(value);
      }
      if (vendorFields.includes(key) && inputs['type'].value !== 'vendor') {
        value = null;
      }
      model[key] = value === '' ? null : value;
    }
    if (typeof api.onSubmit === 'function') {
      await api.onSubmit(model);
    }
  });

  return api;

  function createInput(type) {
    const input = document.createElement('input');
    input.type = type;
    styleInput(input);
    return input;
  }
}

function styleInput(el) {
  el.style.background = '#111318';
  el.style.color = '#e5e7eb';
  el.style.border = '1px solid #2b3246';
  el.style.borderRadius = '10px';
  el.style.padding = '8px';
  el.style.width = '100%';
  el.style.boxSizing = 'border-box';
}

function openModal(modal, model) {
  modal.open(model);
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[c]);
}
