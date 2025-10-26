(function(){
  if (!window.API || !window.Dom || !window.Modals) {
    console.error('Card missing API helpers: inventory');
    return;
  }

  const { el } = window.Dom;
  const API = window.API;

  function asArray(value){
    return Array.isArray(value) ? value : [];
  }

  function formatNumber(value){
    if (value === null || value === undefined) return '';
    const number = Number(value);
    if (Number.isNaN(number)) return '';
    return number.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  function buildForm(state, refresh){
    const vendorSelect = el('select', { name: 'vendor_id' });
    const nameInput = el('input', { name: 'name', required: true, placeholder: 'Item name' });
    const skuInput = el('input', { name: 'sku', placeholder: 'SKU' });
    const qtyInput = el('input', { name: 'qty', type: 'number', step: '0.01', placeholder: 'Quantity' });
    const unitInput = el('input', { name: 'unit', placeholder: 'Unit' });
    const priceInput = el('input', { name: 'price', type: 'number', step: '0.01', placeholder: 'Price' });
    const notesInput = el('textarea', { name: 'notes', placeholder: 'Notes' });
    const submit = el('button', { type: 'submit' }, 'Add Item');
    const cancel = el('button', { type: 'button', class: 'secondary' }, 'Cancel');

    function updateVendors(){
      const vendors = asArray(state.vendors);
      vendorSelect.innerHTML = '';
      vendorSelect.appendChild(el('option', { value: '' }, '— No Vendor —'));
      vendors.forEach(vendor => {
        vendorSelect.appendChild(el('option', { value: String(vendor.id) }, vendor.name || `Vendor #${vendor.id}`));
      });
    }

    function reset(){
      state.editingId = null;
      nameInput.value = '';
      skuInput.value = '';
      qtyInput.value = '';
      unitInput.value = '';
      priceInput.value = '';
      notesInput.value = '';
      vendorSelect.value = '';
      submit.textContent = 'Add Item';
      cancel.style.display = 'none';
    }

    function fill(item){
      state.editingId = item.id;
      nameInput.value = item.name || '';
      skuInput.value = item.sku || '';
      qtyInput.value = item.qty !== null && item.qty !== undefined ? String(item.qty) : '';
      unitInput.value = item.unit || '';
      priceInput.value = item.price !== null && item.price !== undefined ? String(item.price) : '';
      notesInput.value = item.notes || '';
      vendorSelect.value = item.vendor_id ? String(item.vendor_id) : '';
      submit.textContent = 'Update Item';
      cancel.style.display = 'inline-flex';
    }

    const form = el('form', {}, [
      el('div', { class: 'section-title' }, state.editingId ? 'Edit Item' : 'Create Item'),
      el('div', { class: 'form-grid' }, [
        el('label', {}, ['Name', nameInput]),
        el('label', {}, ['SKU', skuInput]),
        el('label', {}, ['Quantity', qtyInput]),
        el('label', {}, ['Unit', unitInput]),
        el('label', {}, ['Price', priceInput]),
        el('label', {}, ['Vendor', vendorSelect]),
      ]),
      el('label', {}, ['Notes', notesInput]),
      el('div', { class: 'actions' }, [submit, cancel]),
    ]);

    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!API) return;
      const payload = {
        name: nameInput.value.trim(),
        sku: skuInput.value.trim() || null,
        qty: qtyInput.value === '' ? null : Number(qtyInput.value),
        unit: unitInput.value.trim() || null,
        price: priceInput.value === '' ? null : Number(priceInput.value),
        notes: notesInput.value.trim() || null,
        vendor_id: vendorSelect.value ? Number(vendorSelect.value) : null,
      };
      if (!payload.name) return;
      try {
        if (state.editingId) {
          await API.put(`/items/${state.editingId}`, payload);
        } else {
          await API.post('/items', payload);
        }
        document.dispatchEvent(new CustomEvent('items:refresh'));
        reset();
        await refresh();
      } catch (error) {
        state.status.textContent = 'Save failed: ' + (error && error.message ? error.message : String(error));
      }
    });

    cancel.addEventListener('click', () => {
      reset();
    });

    state.updateForm = fill;
    state.resetForm = reset;
    state.syncVendors = updateVendors;
    reset();
    updateVendors();
    cancel.style.display = 'none';
    return form;
  }

  function buildTable(state, refresh){
    const table = el('table');
    const head = el('thead', {}, el('tr', {}, [
      el('th', {}, 'Name'),
      el('th', {}, 'SKU'),
      el('th', {}, 'Qty'),
      el('th', {}, 'Vendor'),
      el('th', {}, 'Price'),
      el('th', {}, 'Actions'),
    ]));
    const body = el('tbody');
    table.appendChild(head);
    table.appendChild(body);

    function renderRows(){
      body.innerHTML = '';
      const vendors = new Map(asArray(state.vendors).map(v => [v.id, v]));
      asArray(state.items).forEach(item => {
        const vendor = vendors.get(item.vendor_id);
        const row = el('tr', {}, [
          el('td', {}, item.name || 'Untitled'),
          el('td', {}, item.sku || '—'),
          el('td', {}, formatNumber(item.qty)),
          el('td', {}, vendor ? (vendor.name || `Vendor #${vendor.id}`) : '—'),
          el('td', {}, item.price !== null && item.price !== undefined ? formatNumber(item.price) : '—'),
          el('td', {}, createActions(item)),
        ]);
        body.appendChild(row);
      });
    }

    function createActions(item){
      const edit = el('button', { type: 'button', class: 'secondary' }, 'Edit');
      const remove = el('button', { type: 'button', class: 'danger' }, 'Delete');
      edit.addEventListener('click', () => {
        if (state.updateForm) {
          state.updateForm(item);
        }
      });
      remove.addEventListener('click', () => {
        if (!window.Modals) return;
        window.Modals.confirm('Delete Item', `Delete ${item.name || 'this item'}?`, async () => {
          try {
            await API.delete(`/items/${item.id}`);
            document.dispatchEvent(new CustomEvent('items:refresh'));
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

    const state = { items: [], vendors: [], editingId: null, status: el('div', { class: 'status-box' }) };

    const title = el('h2', {}, 'Inventory');
    const table = buildTable(state, refresh);
    const form = buildForm(state, refresh);

    container.replaceChildren(title, table, form, state.status);

    async function refresh(){
      try {
        const [items, vendors] = await Promise.all([
          API.get('/items'),
          API.get('/vendors'),
        ]);
        state.items = asArray(items);
        state.vendors = asArray(vendors);
        if (state.syncVendors) state.syncVendors();
        if (state.renderRows) state.renderRows();
        state.status.textContent = `Loaded ${state.items.length} items.`;
      } catch (error) {
        state.status.textContent = 'Load failed: ' + (error && error.message ? error.message : String(error));
      }
    }

    const onRefresh = () => refresh();
    document.addEventListener('items:refresh', onRefresh);
    container.addEventListener('DOMNodeRemoved', event => {
      if (event.target === container) {
        document.removeEventListener('items:refresh', onRefresh);
      }
    });

    await refresh();
  }

  function init() {}

  if (window.Cards && typeof window.Cards.register === 'function') {
    window.Cards.register('inventory', { init, render });
  }
})();
