import { apiGet, apiPost, apiDelete, apiPut, ensureToken } from '../api.js';

const LS_KEY = 'contacts.customers.v1';

function loadCustomers() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveCustomers(arr) {
  localStorage.setItem(LS_KEY, JSON.stringify(arr ?? []));
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

const STYLE_ID = 'contacts-card-styles';

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = `
    .contacts-card { color: #e6e6e6; background:#1e1f22; border-radius:12px; padding:20px; box-shadow:0 18px 40px rgba(0,0,0,0.45); }
    .contacts-header { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:12px; margin-bottom:16px; }
    .contacts-header h2 { margin:0; font-size:20px; color:#7f9cff; }
    .contacts-toggle { display:inline-flex; border:1px solid #2d3036; border-radius:12px; overflow:hidden; }
    .contacts-toggle button { background:#2a2c30; color:#c7c7c7; border:none; padding:8px 16px; font-size:13px; cursor:pointer; transition:background 0.15s ease; }
    .contacts-toggle button[data-active="true"] { background:#3a6cff; color:#fff; font-weight:600; }
    .contacts-toggle button:not([data-active="true"]):hover { background:#32353b; }
    .contacts-new-btn { background:#3a6cff; border:none; color:#fff; border-radius:12px; padding:9px 18px; font-size:13px; font-weight:600; cursor:pointer; box-shadow:0 6px 18px rgba(58,108,255,0.35); }
    .contacts-new-btn:hover { background:#5681ff; }
    .contacts-table-wrap { background:#24262b; border-radius:12px; overflow:hidden; border:1px solid #2d3036; }
    .contacts-table { width:100%; border-collapse:collapse; font-size:13px; }
    .contacts-table thead { background:#2b2d31; text-transform:uppercase; letter-spacing:0.05em; font-size:12px; }
    .contacts-table th, .contacts-table td { padding:10px 12px; text-align:left; border-bottom:1px solid #2d3036; }
    .contacts-table tbody tr:hover { background:#23262b; }
    .contact-type { display:inline-flex; align-items:center; justify-content:center; padding:4px 10px; border-radius:999px; font-size:11px; font-weight:600; letter-spacing:0.03em; text-transform:uppercase; }
    .contact-type.vendor { background:rgba(58,108,255,0.15); color:#8ea9ff; border:1px solid rgba(58,108,255,0.35); }
    .contact-type.customer { background:rgba(0,200,160,0.12); color:#7ff0d2; border:1px solid rgba(0,200,160,0.35); }
    .contacts-actions { display:flex; gap:8px; }
    .contacts-actions button { border:none; border-radius:10px; padding:6px 12px; font-size:12px; cursor:pointer; transition:opacity 0.15s ease; }
    .contacts-actions button:hover { opacity:0.85; }
    .contacts-actions .edit { background:#3a6cff; color:#fff; }
    .contacts-actions .delete { background:#ff5f56; color:#fff; }
    .contacts-status { margin-top:12px; font-size:12px; color:#9da3b0; }
    .contacts-status[data-error="true"] { color:#ff9b8f; }
    .contacts-empty { padding:18px; text-align:center; font-size:13px; color:#9da3b0; }
    .contacts-modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.65); display:flex; align-items:center; justify-content:center; z-index:9999; }
    .contacts-modal { width:460px; max-width:90vw; background:#1f2226; border-radius:14px; padding:24px; box-shadow:0 28px 80px rgba(0,0,0,0.55); display:flex; flex-direction:column; gap:16px; }
    .contacts-modal h3 { margin:0; font-size:18px; color:#9bb4ff; }
    .contacts-modal form { display:flex; flex-direction:column; gap:12px; }
    .contacts-modal label { display:flex; flex-direction:column; font-size:12px; gap:6px; color:#c7c7c7; }
    .contacts-modal input, .contacts-modal textarea { background:#2a2c30; border:1px solid #353840; color:#e6e6e6; border-radius:12px; padding:10px; font:inherit; resize:vertical; min-height:36px; }
    .contacts-modal textarea { min-height:72px; }
    .contacts-modal footer { display:flex; justify-content:flex-end; gap:10px; }
    .contacts-modal footer button { border:none; border-radius:12px; padding:8px 18px; font-size:13px; cursor:pointer; }
    .contacts-modal footer .secondary { background:#2d3036; color:#c7c7c7; }
    .contacts-modal footer .primary { background:#3a6cff; color:#fff; }
    .contacts-modal footer button:hover { opacity:0.9; }
  `;
  document.head.appendChild(style);
}

function createToggleButton(label, value, state, onChange) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.textContent = label;
  btn.dataset.value = value;
  btn.dataset.active = state.mode === value ? 'true' : 'false';
  btn.addEventListener('click', () => {
    if (state.mode === value) return;
    state.mode = value;
    onChange();
  });
  return btn;
}

function customerId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `c-${crypto.randomUUID()}`;
  }
  return `c-${Date.now().toString(36)}${Math.random().toString(16).slice(2)}`;
}

export async function mountVendors(container) {
  ensureStyles();

  const state = {
    mode: 'vendor',
    vendors: [],
    customers: loadCustomers(),
    vendorMutations: false,
  };

  container.classList.add('contacts-card');
  container.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'contacts-header';

  const title = document.createElement('h2');
  title.textContent = 'Contacts';

  const toggle = document.createElement('div');
  toggle.className = 'contacts-toggle';

  const newButton = document.createElement('button');
  newButton.className = 'contacts-new-btn';

  const tableWrap = document.createElement('div');
  tableWrap.className = 'contacts-table-wrap';
  const table = document.createElement('table');
  table.className = 'contacts-table';
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th>Type</th>
      <th>Name</th>
      <th>Contact</th>
      <th>Email</th>
      <th>Phone</th>
      <th>Notes</th>
      <th>Actions</th>
    </tr>
  `;
  const tbody = document.createElement('tbody');
  table.append(thead, tbody);
  tableWrap.appendChild(table);

  const status = document.createElement('div');
  status.className = 'contacts-status';

  header.append(title, toggle, newButton);
  container.append(header, tableWrap, status);

  function updateStatus(message, isError = false) {
    status.innerHTML = esc(message);
    if (isError) {
      status.dataset.error = 'true';
    } else {
      delete status.dataset.error;
    }
  }

  function updateToggle() {
    toggle.innerHTML = '';
    const vendorBtn = createToggleButton('Vendor', 'vendor', state, () => {
      updateToggle();
      updateNewButton();
    });
    const customerBtn = createToggleButton('Customer', 'customer', state, () => {
      updateToggle();
      updateNewButton();
    });
    toggle.append(vendorBtn, customerBtn);
  }

  function updateNewButton() {
    newButton.textContent = state.mode === 'vendor' ? 'New Vendor' : 'New Customer';
  }

  function persistCustomers() {
    saveCustomers(state.customers);
  }

  function dispatchRefreshEvents() {
    document.dispatchEvent(new CustomEvent('vendors:refresh'));
    document.dispatchEvent(new CustomEvent('items:refresh'));
  }

  function removeModal(overlay, escHandler) {
    if (escHandler) {
      window.removeEventListener('keydown', escHandler);
    }
    overlay.remove();
  }

  function openModal(mode, existing) {
    const overlay = document.createElement('div');
    overlay.className = 'contacts-modal-overlay';
    const modal = document.createElement('div');
    modal.className = 'contacts-modal';
    overlay.appendChild(modal);

    const heading = document.createElement('h3');
    heading.textContent = existing ? `Edit ${mode === 'vendor' ? 'Vendor' : 'Customer'}` : `New ${mode === 'vendor' ? 'Vendor' : 'Customer'}`;

    const form = document.createElement('form');
    const nameLabel = document.createElement('label');
    nameLabel.innerHTML = `Name <input required name="name" maxlength="200" autocomplete="off">`;
    const nameInput = nameLabel.querySelector('input');

    const contactLabel = document.createElement('label');
    contactLabel.innerHTML = `Contact <input name="contact" maxlength="200" autocomplete="off">`;
    const contactInput = contactLabel.querySelector('input');

    const emailLabel = document.createElement('label');
    emailLabel.innerHTML = `Email <input name="email" type="email" maxlength="200" autocomplete="off">`;
    const emailInput = emailLabel.querySelector('input');

    const phoneLabel = document.createElement('label');
    phoneLabel.innerHTML = `Phone <input name="phone" maxlength="40" autocomplete="off">`;
    const phoneInput = phoneLabel.querySelector('input');

    const notesLabel = document.createElement('label');
    notesLabel.innerHTML = `Notes <textarea name="notes" maxlength="500"></textarea>`;
    const notesInput = notesLabel.querySelector('textarea');

    const footer = document.createElement('footer');
    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'secondary';
    cancelBtn.textContent = 'Cancel';
    const submitBtn = document.createElement('button');
    submitBtn.type = 'submit';
    submitBtn.className = 'primary';
    submitBtn.textContent = existing ? 'Save' : 'Create';
    footer.append(cancelBtn, submitBtn);

    form.append(nameLabel, contactLabel);
    if (mode === 'customer') {
      form.append(emailLabel, phoneLabel, notesLabel);
    }
    form.append(footer);

    if (existing) {
      nameInput.value = existing.name ?? '';
      contactInput.value = existing.contact ?? '';
      if (mode === 'customer') {
        emailInput.value = existing.email ?? '';
        phoneInput.value = existing.phone ?? '';
        notesInput.value = existing.notes ?? '';
      }
    }

    cancelBtn.addEventListener('click', () => removeModal(overlay, escHandler));
    overlay.addEventListener('click', event => {
      if (event.target === overlay) {
        removeModal(overlay, escHandler);
      }
    });

    const escHandler = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        removeModal(overlay, escHandler);
      }
    };
    window.addEventListener('keydown', escHandler);

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const name = nameInput.value.trim();
      if (!name) {
        nameInput.focus();
        return;
      }

      try {
        if (mode === 'vendor') {
          await ensureToken();
          if (existing && existing.kind === 'vendor') {
            const payload = { name };
            const contact = contactInput.value.trim();
            if (contact) {
              payload.contact = contact;
            }
            await apiPut(`/app/vendors/${existing.id}`, payload);
          } else {
            try {
              const payload = { name };
              const contact = contactInput.value.trim();
              if (contact) {
                payload.contact = contact;
              }
              await apiPost('/app/vendors', payload);
            } catch (error) {
              if (error?.status === 404) {
                alert('Vendor endpoint is unavailable (404).');
              } else {
                alert(`Vendor save failed: ${error?.message || error}`);
              }
              throw error;
            }
          }
          dispatchRefreshEvents();
          await refreshVendors();
        } else {
          const record = {
            id: existing?.id ?? customerId(),
            kind: 'customer',
            name,
            contact: contactInput.value.trim() || '',
            email: emailInput.value.trim() || '',
            phone: phoneInput.value.trim() || '',
            notes: notesInput.value.trim() || '',
          };
          if (existing) {
            const idx = state.customers.findIndex(entry => entry.id === existing.id);
            if (idx !== -1) {
              state.customers[idx] = { ...record };
            }
          } else {
            state.customers.unshift(record);
          }
          persistCustomers();
          renderRows();
          updateStatus(`Saved customer ${record.name}`);
        }
      } catch (error) {
        updateStatus(error?.message || 'Save failed', true);
        return;
      }

      removeModal(overlay, escHandler);
    });

    modal.append(heading, form);
    document.body.appendChild(overlay);
    nameInput.focus();
  }

  function renderRows() {
    tbody.innerHTML = '';
    const vendorRows = (state.vendors || []).map(v => ({
      kind: 'vendor',
      id: v.id,
      name: v.name,
      contact: v.contact ?? '',
    }));
    const customerRows = (state.customers || []).map(c => ({ ...c, kind: 'customer' }));
    const combined = [...vendorRows, ...customerRows];

    if (!combined.length) {
      const empty = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 7;
      td.className = 'contacts-empty';
      td.textContent = 'No contacts yet. Use the New button to add one.';
      empty.appendChild(td);
      tbody.appendChild(empty);
      return;
    }

    combined.forEach(entry => {
      const row = document.createElement('tr');

      const typeCell = document.createElement('td');
      const badge = document.createElement('span');
      badge.className = `contact-type ${entry.kind}`;
      badge.textContent = entry.kind === 'vendor' ? 'Vendor' : 'Customer';
      typeCell.appendChild(badge);

      const nameCell = document.createElement('td');
      nameCell.textContent = entry.name || '—';

      const contactCell = document.createElement('td');
      contactCell.textContent = entry.contact ? entry.contact : '—';

      const emailCell = document.createElement('td');
      emailCell.textContent = entry.kind === 'customer' ? (entry.email || '—') : '—';

      const phoneCell = document.createElement('td');
      phoneCell.textContent = entry.kind === 'customer' ? (entry.phone || '—') : '—';

      const notesCell = document.createElement('td');
      notesCell.textContent = entry.kind === 'customer' ? (entry.notes || '—') : '—';

      const actionsCell = document.createElement('td');
      const actions = document.createElement('div');
      actions.className = 'contacts-actions';

      if (entry.kind === 'vendor' && state.vendorMutations) {
        const editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.className = 'edit';
        editBtn.textContent = 'Edit';
        editBtn.addEventListener('click', () => openModal('vendor', entry));

        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.className = 'delete';
        deleteBtn.textContent = 'Delete';
        deleteBtn.addEventListener('click', async () => {
          if (!window.confirm(`Delete vendor "${entry.name}"?`)) {
            return;
          }
          try {
            await ensureToken();
            await apiDelete(`/app/vendors/${entry.id}`);
            dispatchRefreshEvents();
            await refreshVendors();
          } catch (error) {
            updateStatus(error?.message || 'Delete failed', true);
          }
        });
        actions.append(editBtn, deleteBtn);
      } else if (entry.kind === 'customer') {
        const editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.className = 'edit';
        editBtn.textContent = 'Edit';
        editBtn.addEventListener('click', () => openModal('customer', entry));

        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.className = 'delete';
        deleteBtn.textContent = 'Delete';
        deleteBtn.addEventListener('click', () => {
          if (!window.confirm(`Delete customer "${entry.name}"?`)) {
            return;
          }
          state.customers = state.customers.filter(item => item.id !== entry.id);
          persistCustomers();
          renderRows();
          updateStatus(`Deleted customer ${entry.name}`);
        });
        actions.append(editBtn, deleteBtn);
      }

      actionsCell.appendChild(actions);

      row.append(typeCell, nameCell, contactCell, emailCell, phoneCell, notesCell, actionsCell);
      tbody.appendChild(row);
    });
  }

  async function refreshVendors() {
    try {
      updateStatus('Loading contacts…');
      const response = await apiGet('/app/vendors');
      state.vendors = Array.isArray(response) ? response : [];
      renderRows();
      updateStatus(
        `Loaded ${state.vendors.length} vendor${state.vendors.length === 1 ? '' : 's'} and ${state.customers.length} customer${state.customers.length === 1 ? '' : 's'}.`,
      );
    } catch (error) {
      state.vendors = [];
      renderRows();
      updateStatus(error?.message || 'Failed to load vendors', true);
    }
  }

  updateToggle();
  updateNewButton();
  renderRows();

  newButton.addEventListener('click', () => openModal(state.mode, null));

  await refreshVendors();
}

export default mountVendors;
