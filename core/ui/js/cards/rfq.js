(function(){
  const TOKEN_KEY = 'BUS_SESSION_TOKEN';
  let patched = false;
  let lastRoot = null;

  function getApi(){
    const busApi = window.busApi || {};
    const apiGet = typeof busApi.apiGet === 'function' ? busApi.apiGet : window.apiGet;
    const apiPost = typeof busApi.apiPost === 'function' ? busApi.apiPost : window.apiPost;
    return { apiGet, apiPost };
  }

  function el(tag, attrs, ...children){
    const node = document.createElement(tag);
    if (attrs){
      Object.entries(attrs).forEach(([key, value]) => {
        if (value === undefined || value === null) return;
        if (key === 'class') node.className = value;
        else if (key === 'for') node.htmlFor = value;
        else node.setAttribute(key, value);
      });
    }
    children.flat().forEach(child => {
      if (child === undefined || child === null) return;
      if (child instanceof Node) node.appendChild(child);
      else node.appendChild(document.createTextNode(String(child)));
    });
    return node;
  }

  function downloadBlob(blob, filename){
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  async function fetchBlob(path, body){
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    if (!res.ok){
      let message = '';
      try {
        const text = await res.text();
        if (text){
          try {
            const parsed = JSON.parse(text);
            if (parsed && typeof parsed === 'object' && parsed.error) message = String(parsed.error);
            else message = text;
          } catch (_err){
            message = text;
          }
        }
      } catch (_err){
        message = '';
      }
      if (!message) message = 'HTTP ' + res.status;
      throw new Error(message);
    }
    return await res.blob();
  }

  function safeParseObject(text){
    if (!text || !text.trim()) return {};
    try {
      const value = JSON.parse(text);
      if (!value || typeof value !== 'object' || Array.isArray(value)){
        throw new Error('Expected JSON object.');
      }
      return value;
    } catch (error){
      throw new Error('Invalid JSON: ' + error.message);
    }
  }

  async function loadData(apiGet){
    const vendors = await apiGet('/app/vendors').catch(() => []);
    const items = await apiGet('/app/items').catch(() => []);
    return {
      vendors: Array.isArray(vendors) ? vendors : [],
      items: Array.isArray(items) ? items : [],
    };
  }

  function renderOptions(select, records, formatter){
    select.innerHTML = '';
    records.forEach(rec => {
      const opt = document.createElement('option');
      opt.value = String(rec.id);
      opt.textContent = formatter(rec);
      select.appendChild(opt);
    });
  }

  async function render(container){
    const { apiGet, apiPost } = getApi();
    if (typeof apiGet !== 'function' || typeof apiPost !== 'function'){
      container.textContent = 'API helpers unavailable.';
      return;
    }

    let data;
    try {
      data = await loadData(apiGet);
    } catch (error){
      container.textContent = 'Failed to load vendors/items: ' + error.message;
      return;
    }

    const status = el('pre', { class: 'muted', style: 'margin-top:8px; white-space:pre-wrap;' });
    const vendorSelect = el('select', { multiple: '', size: String(Math.min(10, Math.max(3, data.vendors.length || 4))), style: 'min-width:220px;' });
    const itemSelect = el('select', { multiple: '', size: String(Math.min(12, Math.max(4, data.items.length || 6))), style: 'min-width:280px;' });
    const fmtSelect = el('select', { style: 'min-width:120px;' },
      el('option', { value: 'md' }, 'md'),
      el('option', { value: 'txt' }, 'txt'),
      el('option', { value: 'pdf' }, 'pdf'),
    );
    const genBtn = el('button', { type: 'button' }, 'Generate RFQ');

    const inputsArea = el('textarea', { placeholder: 'Inputs JSON e.g. {"1":2}', style: 'min-height:80px;width:100%;' });
    const outputsArea = el('textarea', { placeholder: 'Outputs JSON e.g. {"3":1}', style: 'min-height:80px;width:100%;margin-top:8px;' });
    const noteInput = el('input', { type: 'text', placeholder: 'Optional note', style: 'margin-top:8px;width:100%;' });
    const runBtn = el('button', { type: 'button', style: 'margin-top:8px;' }, 'Run Inventory');

    renderOptions(vendorSelect, data.vendors, rec => rec.name || ('Vendor #' + rec.id));
    renderOptions(itemSelect, data.items, rec => [rec.sku || '', rec.name || ('Item #' + rec.id)].filter(Boolean).join(' ').trim());

    const rfqBox = el('div', { class: 'rfq-box' },
      el('h3', {}, 'RFQ'),
      el('div', { style: 'display:flex;gap:12px;flex-wrap:wrap;' },
        el('label', { style: 'display:flex;flex-direction:column;gap:4px;' }, 'Vendors', vendorSelect),
        el('label', { style: 'display:flex;flex-direction:column;gap:4px;' }, 'Items', itemSelect),
        el('label', { style: 'display:flex;flex-direction:column;gap:4px;align-self:flex-start;' }, 'Format', fmtSelect),
      ),
      genBtn,
    );

    const invBox = el('div', { class: 'rfq-inventory', style: 'margin-top:16px;' },
      el('h3', {}, 'Inventory Run'),
      inputsArea,
      outputsArea,
      noteInput,
      runBtn,
    );

    container.replaceChildren(rfqBox, invBox, status);

    genBtn.addEventListener('click', async () => {
      const selectedItems = Array.from(itemSelect.selectedOptions).map(opt => Number(opt.value)).filter(n => !Number.isNaN(n));
      const selectedVendors = Array.from(vendorSelect.selectedOptions).map(opt => Number(opt.value)).filter(n => !Number.isNaN(n));
      if (!selectedItems.length){
        status.textContent = 'Select at least one item.';
        return;
      }
      if (!selectedVendors.length){
        status.textContent = 'Select at least one vendor.';
        return;
      }

      const fmt = fmtSelect.value;
      status.textContent = 'Generating RFQ…';
      genBtn.disabled = true;
      try {
        const blob = await fetchBlob('/app/rfq/generate', { items: selectedItems, vendors: selectedVendors, fmt });
        const ts = Math.floor(Date.now() / 1000);
        const ext = fmt === 'pdf' ? 'pdf' : (fmt === 'txt' ? 'txt' : 'md');
        downloadBlob(blob, `rfq-${ts}.${ext}`);
        status.textContent = 'RFQ generated.';
      } catch (error){
        status.textContent = 'RFQ error: ' + error.message;
      } finally {
        genBtn.disabled = false;
      }
    });

    runBtn.addEventListener('click', async () => {
      status.textContent = 'Running inventory…';
      runBtn.disabled = true;
      try {
        const inputs = safeParseObject(inputsArea.value);
        const outputs = safeParseObject(outputsArea.value);
        const note = noteInput.value && noteInput.value.trim() ? noteInput.value.trim() : null;
        const result = await apiPost('/app/inventory/run', { inputs, outputs, note });
        status.textContent = JSON.stringify(result, null, 2);
        document.dispatchEvent(new CustomEvent('items:refresh'));
      } catch (error){
        status.textContent = 'Inventory error: ' + error.message;
      } finally {
        runBtn.disabled = false;
      }
    });
  }

  async function mountRFQ(root){
    if (!root) return;
    lastRoot = root;
    let container = root.querySelector('[data-rfq-root]');
    if (!container){
      container = document.createElement('div');
      container.dataset.rfqRoot = '1';
      container.style.marginTop = '16px';
      container.style.paddingTop = '12px';
      container.style.borderTop = '1px solid #26262e';
      root.appendChild(container);
    }
    container.textContent = 'Loading RFQ…';
    try {
      await render(container);
    } catch (error){
      container.textContent = 'RFQ load error: ' + error.message;
    }
  }

  function handleRefresh(){
    if (lastRoot && lastRoot.isConnected){
      mountRFQ(lastRoot);
    }
  }

  function tryPatch(){
    if (patched) return true;
    const { apiGet, apiPost } = getApi();
    const cards = window.busCards;
    const hasToken = !!localStorage.getItem(TOKEN_KEY);
    if (!cards || typeof cards.mountOrganizer !== 'function' || typeof apiGet !== 'function' || typeof apiPost !== 'function' || !hasToken){
      return false;
    }
    const original = cards.mountOrganizer;
    cards.mountOrganizer = async function(root){
      await Promise.resolve(original(root));
      try {
        await mountRFQ(root);
      } catch (error){
        console.error('rfq mount failed', error);
      }
    };
    document.addEventListener('items:refresh', handleRefresh);
    patched = true;
    return true;
  }

  function schedule(){
    if (tryPatch()) return;
    setTimeout(schedule, 200);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', schedule);
  else schedule();
  window.addEventListener('bus:token-ready', schedule);
})();
