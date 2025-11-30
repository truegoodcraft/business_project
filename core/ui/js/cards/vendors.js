// SPDX-License-Identifier: AGPL-3.0-or-later
// Contacts & Vendors card (unified shallow/deep flows)

import { apiDelete, apiGet, apiPost, apiPut, ensureToken } from '../api.js';

const BG = '#1e1f22';
const FG = '#e6e6e6';
const PANEL = '#23262b';
const INPUT_BG = '#2a2c30';
const BORDER = '#2f3239';

const ROLE_FILTERS = [
  { key: 'all', label: 'All', is_vendor: null },
  { key: 'vendors', label: 'Vendors', is_vendor: true },
  { key: 'contacts', label: 'Contacts', is_vendor: false },
];

function formatDate(val) {
  if (!val) return '';
  try {
    const d = new Date(val);
    if (Number.isNaN(d.getTime())) return String(val);
    return d.toLocaleString();
  } catch {
    return String(val);
  }
}

function chip(text, tone = 'default') {
  const span = document.createElement('span');
  span.textContent = text;
  span.style.display = 'inline-flex';
  span.style.alignItems = 'center';
  span.style.gap = '6px';
  span.style.padding = '4px 10px';
  span.style.borderRadius = '999px';
  span.style.fontSize = '12px';
  span.style.border = `1px solid ${BORDER}`;
  span.style.background = tone === 'accent' ? '#2f3542' : '#1f2227';
  span.style.color = FG;
  return span;
}

function button(label) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.textContent = label;
  btn.style.background = '#2a3040';
  btn.style.color = FG;
  btn.style.border = `1px solid ${BORDER}`;
  btn.style.padding = '10px 14px';
  btn.style.borderRadius = '10px';
  btn.style.cursor = 'pointer';
  btn.style.transition = 'background 0.15s ease, transform 0.15s ease';
  btn.onmouseenter = () => (btn.style.background = '#32384a');
  btn.onmouseleave = () => (btn.style.background = '#2a3040');
  btn.onfocus = () => (btn.style.outline = '2px solid #4b6bfb');
  btn.onblur = () => (btn.style.outline = 'none');
  return btn;
}

function input(label, type = 'text') {
  const wrap = document.createElement('label');
  wrap.style.display = 'flex';
  wrap.style.flexDirection = 'column';
  wrap.style.gap = '6px';
  wrap.style.color = FG;
  wrap.style.fontSize = '13px';

  const span = document.createElement('span');
  span.textContent = label;
  const field = document.createElement('input');
  field.type = type;
  field.style.background = INPUT_BG;
  field.style.color = FG;
  field.style.border = `1px solid ${BORDER}`;
  field.style.borderRadius = '10px';
  field.style.padding = '10px 12px';
  field.style.fontSize = '14px';
  field.style.outline = 'none';
  field.onfocus = () => (field.style.borderColor = '#4b6bfb');
  field.onblur = () => (field.style.borderColor = BORDER);

  wrap.append(span, field);
  return { wrap, field };
}

function select(label) {
  const wrap = document.createElement('label');
  wrap.style.display = 'flex';
  wrap.style.flexDirection = 'column';
  wrap.style.gap = '6px';
  wrap.style.color = FG;
  wrap.style.fontSize = '13px';

  const span = document.createElement('span');
  span.textContent = label;
  const field = document.createElement('select');
  field.style.background = INPUT_BG;
  field.style.color = FG;
  field.style.border = `1px solid ${BORDER}`;
  field.style.borderRadius = '10px';
  field.style.padding = '10px 12px';
  field.style.fontSize = '14px';
  field.style.outline = 'none';
  field.onfocus = () => (field.style.borderColor = '#4b6bfb');
  field.onblur = () => (field.style.borderColor = BORDER);

  wrap.append(span, field);
  return { wrap, field };
}

function toast(message, tone = 'ok') {
  const el = document.createElement('div');
  el.textContent = message;
  el.style.position = 'fixed';
  el.style.bottom = '20px';
  el.style.right = '20px';
  el.style.padding = '12px 14px';
  el.style.borderRadius = '10px';
  el.style.background = tone === 'error' ? '#5b1f1f' : '#1f3b2f';
  el.style.color = FG;
  el.style.boxShadow = '0 8px 20px rgba(0,0,0,0.4)';
  el.style.zIndex = '9999';
  document.body.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.3s ease';
    setTimeout(() => el.remove(), 300);
  }, 2000);
}

function vendorLabel(isVendor) {
  return isVendor ? 'Vendor' : 'Contact';
}

function buildModal() {
  const overlay = document.createElement('div');
  overlay.className = 'contacts-modal';
  overlay.style.position = 'fixed';
  overlay.style.inset = '0';
  overlay.style.background = 'rgba(0,0,0,0.55)';
  overlay.style.display = 'flex';
  overlay.style.alignItems = 'center';
  overlay.style.justifyContent = 'center';
  overlay.style.zIndex = '5000';

  const box = document.createElement('div');
  box.style.background = PANEL;
  box.style.borderRadius = '12px';
  box.style.width = '520px';
  box.style.padding = '20px';
  box.style.boxShadow = '0 18px 36px rgba(0,0,0,0.5)';
  box.style.display = 'flex';
  box.style.flexDirection = 'column';
  box.style.gap = '14px';
  box.style.maxHeight = '85vh';
  box.style.overflow = 'auto';

  overlay.appendChild(box);
  return { overlay, box };
}

export function mountContacts(host) {
  if (!host) return;
  host.innerHTML = '';
  host.style.background = BG;
  host.style.color = FG;
  host.style.padding = '16px';
  host.style.borderRadius = '12px';
  host.style.boxSizing = 'border-box';

  const state = {
    list: [],
    orgs: [],
    expandedId: null,
    filterRole: 'all',
    search: '',
  };

  const header = document.createElement('div');
  header.style.display = 'flex';
  header.style.justifyContent = 'space-between';
  header.style.alignItems = 'center';
  header.style.gap = '12px';
  header.style.marginBottom = '10px';

  const headLeft = document.createElement('div');
  headLeft.style.display = 'flex';
  headLeft.style.flexDirection = 'column';
  headLeft.style.gap = '4px';

  const title = document.createElement('h2');
  title.textContent = 'Contacts';
  title.style.margin = '0';
  title.style.color = FG;

  const subtitle = document.createElement('div');
  subtitle.textContent = 'Vendors & people you deal with';
  subtitle.style.color = '#b9bcc5';
  subtitle.style.fontSize = '13px';

  headLeft.append(title, subtitle);

  const newBtn = button('+ New Contact');

  header.append(headLeft, newBtn);

  const filtersRow = document.createElement('div');
  filtersRow.style.display = 'flex';
  filtersRow.style.alignItems = 'center';
  filtersRow.style.gap = '10px';
  filtersRow.style.flexWrap = 'wrap';
  filtersRow.style.marginBottom = '12px';

  ROLE_FILTERS.forEach((f) => {
    const b = button(f.label);
    b.style.padding = '8px 12px';
    const setActive = () => {
      b.style.background = state.filterRole === f.key ? '#34405c' : '#2a3040';
      b.style.borderColor = state.filterRole === f.key ? '#4b6bfb' : BORDER;
    };
    setActive();
    b.addEventListener('click', () => {
      state.filterRole = f.key;
      setActive();
      loadData();
    });
    filtersRow.appendChild(b);
  });

  const searchWrap = document.createElement('div');
  searchWrap.style.display = 'flex';
  searchWrap.style.flex = '1';
  searchWrap.style.justifyContent = 'flex-end';

  const searchField = document.createElement('input');
  searchField.type = 'search';
  searchField.placeholder = 'Search name or contact…';
  searchField.style.background = INPUT_BG;
  searchField.style.color = FG;
  searchField.style.border = `1px solid ${BORDER}`;
  searchField.style.borderRadius = '10px';
  searchField.style.padding = '10px 12px';
  searchField.style.flex = '1';
  searchField.style.maxWidth = '280px';
  searchField.addEventListener('input', () => {
    state.search = searchField.value.trim();
    loadData();
  });

  searchWrap.appendChild(searchField);
  filtersRow.appendChild(searchWrap);

  const table = document.createElement('div');
  table.style.background = PANEL;
  table.style.border = `1px solid ${BORDER}`;
  table.style.borderRadius = '12px';
  table.style.overflow = 'hidden';

  const headerRow = document.createElement('div');
  headerRow.style.display = 'grid';
    headerRow.style.gridTemplateColumns = '2fr 2fr 1fr 80px';
  headerRow.style.padding = '10px 14px';
  headerRow.style.background = '#2b2d31';
  headerRow.style.color = '#cdd1dc';
  headerRow.style.fontSize = '13px';
  headerRow.style.fontWeight = '600';
    ['Name', 'Contact', 'Flags', ''].forEach((col) => {
      const c = document.createElement('div');
      c.textContent = col;
      headerRow.appendChild(c);
    });

  const body = document.createElement('div');
  body.style.display = 'flex';
  body.style.flexDirection = 'column';

  table.append(headerRow, body);

  host.append(header, filtersRow, table);

  function orgName(id) {
    if (id == null) return null;
    const found = state.orgs.find((o) => o.id === id) || state.list.find((o) => o.id === id);
    return found?.name || null;
  }

  function renderRow(entry) {
    const row = document.createElement('div');
    row.style.display = 'grid';
    row.style.gridTemplateColumns = '2fr 2fr 1fr 80px';
    row.style.padding = '10px 14px';
    row.style.borderTop = `1px solid ${BORDER}`;
    row.style.cursor = 'pointer';
    row.style.alignItems = 'center';
    row.onmouseenter = () => (row.style.background = '#262a31');
    row.onmouseleave = () => (row.style.background = 'transparent');

    const nameCol = document.createElement('div');
    nameCol.style.display = 'flex';
    nameCol.style.flexDirection = 'column';
    nameCol.style.gap = '4px';

    const nameLine = document.createElement('div');
    nameLine.style.display = 'flex';
    nameLine.style.alignItems = 'center';
    nameLine.style.gap = '8px';
    const nm = document.createElement('div');
    nm.textContent = entry.name || '(unnamed)';
    nm.style.fontWeight = '600';
    const vendorBadge = chip(vendorLabel(Boolean(entry.is_vendor)), entry.is_vendor ? 'accent' : 'default');
    vendorBadge.style.opacity = entry.is_vendor ? '1' : '0.8';
    nameLine.append(nm, vendorBadge);
    if (entry.is_org) {
      const orgBadge = chip('Organization');
      nameLine.append(orgBadge);
    }

    const metaLine = document.createElement('div');
    metaLine.style.fontSize = '12px';
    metaLine.style.color = '#b5b8c2';
    const org = orgName(entry.organization_id);
    metaLine.textContent = [entry.contact || '', org ? `Org: ${org}` : '']
      .filter(Boolean)
      .join(' • ');

    nameCol.append(nameLine, metaLine);

    const contactCol = document.createElement('div');
    contactCol.textContent = entry.contact || '—';
    contactCol.style.color = '#cdd1dc';

    const flagsCol = document.createElement('div');
    flagsCol.style.display = 'flex';
    flagsCol.style.gap = '6px';
    flagsCol.style.flexWrap = 'wrap';
    flagsCol.append(chip(vendorLabel(Boolean(entry.is_vendor)), entry.is_vendor ? 'accent' : 'default'));
    if (entry.is_org) {
      flagsCol.append(chip('Organization'));
    }

    const actions = document.createElement('div');
    actions.style.display = 'flex';
    actions.style.justifyContent = 'flex-end';
    actions.style.gap = '6px';

    const edit = button('Edit');
    edit.style.padding = '6px 10px';
    edit.addEventListener('click', (ev) => {
      ev.stopPropagation();
      openEditor(entry);
    });
    const del = button('Delete');
    del.style.padding = '6px 10px';
    del.addEventListener('click', (ev) => {
      ev.stopPropagation();
      openDelete(entry);
    });
    actions.append(edit, del);

    row.append(nameCol, contactCol, flagsCol, actions);

    const expanded = document.createElement('div');
    expanded.style.gridColumn = '1 / -1';
    expanded.style.background = '#1e2025';
    expanded.style.borderRadius = '10px';
    expanded.style.marginTop = '10px';
    expanded.style.padding = '12px 12px 10px';
    expanded.style.display = state.expandedId === entry.id ? 'grid' : 'none';
    expanded.style.gridTemplateColumns = '1fr 1fr';
    expanded.style.gap = '12px';

    const left = document.createElement('div');
    left.style.display = 'flex';
    left.style.flexDirection = 'column';
    left.style.gap = '8px';
    const nameLabel = document.createElement('div');
    nameLabel.textContent = entry.name || '(unnamed)';
    nameLabel.style.fontWeight = '600';
    const chipsRow = document.createElement('div');
    chipsRow.style.display = 'flex';
    chipsRow.style.gap = '8px';
    chipsRow.append(chip(vendorLabel(Boolean(entry.is_vendor)), entry.is_vendor ? 'accent' : 'default'));
    if (entry.is_org) chipsRow.append(chip('Organization'));
    const orgLine = document.createElement('div');
    orgLine.style.fontSize = '12px';
    orgLine.style.color = '#b5b8c2';
    const orgLabel = orgName(entry.organization_id);
    orgLine.textContent = orgLabel ? `Organization: ${orgLabel}` : 'No organization linked';
    left.append(nameLabel, chipsRow, orgLine);

    const right = document.createElement('div');
    right.style.display = 'flex';
    right.style.flexDirection = 'column';
    right.style.gap = '6px';
    const contactLine = document.createElement('div');
    contactLine.textContent = `Contact: ${entry.contact || '—'}`;
    const createdLine = document.createElement('div');
    createdLine.textContent = `Created at: ${formatDate(entry.created_at) || '—'}`;
    right.append(contactLine, createdLine);

    const footer = document.createElement('div');
    footer.style.gridColumn = '1 / -1';
    footer.style.display = 'flex';
    footer.style.justifyContent = 'flex-end';
    footer.style.gap = '8px';
    const edit2 = button('Edit');
    edit2.addEventListener('click', (ev) => {
      ev.stopPropagation();
      openEditor(entry);
    });
    const del2 = button('Delete');
    del2.addEventListener('click', (ev) => {
      ev.stopPropagation();
      openDelete(entry);
    });
    footer.append(edit2, del2);

    expanded.append(left, right, footer);

    row.addEventListener('click', () => {
      state.expandedId = state.expandedId === entry.id ? null : entry.id;
      render();
    });

    const wrapper = document.createElement('div');
    wrapper.append(row, expanded);
    return wrapper;
  }

  function renderEmpty() {
    const empty = document.createElement('div');
    empty.textContent = 'No contacts yet.';
    empty.style.padding = '18px';
    empty.style.color = '#b5b8c2';
    empty.style.textAlign = 'center';
    return empty;
  }

  function render() {
    body.innerHTML = '';
    if (!state.list.length) {
      body.appendChild(renderEmpty());
      return;
    }
    state.list.forEach((entry) => body.appendChild(renderRow(entry)));
  }

  async function loadOrgs() {
    try {
      let res = await apiGet('/app/vendors?is_org=true');
      if (!Array.isArray(res) || !res.length) {
        res = await apiGet('/app/vendors?is_vendor=true');
      }
      state.orgs = Array.isArray(res) ? res : [];
    } catch (err) {
      if (err && (err.status === 404 || err.status === 500)) {
        state.orgs = [];
      } else {
        throw err;
      }
    }
  }

  async function loadData() {
    const params = new URLSearchParams();
    const selected = ROLE_FILTERS.find((f) => f.key === state.filterRole);
    if (selected && selected.is_vendor !== null && selected.is_vendor !== undefined) params.set('is_vendor', selected.is_vendor);
    if (state.search) params.set('q', state.search);
    try {
      const res = await apiGet(`/app/contacts?${params.toString()}`);
      state.list = Array.isArray(res)
        ? res.map((r) => ({ ...r, facade: r.is_vendor ? 'vendors' : 'contacts' }))
        : [];
    } catch (err) {
      if (err && (err.status === 404 || err.status === 500)) {
        state.list = [];
      } else {
        throw err;
      }
    }
    await loadOrgs();
    render();
  }

  function buildToggle(label, initial = false) {
    const wrap = document.createElement('label');
    wrap.style.display = 'flex';
    wrap.style.alignItems = 'center';
    wrap.style.gap = '8px';
    const box = document.createElement('input');
    box.type = 'checkbox';
    box.checked = !!initial;
    const text = document.createElement('span');
    text.textContent = label;
    text.style.fontSize = '13px';
    wrap.append(box, text);
    return {
      wrap,
      input: box,
      getValue: () => box.checked,
      setValue: (val) => {
        box.checked = !!val;
      },
    };
  }

  function openEditor(entry = {}) {
    const isEdit = Boolean(entry?.id);
    const { overlay, box } = buildModal();

    const meta = entry.meta || {};
    const addressMeta = meta.address || {};
    const inferredEmail = meta.email || (entry.contact?.includes('@') ? entry.contact : '');
    const inferredPhone = meta.phone || (!meta.email && !entry.contact?.includes('@') ? entry.contact || '' : '');
    const initialNotes = meta.notes || '';
    const initialExtended = Boolean(
      addressMeta.line1 ||
        addressMeta.line2 ||
        addressMeta.city ||
        addressMeta.state ||
        addressMeta.zip ||
        initialNotes
    );

    const titleRow = document.createElement('div');
    titleRow.style.display = 'flex';
    titleRow.style.justifyContent = 'space-between';
    titleRow.style.alignItems = 'center';

    const heading = document.createElement('div');
    heading.textContent = isEdit ? 'Edit Contact' : 'New Contact';
    heading.style.fontSize = '18px';
    heading.style.fontWeight = '700';

    const closeBtn = button('Cancel');

    titleRow.append(heading, closeBtn);

    const form = document.createElement('div');
    form.style.display = 'flex';
    form.style.flexDirection = 'column';
    form.style.gap = '12px';

    const { wrap: nameWrap, field: nameField } = input('Name *');
    nameField.required = true;
    nameField.placeholder = 'Full name or company';
    nameField.value = entry?.name || '';

    const { wrap: emailWrap, field: emailField } = input('Email', 'email');
    emailField.placeholder = 'name@domain.com';
    emailField.value = inferredEmail || '';

    const { wrap: phoneWrap, field: phoneField } = input('Phone', 'tel');
    phoneField.placeholder = '555-0123';
    phoneField.value = inferredPhone || '';

    const togglesRow = document.createElement('div');
    togglesRow.style.display = 'grid';
    togglesRow.style.gap = '8px';

    const extendToggle = buildToggle('Add Address & Notes', initialExtended);
    const vendorToggle = buildToggle('Treat as Vendor', entry?.is_vendor ?? entry?.facade === 'vendors');

    togglesRow.append(extendToggle.wrap, vendorToggle.wrap);

    const extendedSection = document.createElement('div');
    extendedSection.style.display = extendToggle.getValue() ? 'flex' : 'none';
    extendedSection.style.flexDirection = 'column';
    extendedSection.style.gap = '10px';
    extendedSection.style.paddingTop = '4px';

    const { wrap: addr1Wrap, field: addr1Field } = input('Address Line 1');
    addr1Field.placeholder = '123 Main St';
    addr1Field.value = addressMeta.line1 || '';

    const { wrap: addr2Wrap, field: addr2Field } = input('Address Line 2');
    addr2Field.placeholder = 'Unit, Suite, etc.';
    addr2Field.value = addressMeta.line2 || '';

    const cityStateZip = document.createElement('div');
    cityStateZip.style.display = 'grid';
    cityStateZip.style.gap = '8px';
    cityStateZip.style.gridTemplateColumns = '1fr 120px 120px';

    const { wrap: cityWrap, field: cityField } = input('City');
    cityField.placeholder = 'City';
    cityWrap.style.marginBottom = '0';

    const { wrap: stateWrap, field: stateField } = input('State');
    stateField.placeholder = 'State';
    stateWrap.style.marginBottom = '0';

    const { wrap: zipWrap, field: zipField } = input('Zip');
    zipField.placeholder = 'Zip';
    zipWrap.style.marginBottom = '0';

    cityStateZip.append(cityWrap, stateWrap, zipWrap);

    const notesWrap = document.createElement('label');
    notesWrap.style.display = 'flex';
    notesWrap.style.flexDirection = 'column';
    notesWrap.style.gap = '6px';
    notesWrap.style.color = FG;
    notesWrap.style.fontSize = '13px';
    const notesLabel = document.createElement('span');
    notesLabel.textContent = 'Notes';
    const notesField = document.createElement('textarea');
    notesField.rows = 3;
    notesField.placeholder = 'Anything helpful…';
    notesField.style.background = INPUT_BG;
    notesField.style.color = FG;
    notesField.style.border = `1px solid ${BORDER}`;
    notesField.style.borderRadius = '10px';
    notesField.style.padding = '10px 12px';
    notesField.style.fontSize = '14px';
    notesField.style.outline = 'none';
    notesField.onfocus = () => (notesField.style.borderColor = '#4b6bfb');
    notesField.onblur = () => (notesField.style.borderColor = BORDER);
    notesField.value = initialNotes;
    notesWrap.append(notesLabel, notesField);

    extendedSection.append(addr1Wrap, addr2Wrap, cityStateZip, notesWrap);

    extendToggle.input.addEventListener('change', () => {
      extendedSection.style.display = extendToggle.getValue() ? 'flex' : 'none';
    });

    form.append(nameWrap, emailWrap, phoneWrap, togglesRow, extendedSection);

    const actions = document.createElement('div');
    actions.style.display = 'flex';
    actions.style.justifyContent = 'flex-end';
    actions.style.gap = '10px';
    actions.style.marginTop = '6px';

    const saveBtn = button('Save');
    saveBtn.disabled = !nameField.value.trim();

    const cancelBtn = button('Cancel');
    cancelBtn.addEventListener('click', () => document.body.removeChild(overlay));

    nameField.addEventListener('input', () => {
      saveBtn.disabled = !nameField.value.trim();
    });

    async function save() {
      if (!nameField.value.trim()) {
        toast('Name is required', 'error');
        return;
      }

      const emailVal = emailField.value.trim();
      const phoneVal = phoneField.value.trim();
      const useExtended = extendToggle.getValue();
      const legacyContact = emailVal || phoneVal || '';

      const payload = {
        name: nameField.value.trim(),
        contact: legacyContact || null,
        role: 'contact',
        is_vendor: vendorToggle.getValue() ? 1 : 0,
        is_org: entry?.is_org ? 1 : 0,
        organization_id: entry?.organization_id ?? null,
        meta: {
          email: emailVal,
          phone: phoneVal,
          address: useExtended
            ? {
                line1: addr1Field.value.trim(),
                line2: addr2Field.value.trim(),
                city: cityField.value.trim(),
                state: stateField.value.trim(),
                zip: zipField.value.trim(),
              }
            : { line1: '', line2: '', city: '', state: '', zip: '' },
          notes: useExtended ? notesField.value.trim() : '',
        },
      };

      try {
        saveBtn.textContent = 'Saving…';
        saveBtn.disabled = true;
        await ensureToken();
        let saved;
        if (isEdit) {
          const facade = entry.facade || (entry.is_vendor ? 'vendors' : 'contacts');
          if (facade !== 'contacts') delete payload.role;
          saved = await apiPut(`/app/${facade}/${entry.id}`, payload);
          toast('Saved');
        } else {
          saved = await apiPost('/app/contacts', payload);
          toast('Created');
        }
        if (saved) {
          window.dispatchEvent(new CustomEvent('contacts:saved', { detail: saved }));
        }
        overlay.remove();
        await loadData();
      } catch (err) {
        console.error('save contact failed', err);
        toast('Save failed', 'error');
        saveBtn.textContent = 'Save';
        saveBtn.disabled = false;
      }
    }

    saveBtn.addEventListener('click', save);

    overlay.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        save();
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        document.body.removeChild(overlay);
      }
    });

    closeBtn.addEventListener('click', () => {
      document.body.removeChild(overlay);
    });

    actions.append(cancelBtn, saveBtn);

    box.append(titleRow, form, actions);
    document.body.appendChild(overlay);
    nameField.focus();
  }

  async function openDelete(entry) {
    const { overlay, box } = buildModal();
    const heading = document.createElement('div');
    heading.textContent = 'Delete contact/vendor';
    heading.style.fontSize = '18px';
    heading.style.fontWeight = '700';

    const bodyText = document.createElement('div');
    bodyText.style.color = '#cdd1dc';
    bodyText.style.fontSize = '14px';
    bodyText.textContent = `What should happen to ${entry.name || 'this record'}?`;

    const actions = document.createElement('div');
    actions.style.display = 'flex';
    actions.style.flexDirection = 'column';
    actions.style.gap = '10px';

    const buttonsRow = document.createElement('div');
    buttonsRow.style.display = 'flex';
    buttonsRow.style.justifyContent = 'flex-end';
    buttonsRow.style.gap = '8px';

    const cancel = button('Cancel');
    cancel.addEventListener('click', () => document.body.removeChild(overlay));

    const confirm = button('Confirm');
    const facade = entry.facade || (entry.is_vendor ? 'vendors' : 'contacts');

    if (entry.is_org) {
      const notice = document.createElement('div');
      notice.style.fontSize = '13px';
      notice.style.color = '#cdd1dc';
      notice.textContent = 'Delete this organization. Optionally cascade to linked contacts.';

      const cascadeWrap = document.createElement('label');
      cascadeWrap.style.display = 'flex';
      cascadeWrap.style.alignItems = 'center';
      cascadeWrap.style.gap = '8px';
      cascadeWrap.style.marginTop = '6px';
      const cascadeBox = document.createElement('input');
      cascadeBox.type = 'checkbox';
      const cascadeLabel = document.createElement('span');
      cascadeLabel.textContent = 'Also delete linked contacts (counting…)';
      cascadeWrap.append(cascadeBox, cascadeLabel);

      actions.append(notice, cascadeWrap);

      try {
        const res = await apiGet(`/app/contacts?organization_id=${entry.id}`);
        const count = Array.isArray(res) ? res.length : 0;
        cascadeLabel.textContent = `Also delete ${count} linked contact${count === 1 ? '' : 's'}`;
      } catch (err) {
        console.warn('child count failed', err);
      }

      confirm.addEventListener('click', async () => {
        try {
          confirm.textContent = 'Deleting…';
          confirm.disabled = true;
          await ensureToken();
          const qs = cascadeBox.checked ? '?cascade_children=true' : '';
          await apiDelete(`/app/vendors/${entry.id}${qs}`);
          toast('Deleted');
          document.body.removeChild(overlay);
          await loadData();
        } catch (err) {
          console.error('delete org failed', err);
          toast('Delete failed', 'error');
          confirm.textContent = 'Confirm';
          confirm.disabled = false;
        }
      });
    } else {
      confirm.addEventListener('click', async () => {
        try {
          confirm.textContent = 'Deleting…';
          confirm.disabled = true;
          await ensureToken();
          await apiDelete(`/app/${facade}/${entry.id}`);
          toast('Deleted');
          document.body.removeChild(overlay);
          await loadData();
        } catch (err) {
          console.error('delete failed', err);
          toast('Delete failed', 'error');
          confirm.textContent = 'Confirm';
          confirm.disabled = false;
        }
      });
    }

    buttonsRow.append(cancel, confirm);

    box.append(heading, bodyText, actions, buttonsRow);
    document.body.appendChild(overlay);
    overlay.focus();
  }

  newBtn.addEventListener('click', () => openEditor({ is_vendor: false, is_org: false, facade: 'contacts' }));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'n' || e.key === 'N') {
      const focusedInModal = document.querySelector('.contacts-modal');
      if (!focusedInModal) {
        e.preventDefault();
        openEditor({ is_vendor: false, is_org: false, facade: 'contacts' });
      }
    }
  });

  if (!window.__contactsModalListener) {
    window.addEventListener('open-contacts-modal', (ev) => {
      const prefill = ev.detail?.prefill || {};
      openEditor({ ...prefill, facade: 'contacts' });
    });
    window.__contactsModalListener = true;
  }

  loadData();
}

export default mountContacts;
