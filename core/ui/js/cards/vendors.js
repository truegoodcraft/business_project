(function(){
  if (!window.API || !window.Dom || !window.Modals) {
    console.error('Card missing API helpers: vendors');
    return;
  }

  const { el } = window.Dom;
  const API = window.API;

  function asArray(value){
    return Array.isArray(value) ? value : [];
  }

  function buildForm(state, refresh){
    const nameInput = el('input', { name: 'name', required: true, placeholder: 'Vendor name' });
    const contactInput = el('input', { name: 'contact', placeholder: 'Contact details' });
    const notesInput = el('textarea', { name: 'notes', placeholder: 'Notes' });
    const submit = el('button', { type: 'submit' }, 'Add Vendor');
    const cancel = el('button', { type: 'button', class: 'secondary' }, 'Cancel');

    function reset(){
      state.editingId = null;
      nameInput.value = '';
      contactInput.value = '';
      notesInput.value = '';
      submit.textContent = 'Add Vendor';
      cancel.style.display = 'none';
    }

    function fill(vendor){
      state.editingId = vendor.id;
      nameInput.value = vendor.name || '';
      contactInput.value = vendor.contact || '';
      notesInput.value = vendor.notes || '';
      submit.textContent = 'Update Vendor';
      cancel.style.display = 'inline-flex';
    }

    const form = el('form', {}, [
      el('div', { class: 'section-title' }, state.editingId ? 'Edit Vendor' : 'Create Vendor'),
      el('div', { class: 'form-grid' }, [
        el('label', {}, ['Name', nameInput]),
        el('label', {}, ['Contact', contactInput]),
      ]),
      el('label', {}, ['Notes', notesInput]),
      el('div', { class: 'actions' }, [submit, cancel]),
    ]);

    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!API) return;
      const payload = {
        name: nameInput.value.trim(),
        contact: contactInput.value.trim() || null,
        notes: notesInput.value.trim() || null,
      };
      if (!payload.name) return;
      try {
        if (state.editingId) {
          await API.put(`/vendors/${state.editingId}`, payload);
        } else {
          await API.post('/vendors', payload);
        }
        reset();
        await refresh();
        document.dispatchEvent(new CustomEvent('vendors:refresh'));
        document.dispatchEvent(new CustomEvent('items:refresh'));
      } catch (error) {
        state.status.textContent = 'Save failed: ' + (error && error.message ? error.message : String(error));
      }
    });

    cancel.addEventListener('click', () => reset());

    state.updateForm = fill;
    state.resetForm = reset;
    reset();
    cancel.style.display = 'none';
    return form;
  }

  function buildTable(state, refresh){
    const table = el('table');
    const head = el('thead', {}, el('tr', {}, [
      el('th', {}, 'Name'),
      el('th', {}, 'Contact'),
      el('th', {}, 'Notes'),
      el('th', {}, 'Actions'),
    ]));
    const body = el('tbody');
    table.appendChild(head);
    table.appendChild(body);

    function renderRows(){
      body.innerHTML = '';
      asArray(state.vendors).forEach(vendor => {
        const row = el('tr', {}, [
          el('td', {}, vendor.name || 'Unnamed'),
          el('td', {}, vendor.contact || '—'),
          el('td', {}, vendor.notes || '—'),
          el('td', {}, createActions(vendor)),
        ]);
        body.appendChild(row);
      });
    }

    function createActions(vendor){
      const edit = el('button', { type: 'button', class: 'secondary' }, 'Edit');
      const remove = el('button', { type: 'button', class: 'danger' }, 'Delete');
      edit.addEventListener('click', () => {
        if (state.updateForm) state.updateForm(vendor);
      });
      remove.addEventListener('click', () => {
        if (!window.Modals) return;
        window.Modals.confirm('Delete Vendor', `Delete ${vendor.name || 'this vendor'}?`, async () => {
          try {
            await API.delete(`/vendors/${vendor.id}`);
            await refresh();
            document.dispatchEvent(new CustomEvent('vendors:refresh'));
            document.dispatchEvent(new CustomEvent('items:refresh'));
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

    const state = { vendors: [], editingId: null, status: el('div', { class: 'status-box' }) };
    const title = el('h2', {}, 'Vendors');
    const table = buildTable(state, refresh);
    const form = buildForm(state, refresh);

    container.replaceChildren(title, table, form, state.status);

    async function refresh(){
      try {
        const vendors = await API.get('/vendors');
        state.vendors = asArray(vendors);
        if (state.renderRows) state.renderRows();
        state.status.textContent = `Loaded ${state.vendors.length} vendors.`;
      } catch (error) {
        state.status.textContent = 'Load failed: ' + (error && error.message ? error.message : String(error));
      }
    }

    await refresh();
  }

  function init() {}

  if (window.Cards && typeof window.Cards.register === 'function') {
    window.Cards.register('vendors', { init, render });
  }
})();
