(function(){
  function register(){
    if (!window.API || !window.Dom || !window.Modals) {
      console.error('Card missing API helpers: dev');
      return;
    }

    const { el } = window.Dom;
    const API = window.API;

    function init() {}

    async function render(container){
      if (!container) return;

      const title = el('h2', {}, 'Developer Tools');
      const description = el('div', { class: 'badge-note' }, 'Ping local plugin endpoints for debugging.');
      const pingButton = el('button', { type: 'button' }, 'Ping Plugin');
      const output = el('pre', { class: 'status-box', style: { minHeight: '140px' } }, 'Awaiting action.');

      pingButton.addEventListener('click', async () => {
        output.textContent = 'Pinging…';
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

    const module = { init, render };
    if (window.Cards && typeof window.Cards.register === 'function') {
      window.Cards.register('dev', module);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', register);
  } else {
    register();
  }
})();
