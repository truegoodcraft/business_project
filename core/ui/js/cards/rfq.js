(function(){
  if (!window.API || !window.Dom || !window.Modals) {
    console.error('Card missing API helpers: rfq');
    return;
  }

  const { el, bindDisabledWithProGate } = window.Dom;
  const API = window.API;

  function asArray(value){
    return Array.isArray(value) ? value : [];
  }

  function downloadBlob(blob, filename){
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  async function render(container){
    if (!el || !API) {
      container.textContent = 'UI helpers unavailable.';
      return;
    }

    const status = el('div', { class: 'status-box' }, 'Load vendors and items before generating RFQs.');
    const vendorSelect = el('select', { multiple: true, size: 6 });
    const itemSelect = el('select', { multiple: true, size: 8 });
    const formatSelect = el('select', {}, [
      el('option', { value: 'md' }, 'Markdown (.md)'),
      el('option', { value: 'txt' }, 'Plain text (.txt)'),
      el('option', { value: 'pdf' }, 'PDF (.pdf)'),
    ]);
    const generateButton = el('button', { type: 'button' }, 'Generate RFQ');
    bindDisabledWithProGate(generateButton, 'rfq');

    container.replaceChildren(
      el('div', { class: 'form-grid' }, [
        el('label', {}, ['Vendors', vendorSelect]),
        el('label', {}, ['Items', itemSelect]),
        el('label', {}, ['Format', formatSelect]),
      ]),
      generateButton,
      status,
    );

    async function loadData(){
      try {
        status.textContent = 'Loading vendors and items…';
        const [vendors, items] = await Promise.all([
          API.get('/vendors'),
          API.get('/items'),
        ]);
        vendorSelect.innerHTML = '';
        asArray(vendors).forEach(vendor => {
          vendorSelect.appendChild(el('option', { value: String(vendor.id) }, vendor.name || `Vendor #${vendor.id}`));
        });
        itemSelect.innerHTML = '';
        asArray(items).forEach(item => {
          const label = [item.sku, item.name || `Item #${item.id}`].filter(Boolean).join(' • ');
          itemSelect.appendChild(el('option', { value: String(item.id) }, label));
        });
        status.textContent = 'Select vendors and items to generate RFQs.';
      } catch (error) {
        status.textContent = 'Failed to load data: ' + (error && error.message ? error.message : String(error));
      }
    }

    generateButton.addEventListener('click', async () => {
      const selectedVendors = Array.from(vendorSelect.selectedOptions).map(option => Number(option.value)).filter(id => !Number.isNaN(id));
      const selectedItems = Array.from(itemSelect.selectedOptions).map(option => Number(option.value)).filter(id => !Number.isNaN(id));
      if (!selectedVendors.length || !selectedItems.length) {
        status.textContent = 'Select at least one vendor and one item.';
        return;
      }
      const fmt = formatSelect.value || 'md';
      status.textContent = 'Generating RFQ…';
      try {
        const result = await API.post('/rfq/generate', {
          vendors: selectedVendors,
          items: selectedItems,
          fmt,
        });
        if (result && result.locked) {
          return;
        }
        if (result instanceof Blob) {
          const ext = fmt === 'pdf' ? 'pdf' : (fmt === 'txt' ? 'txt' : 'md');
          const filename = `rfq-${Date.now()}.${ext}`;
          downloadBlob(result, filename);
          status.textContent = `RFQ downloaded: ${filename}`;
        } else {
          status.textContent = 'Unexpected response.';
        }
      } catch (error) {
        status.textContent = 'Generation failed: ' + (error && error.message ? error.message : String(error));
      }
    });

    await loadData();
    document.addEventListener('vendors:refresh', loadData);
    document.addEventListener('items:refresh', loadData);
    container.addEventListener('DOMNodeRemoved', event => {
      if (event.target === container) {
        document.removeEventListener('vendors:refresh', loadData);
        document.removeEventListener('items:refresh', loadData);
      }
    });
  }

  function init() {}

  if (window.Cards && typeof window.Cards.register === 'function') {
    window.Cards.register('rfq', { init, render });
  }
})();
