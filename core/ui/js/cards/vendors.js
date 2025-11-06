import { apiGet, apiPost, ensureToken } from '../api.js';

const LS_KEY = 'contacts.customers.v1';

async function vendorExistsByName(name) {
  const target = (name || '').trim().toLowerCase();
  if (!target) return false;
  const normalize = (value) => String(value || '').trim().toLowerCase();
  try {
    const list = await apiGet('/app/vendors');
    const arr = Array.isArray(list) ? list : Array.isArray(list?.items) ? list.items : [];
    return arr.some((vendor) => normalize(vendor?.name) === target);
  } catch {
    try {
      const fallback = await apiGet('/app/vendors/list');
      const arr = Array.isArray(fallback) ? fallback : [];
      return arr.some((vendor) => normalize(vendor?.name) === target);
    } catch {
      return false;
    }
  }
}

export async function mountVendors(container) {
  // --- BEGIN SPEC-1 BODY ---
  container.innerHTML = '';
  container.style.background = '#0f1115';
  container.style.color = '#e5e7eb';
  container.style.padding = '16px';
  container.style.borderRadius = '12px';

  const header = document.createElement('div');
  header.style.display = 'flex';
  header.style.alignItems = 'center';
  header.style.justifyContent = 'space-between';
  header.style.gap = '12px';
  header.style.marginBottom = '12px';

  const title = document.createElement('h2');
  title.textContent = 'Contacts';
  title.style.margin = '0';

  const addContactBtn = document.createElement('button');
  addContactBtn.type = 'button';
  addContactBtn.textContent = 'Add Contact';
  addContactBtn.dataset.action = 'open-contacts-modal';
  styleBtn(addContactBtn);

  header.append(title, addContactBtn);

  const table = document.createElement('table');
  table.dataset.role = 'contacts-table';
  table.className = 'table';
  table.style.width = '100%';
  table.style.borderCollapse = 'separate';
  table.style.borderSpacing = '0';
  table.style.background = '#111318';
  table.style.borderRadius = '10px';
  table.style.overflow = 'hidden';
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Type</th>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Contact</th>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Actions</th>
    </tr>`;
  const tbody = document.createElement('tbody');
  table.append(thead, tbody);

  container.append(header, table);

  const tbl = document.querySelector('[data-role="contacts-table"]');
  const tbodyEl = tbl?.querySelector('tbody');
  const drawer = document.querySelector('[data-role="contacts-drawer"]');
  const drawerBackdrop = drawer?.querySelector('.drawer-backdrop');
  const drawerCloseBtn = drawer?.querySelector('.drawer-header [data-action="close-contacts-drawer"]');
  const linkedList = drawer?.querySelector('[data-role="linked-items"]');
  const field = (name) => drawer?.querySelector(`[data-field="${name}"]`);

  function openDrawer() {
    if (!drawer) return;
    drawer.classList.remove('hidden');
    drawer.setAttribute('aria-hidden', 'false');
  }
  function closeDrawer() {
    if (!drawer) return;
    drawer.classList.add('hidden');
    drawer.setAttribute('aria-hidden', 'true');
    if (linkedList) linkedList.innerHTML = '';
  }

  if (drawer && !drawer.dataset.contactsDrawerBound) {
    drawerBackdrop?.addEventListener('click', closeDrawer);
    drawerCloseBtn?.addEventListener('click', closeDrawer);
    drawer.dataset.contactsDrawerBound = '1';
  }
  const bodyEl = document.body;
  if (drawer && bodyEl && !bodyEl.dataset.contactsDrawerEscBound) {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !drawer.classList.contains('hidden')) {
        closeDrawer();
      }
    });
    bodyEl.dataset.contactsDrawerEscBound = '1';
  }

  async function loadContactsList() {
    try {
      const list = await apiGet('/app/contacts');
      if (Array.isArray(list)) return list;
    } catch (e) {
      const s = e?.status || e?.response?.status;
      if (s !== 404 && s !== 405) console.warn('GET /app/contacts failed', e);
    }

    let vendors = [];
    try {
      vendors = await apiGet('/app/vendors');
    } catch (err) {
      console.warn('GET /app/vendors fallback failed', err);
      vendors = [];
    }
    vendors = Array.isArray(vendors)
      ? vendors.map((v) => ({
          id: v.id,
          type: 'vendor',
          name: v.name,
          email: v.email,
          material: v.material,
          lead_time_days: v.lead_time_days,
          notes: v.notes,
        }))
      : [];

    let customers = [];
    try {
      customers = JSON.parse(localStorage.getItem(LS_KEY) || '[]');
    } catch {
      customers = [];
    }
    customers = Array.isArray(customers)
      ? customers.map((c, i) => ({
          id: c.id || `local:${i}`,
          type: 'customer',
          name: c.name,
          email: c.email,
          notes: c.notes,
        }))
      : [];

    return [...vendors, ...customers];
  }

  async function openContactDrawer(contact) {
    if (!drawer) return;
    const set = (k, v) => {
      const el = field(k);
      if (el) el.textContent = v ?? '';
    };

    const typeLabel = (contact.type || '').toString();
    set('type', typeLabel ? typeLabel.replace(/^./, (m) => m.toUpperCase()) : '');
    set('name', contact.name || '');
    set('email', contact.email || '');
    set('material', contact.type === 'vendor' ? contact.material || '' : '');
    set('lead_time_days', contact.lead_time_days != null ? String(contact.lead_time_days) : '');
    set('notes', contact.notes || '');

    drawer.querySelectorAll('.vendor-only').forEach((el) => {
      el.style.display = contact.type === 'vendor' ? '' : 'none';
    });

    if (linkedList) {
      linkedList.innerHTML = '';
      if (contact.type === 'vendor' && contact.id != null && String(contact.id)) {
        const loading = document.createElement('li');
        loading.textContent = 'Loading linked items…';
        linkedList.appendChild(loading);
        try {
          const items = await apiGet(`/app/items?vendor_id=${encodeURIComponent(contact.id)}`);
          linkedList.innerHTML = '';
          const arr = Array.isArray(items) ? items : [];
          arr.forEach((item) => {
            const li = document.createElement('li');
            const name = item.name || '(unnamed)';
            const qty = item.qty != null ? item.qty : 0;
            li.textContent = `${name} — qty: ${qty}`;
            linkedList.appendChild(li);
          });
          if (!linkedList.children.length) {
            const li = document.createElement('li');
            li.textContent = 'No linked items.';
            linkedList.appendChild(li);
          }
        } catch (err) {
          linkedList.innerHTML = '';
          const li = document.createElement('li');
          li.textContent = 'Could not load linked items.';
          linkedList.appendChild(li);
          console.warn('GET /app/items vendor linked items failed', err);
        }
      } else {
        const li = document.createElement('li');
        li.textContent = 'Linked items available for vendors only.';
        linkedList.appendChild(li);
      }
    }

    openDrawer();
  }

  async function renderContactsTable() {
    if (!tbodyEl) return;
    const list = await loadContactsList();
    tbodyEl.innerHTML = '';

    if (!list.length) {
      const emptyRow = document.createElement('tr');
      const emptyCell = document.createElement('td');
      emptyCell.colSpan = 3;
      emptyCell.textContent = 'No contacts yet.';
      emptyCell.style.padding = '12px 16px';
      emptyCell.style.color = '#9ca3af';
      emptyRow.appendChild(emptyCell);
      tbodyEl.appendChild(emptyRow);
      return;
    }

    for (const c of list) {
      const tr = document.createElement('tr');
      tr.dataset.contactId = String(c.id ?? '');
      tr.dataset.contactType = String(c.type ?? '');

      const typeCell = document.createElement('td');
      typeCell.style.padding = '10px';
      typeCell.style.borderTop = '1px solid #222733';
      typeCell.textContent = (c.type || '').toString().replace(/^./, (m) => m.toUpperCase());

      const nameCell = document.createElement('td');
      nameCell.style.padding = '10px';
      nameCell.style.borderTop = '1px solid #222733';
      nameCell.textContent = (c.name || '').toString();

      const actionsCell = document.createElement('td');
      actionsCell.style.padding = '10px';
      actionsCell.style.borderTop = '1px solid #222733';

      const actionsWrap = document.createElement('div');
      actionsWrap.style.display = 'flex';
      actionsWrap.style.gap = '8px';

      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.dataset.action = 'contact-edit';
      editBtn.textContent = 'Edit';
      styleBtn(editBtn);

      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.dataset.action = 'contact-delete';
      delBtn.textContent = 'Delete';
      delBtn.disabled = true;
      styleBtn(delBtn);
      delBtn.style.cursor = 'not-allowed';
      delBtn.style.opacity = '0.5';
      delBtn.onmouseenter = null;
      delBtn.onmouseleave = null;

      actionsWrap.append(editBtn, delBtn);
      actionsCell.append(actionsWrap);

      tr.append(typeCell, nameCell, actionsCell);

      tr.addEventListener('click', (event) => {
        if (event.target instanceof HTMLElement && event.target.closest('button')) {
          return;
        }
        openContactDrawer(c);
      });

      editBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        openContactDrawer(c);
      });

      tbodyEl.appendChild(tr);
    }
  }

  const contactsModal = document.querySelector('[data-role="contacts-modal"]');
  const contactsForm = contactsModal?.querySelector('[data-role="contacts-form"]');
  const contactsSaveBtn = contactsModal?.querySelector('[data-role="contacts-save"]');
  const contactsOpenBtn = document.querySelector('[data-action="open-contacts-modal"]');
  const contactsCloseButtons = contactsModal ? Array.from(contactsModal.querySelectorAll('[data-action="close-contacts-modal"]')) : [];
  const vendorOnlyWrap = contactsModal?.querySelector('[data-visible-when="vendor"]');

  function updateVendorOnly() {
    if (!vendorOnlyWrap || !contactsForm) return;
    const t = String(contactsForm.elements.type.value || '').toLowerCase();
    vendorOnlyWrap.style.display = t === 'vendor' ? '' : 'none';
  }

  function setContactsBusy(busy) {
    if (!contactsSaveBtn) return;
    if (!contactsSaveBtn.dataset._orig) {
      contactsSaveBtn.dataset._orig = contactsSaveBtn.textContent || 'Save';
    }
    contactsSaveBtn.disabled = !!busy;
    contactsSaveBtn.textContent = busy ? 'Saving…' : contactsSaveBtn.dataset._orig;
  }

  function openContactsModal(preset = {}) {
    if (!contactsModal || !contactsForm) return;
    contactsForm.reset();
    if (preset.name) contactsForm.elements.name.value = preset.name;
    const typeField = contactsForm.elements.type;
    const presetType = (preset.type || '').toLowerCase();
    if (typeField) {
      typeField.value = presetType || '';
    }
    if (preset.email) contactsForm.elements.email.value = preset.email;
    if (preset.material) contactsForm.elements.material.value = preset.material;
    if (preset.lead_time_days != null) contactsForm.elements.lead_time_days.value = preset.lead_time_days;
    if (preset.notes) contactsForm.elements.notes.value = preset.notes;
    updateVendorOnly();
    contactsModal.classList.remove('hidden');
    contactsModal.classList.add('open');
    contactsForm.elements.name?.focus();
  }

  function closeContactsModal() {
    if (!contactsModal) return;
    contactsModal.classList.add('hidden');
    contactsModal.classList.remove('open');
  }

  contactsOpenBtn?.addEventListener('click', () => openContactsModal());

  if (contactsModal && !contactsModal.dataset.contactsOverlayBound) {
    contactsModal.addEventListener('click', (event) => {
      if (event.target === contactsModal || event.target.classList.contains('modal-backdrop')) {
        closeContactsModal();
      }
    });
    contactsModal.dataset.contactsOverlayBound = '1';
  }

  contactsCloseButtons.forEach((btn) => {
    if (!btn.dataset.contactsCloseBound) {
      btn.addEventListener('click', () => closeContactsModal());
      btn.dataset.contactsCloseBound = '1';
    }
  });

  if (contactsModal && !contactsModal.dataset.contactsEscBound) {
    const escHandler = (event) => {
      if (event.key === 'Escape' && !contactsModal.classList.contains('hidden')) {
        closeContactsModal();
      }
    };
    document.addEventListener('keydown', escHandler);
    contactsModal.dataset.contactsEscBound = '1';
  }

  if (contactsForm && !contactsForm.dataset.contactsTypeBound) {
    contactsForm.elements.type?.addEventListener('change', updateVendorOnly);
    contactsForm.dataset.contactsTypeBound = '1';
  }

  if (contactsForm) {
    updateVendorOnly();
  }

  if (contactsForm && !contactsForm.dataset.contactsSubmitBound) {
    contactsForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (contactsSaveBtn?.disabled) return;

      const fd = new FormData(contactsForm);
      const name = String(fd.get('name') || '').trim();
      let type = String(fd.get('type') || '').trim().toLowerCase();
      const email = String(fd.get('email') || '').trim();
      const material = String(fd.get('material') || '').trim();
      const leadRaw = String(fd.get('lead_time_days') || '').trim();
      const notes = String(fd.get('notes') || '').trim();

      if (!name) { alert('Name required'); return; }
      if (type !== 'vendor' && type !== 'customer') { alert('Type required'); return; }

      let lead_time_days = null;
      if (leadRaw) {
        const n = parseInt(leadRaw, 10);
        if (Number.isNaN(n)) { alert('Lead time must be a number'); return; }
        lead_time_days = n;
      }

      const payload = {
        name,
        type,
        ...(email ? { email } : {}),
        ...(type === 'vendor' && material ? { material } : {}),
        ...(lead_time_days != null ? { lead_time_days } : {}),
        ...(notes ? { notes } : {}),
      };

      let vendorCreated = false;

      try {
        setContactsBusy(true);
        await ensureToken();

        if (type === 'vendor') {
          if (await vendorExistsByName(name)) {
            alert('Vendor already exists');
            return;
          }
          const vendorPayload = {
            name,
            ...(email ? { email } : {}),
            ...(material ? { material } : {}),
            ...(lead_time_days != null ? { lead_time_days } : {}),
            ...(notes ? { notes } : {}),
          };
          try {
            await apiPost('/app/vendors', vendorPayload);
            vendorCreated = true;
            document.dispatchEvent(new CustomEvent('vendors:changed', { bubbles: true }));
          } catch (vendorErr) {
            const vs = vendorErr?.status || vendorErr?.response?.status;
            if (vs !== 404 && vs !== 405) {
              throw vendorErr;
            }
          }
        }

        try {
          await apiPost('/app/contacts', payload);
          closeContactsModal();
          await renderContactsTable();
          document.dispatchEvent(new CustomEvent('contacts:changed', { bubbles: true }));
        } catch (err) {
          const status = err?.status || err?.response?.status;
          if ((status === 404 || status === 405) && vendorCreated) {
            closeContactsModal();
            await renderContactsTable();
            document.dispatchEvent(new CustomEvent('contacts:changed', { bubbles: true }));
            return;
          }
          throw err;
        }
      } catch (err) {
        const status = err?.status || err?.response?.status;
        if (status === 404 || status === 405) {
          alert('Contacts endpoint is not available yet (HTTP ' + status + '). Please add /app/contacts on the backend.');
        } else {
          alert('Could not save contact.');
        }
        console.error('POST /app/contacts failed', err);
      } finally {
        setContactsBusy(false);
      }
    });
    contactsForm.dataset.contactsSubmitBound = '1';
  }

  if (container.__contactsRefreshHandler) {
    document.removeEventListener('contacts:changed', container.__contactsRefreshHandler);
    document.removeEventListener('vendors:changed', container.__contactsRefreshHandler);
    document.removeEventListener('customers:changed', container.__contactsRefreshHandler);
  }

  const refreshContactsTable = () => {
    renderContactsTable().catch((err) => console.error('renderContactsTable failed', err));
  };

  container.__contactsRefreshHandler = refreshContactsTable;

  document.addEventListener('contacts:changed', refreshContactsTable);
  document.addEventListener('vendors:changed', refreshContactsTable);
  document.addEventListener('customers:changed', refreshContactsTable);

  closeDrawer();

  await renderContactsTable();
  // --- END SPEC-1 BODY ---
}
function styleBtn(btn){
  btn.style.background = '#23293a';
  btn.style.color = '#e5e7eb';
  btn.style.border = '1px solid #2b3246';
  btn.style.padding = '6px 10px';
  btn.style.borderRadius = '10px';
  btn.style.cursor = 'pointer';
  btn.onmouseenter = () => btn.style.background = '#2a3146';
  btn.onmouseleave = () => btn.style.background = '#23293a';
}
export default mountVendors;
