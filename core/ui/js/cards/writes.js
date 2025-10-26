registerCard('writes', function ({ API, Dom, Modals }) {
  const el = Dom && typeof Dom.el === 'function' ? Dom.el : null;

  async function fetchState(statusNode, toggle){
    if (!statusNode || !API) return;
    statusNode.textContent = 'Loading…';
    try {
      const data = await API.get('/dev/writes');
      if (toggle) {
        toggle.checked = Boolean(data && data.enabled);
      }
      statusNode.textContent = JSON.stringify(data || {}, null, 2);
    } catch (error) {
      statusNode.textContent = 'Error: ' + (error && error.message ? error.message : String(error));
    }
  }

  async function updateState(enabled, statusNode, toggle){
    if (!statusNode || !API) {
      return;
    }
    statusNode.textContent = 'Updating…';
    try {
      const data = await API.post('/dev/writes', { enabled });
      statusNode.textContent = JSON.stringify(data || {}, null, 2);
      const headerToggle = document.getElementById('writes-toggle');
      if (headerToggle) {
        headerToggle.checked = enabled;
        headerToggle.dispatchEvent(new Event('change'));
      } else {
        document.dispatchEvent(new CustomEvent('writes:changed', { detail: { enabled } }));
      }
    } catch (error) {
      statusNode.textContent = 'Error: ' + (error && error.message ? error.message : String(error));
      if (toggle) {
        toggle.checked = !enabled;
      }
    } finally {
      await fetchState(statusNode, toggle);
    }
  }

  function init() {}

  async function render(container){
    if (!container) return;
    if (!el) {
      container.textContent = 'UI helpers unavailable.';
      return;
    }

    const title = el('h2', {}, 'Writes Control');
    const description = el('div', { class: 'badge-note' }, 'Toggle local API writes for diagnostics and development.');
    const toggle = el('input', { type: 'checkbox', id: 'writes-card-toggle' });
    const toggleLabel = el('label', { class: 'writes-card-toggle', for: 'writes-card-toggle' }, [
      toggle,
      el('span', { class: 'toggle-label' }, 'Enable writes via API'),
    ]);
    const refreshButton = el('button', { type: 'button', class: 'secondary' }, 'Refresh State');
    const status = el('pre', { class: 'status-box', style: { minHeight: '160px' } }, 'Loading…');

    const headerSync = event => {
      if (!event || !event.detail || toggle.dataset.pending === 'true') {
        return;
      }
      toggle.checked = Boolean(event.detail.enabled);
    };

    refreshButton.addEventListener('click', () => fetchState(status, toggle));
    toggle.addEventListener('change', () => {
      toggle.dataset.pending = 'true';
      updateState(toggle.checked, status, toggle).finally(() => {
        toggle.dataset.pending = 'false';
      });
    });

    document.addEventListener('writes:changed', headerSync);

    container.replaceChildren(
      title,
      description,
      el('section', {}, [
        el('div', { class: 'section-title' }, 'Control'),
        toggleLabel,
        el('div', { class: 'actions' }, [refreshButton]),
      ]),
      el('section', {}, [
        el('div', { class: 'section-title' }, 'State'),
        status,
      ]),
    );

    await fetchState(status, toggle);

    container.addEventListener('DOMNodeRemoved', event => {
      if (event.target === container) {
        document.removeEventListener('writes:changed', headerSync);
      }
    });
  }

  return { init, render };
});
