import { apiGet, apiPost, apiDelete, ensureToken } from '../api.js';

const LS_KEY = 'contacts.customers.v1';
const loadCustomers = () => { try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]'); } catch { return []; } };
const saveCustomers = (arr) => localStorage.setItem(LS_KEY, JSON.stringify(arr));

export async function mountVendors(container) {
  // --- BEGIN SPEC-1 BODY ---
  container.innerHTML = '';
  container.style.background = '#0f1115';
  container.style.color = '#e5e7eb';
  container.style.padding = '16px';
  container.style.borderRadius = '12px';

  let mode = 'vendor'; // 'vendor' | 'customer'

  // Header with toggle + Add Contact button
  const header = document.createElement('div');
  header.style.display = 'flex';
  header.style.alignItems = 'center';
  header.style.gap = '10px';
  header.style.marginBottom = '12px';

  const title = document.createElement('h2');
  title.textContent = 'Contacts';
  title.style.margin = '0';

  const toggle = document.createElement('div');
  toggle.style.display = 'inline-flex';
  toggle.style.border = '1px solid #2b3246';
  toggle.style.borderRadius = '10px';
  function mkToggleBtn(txt, val) {
    const b = document.createElement('button');
    b.textContent = txt;
    b.style.padding = '6px 10px';
    b.style.border = '0';
    b.style.cursor = 'pointer';
    b.style.background = val === mode ? '#23293a' : 'transparent';
    b.style.color = '#e5e7eb';
    b.onclick = () => { mode = val; renderToggle(); };
    return b;
  }
  function renderToggle() {
    toggle.innerHTML = '';
    toggle.append(mkToggleBtn('Vendor','vendor'), mkToggleBtn('Customer','customer'));
    loadAndRender();
  }
  renderToggle();

  const addContactBtn = document.createElement('button');
  addContactBtn.type = 'button';
  addContactBtn.textContent = 'Add Contact';
  addContactBtn.dataset.action = 'open-contacts-modal';
  styleBtn(addContactBtn);

  header.append(title, toggle, addContactBtn);

  // Table
  const table = document.createElement('table');
  table.style.width = '100%';
  table.style.borderCollapse = 'separate';
  table.style.borderSpacing = '0';
  table.style.background = '#111318';
  table.style.borderRadius = '10px';
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Name</th>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Type</th>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Contact</th>
      <th style="text-align:left;padding:10px;background:#1a1f2b">Actions</th>
    </tr>`;
  const tbody = document.createElement('tbody');
  table.append(thead, tbody);

  container.append(header, table);

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

  function disableLegacyEditButton(btn) {
    if (!btn) return null;
    const clone = btn.cloneNode(true);
    clone.disabled = true;
    clone.dataset.action = 'contact-edit';
    clone.title = 'Edit coming soon';
    btn.replaceWith(clone);
    return clone;
  }

  function openContactsModal(preset = {}) {
    if (!contactsModal || !contactsForm) return;
    contactsForm.reset();
    if (preset.name) contactsForm.elements.name.value = preset.name;
    const typeField = contactsForm.elements.type;
    const presetType = (preset.type || mode || '').toLowerCase();
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

  contactsOpenBtn?.addEventListener('click', () => openContactsModal({ type: mode }));

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

      try {
        setContactsBusy(true);
        await ensureToken();
        await apiPost('/app/contacts', payload);
        closeContactsModal();
        await loadAndRender();
        document.dispatchEvent(new CustomEvent('contacts:changed', { bubbles: true }));
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

  async function loadAndRender() {
    // vendors from server
    let vendors = [];
    try {
      vendors = await apiGet('/app/vendors'); // [{id,name}]
    } catch {
      vendors = [];
    }
    // customers from local storage
    const customers = loadCustomers(); // [{id,name,contact,email,phone,notes}]
    renderRows(vendors, customers);
  }

  function renderRows(vendors, customers) {
    tbody.innerHTML = '';
    const rows = [
      ...vendors.map(v => ({ id: v.id, name: v.name, contact: v.contact || '', _type: 'Vendor', _local: false })),
      ...customers.map(c => ({ id: c.id, name: c.name, contact: c.contact || '', _type: 'Customer', _local: true, _full: c }))
    ];
    for (const r of rows) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="padding:10px;border-top:1px solid #222733">${esc(r.name)}</td>
        <td style="padding:10px;border-top:1px solid #222733">${r._type}</td>
        <td style="padding:10px;border-top:1px solid #222733">${esc(r.contact || '')}</td>
        <td style="padding:10px;border-top:1px solid #222733">
          <div style="display:flex;gap:8px;">
            <button class="edit">Edit</button>
            <button class="del">Delete</button>
          </div>
        </td>`;
      let editBtn = tr.querySelector('.edit');
      if (editBtn) {
        editBtn = disableLegacyEditButton(editBtn);
        if (editBtn) {
          styleBtn(editBtn);
          editBtn.style.cursor = 'not-allowed';
          editBtn.onmouseenter = null;
          editBtn.onmouseleave = null;
        }
      }

      const delBtn = tr.querySelector('.del');
      if (delBtn) {
        styleBtn(delBtn);
        delBtn.onclick = async () => {
          if (!confirm(`Delete ${r.name}?`)) return;
          if (r._local) {
            const list = loadCustomers().filter(x => x.id !== r.id);
            saveCustomers(list);
            renderRows(vendors, list);
          } else {
            // Only attempt if DELETE exists; ignore 404
            try {
              await ensureToken();
              await apiDelete(`/app/vendors/${r.id}`);
            } catch {}
            await loadAndRender();
          }
        };
      }

      tbody.appendChild(tr);
    }
  }

  await loadAndRender();
  // --- END SPEC-1 BODY ---
}

function esc(s){ return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
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
