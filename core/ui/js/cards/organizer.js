(function(){
  function register(){
    if (!window.API || !window.Dom || !window.Modals) {
      console.error('Card missing API helpers: organizer');
      return;
    }

    const { el } = window.Dom;
    const API = window.API;
    const Modals = window.Modals;

    function showError(output, error){
      output.textContent = 'Error: ' + (error && error.message ? error.message : String(error));
    }

    function init() {}

    async function render(container){
      if (!container) return;

      const startInput = el('input', { type: 'text', placeholder: 'Start folder', style: { minWidth: '320px' } });
      const quarantineInput = el('input', { type: 'text', placeholder: 'Quarantine folder (optional)', style: { minWidth: '320px' } });
      const duplicatesButton = el('button', { type: 'button' }, 'Duplicates -> Plan');
      const renameButton = el('button', { type: 'button' }, 'Normalize -> Plan');
      const planInput = el('input', { type: 'text', placeholder: 'Plan ID', style: { minWidth: '320px' } });
      const previewButton = el('button', { type: 'button', class: 'secondary' }, 'Preview Plan');
      const commitButton = el('button', { type: 'button' }, 'Commit Plan');
      const status = el('pre', { class: 'status-box', style: { minHeight: '180px' } }, 'Awaiting action.');

      async function withStatus(task){
        status.textContent = 'Working…';
        try {
          const result = await task();
          status.textContent = JSON.stringify(result || {}, null, 2);
          return result;
        } catch (error) {
          showError(status, error);
          throw error;
        }
      }

      duplicatesButton.addEventListener('click', async () => {
        const startPath = startInput.value.trim();
        if (!startPath) {
          Modals.alert('Organizer', 'Provide a start folder.');
          return;
        }
        try {
          const result = await withStatus(() => API.post('/organizer/duplicates/plan', {
            start_path: startPath,
            quarantine_dir: quarantineInput.value.trim() || null,
          }));
          if (result && result.plan_id) {
            planInput.value = result.plan_id;
          }
        } catch (error) {
          // handled by withStatus
        }
      });

      renameButton.addEventListener('click', async () => {
        const startPath = startInput.value.trim();
        if (!startPath) {
          Modals.alert('Organizer', 'Provide a start folder.');
          return;
        }
        try {
          const result = await withStatus(() => API.post('/organizer/rename/plan', {
            start_path: startPath,
          }));
          if (result && result.plan_id) {
            planInput.value = result.plan_id;
          }
        } catch (error) {
          // handled by withStatus
        }
      });

      function ensurePlanId(){
        const value = planInput.value.trim();
        if (!value) {
          Modals.alert('Organizer', 'Set a plan ID before continuing.');
          return null;
        }
        return value;
      }

      previewButton.addEventListener('click', async () => {
        const planId = ensurePlanId();
        if (!planId) return;
        try {
          await withStatus(() => API.post(`/plans/${encodeURIComponent(planId)}/preview`, {}));
        } catch (error) {
          // handled by withStatus
        }
      });

      commitButton.addEventListener('click', async () => {
        const planId = ensurePlanId();
        if (!planId) return;
        try {
          await withStatus(() => API.post(`/plans/${encodeURIComponent(planId)}/commit`, {}));
        } catch (error) {
          // handled by withStatus
        }
      });

      container.replaceChildren(
        el('h2', {}, 'Organizer'),
        el('div', { class: 'badge-note' }, 'Create, preview, and commit organizer plans.'),
        el('section', {}, [
          el('div', { class: 'section-title' }, 'Create plan'),
          el('div', { class: 'form-grid' }, [
            el('label', {}, ['Start folder', startInput]),
            el('label', {}, ['Quarantine folder', quarantineInput]),
          ]),
          el('div', { class: 'actions' }, [duplicatesButton, renameButton]),
        ]),
        el('section', {}, [
          el('div', { class: 'section-title' }, 'Manage plan'),
          el('div', { class: 'form-grid' }, [
            el('label', {}, ['Plan ID', planInput]),
          ]),
          el('div', { class: 'actions' }, [previewButton, commitButton]),
        ]),
        status,
      );
    }

    const module = { init, render };
    if (window.Cards && typeof window.Cards.register === 'function') {
      window.Cards.register('organizer', module);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', register);
  } else {
    register();
  }
})();
