registerCard('dev', ({ API, Dom }) => {
  const el = Dom && typeof Dom.el === 'function' ? Dom.el : null;

  function init() {}

  async function render(container){
    if (!container) return;
    if (!el) {
      container.textContent = 'UI helpers unavailable.';
      return;
    }

    const title = el('h2', {}, 'Developer Tools');
    const description = el('div', { class: 'badge-note' }, 'Ping local plugin endpoints for debugging.');
    const pingButton = el('button', { type: 'button' }, 'Ping Plugin');
    const output = el('pre', { class: 'status-box', style: { minHeight: '140px' } }, 'Awaiting action.');

    pingButton.addEventListener('click', async () => {
      output.textContent = 'Pinging…';
      if (!API) {
        output.textContent = 'API unavailable.';
        return;
      }
      try {
        const data = await API.get('/dev/ping_plugin');
        output.textContent = JSON.stringify(data || {}, null, 2);
      } catch (error) {
        output.textContent = 'Error: ' + (error && error.message ? error.message : String(error));
      }
    });

    container.replaceChildren(
      title,
      description,
      el('section', {}, [
        el('div', { class: 'section-title' }, 'Diagnostics'),
        el('div', { class: 'actions' }, [pingButton]),
        output,
      ]),
    );
  }

  return { init, render };
});
