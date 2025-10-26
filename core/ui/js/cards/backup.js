(function(){
  if (!window.API || !window.Dom || !window.Modals) {
    console.error('Card missing API helpers: backup');
    return;
  }

  const { el, bindDisabledWithProGate } = window.Dom;
  const API = window.API;

  async function render(container){
    if (!el || !API) {
      container.textContent = 'UI helpers unavailable.';
      return;
    }

    const exportPassword = el('input', { type: 'password', placeholder: 'Export password' });
    const exportButton = el('button', { type: 'button' }, 'Export Backup');
    const importPath = el('input', { type: 'text', placeholder: 'Full path to .tgc file' });
    const importPassword = el('input', { type: 'password', placeholder: 'Import password' });
    const previewButton = el('button', { type: 'button', class: 'secondary' }, 'Preview Import');
    const commitButton = el('button', { type: 'button' }, 'Commit Import');
    bindDisabledWithProGate(commitButton, 'import_commit');
    commitButton.dataset.previewReady = 'false';
    const enforcePreviewLock = () => {
      if (commitButton.dataset.pro !== 'true' && commitButton.dataset.previewReady !== 'true') {
        commitButton.disabled = true;
      }
    };
    enforcePreviewLock();
    document.addEventListener('license:updated', enforcePreviewLock);
    const status = el('div', { class: 'status-box' }, 'Awaiting action.');

    const title = el('h2', {}, 'Backup & Restore');
    const hint = el('div', { class: 'badge-note' }, '%LOCALAPPDATA%/BUSCore/exports will receive new exports.');

    container.replaceChildren(
      title,
      hint,
      el('section', {}, [
        el('div', { class: 'section-title' }, 'Export'),
        el('div', { class: 'form-grid' }, [
          el('label', {}, ['Password', exportPassword]),
        ]),
        exportButton,
      ]),
      el('section', {}, [
        el('div', { class: 'section-title' }, 'Import'),
        el('div', { class: 'form-grid' }, [
          el('label', {}, ['Archive path', importPath]),
          el('label', {}, ['Password', importPassword]),
        ]),
        el('div', { class: 'actions' }, [previewButton, commitButton]),
      ]),
      status,
    );

    let lastPreview = null;

    exportButton.addEventListener('click', async () => {
      const password = exportPassword.value.trim();
      if (!password) {
        status.textContent = 'Enter an export password.';
        return;
      }
      status.textContent = 'Exporting…';
      try {
        const result = await API.post('/export', { password });
        if (result && result.path) {
          status.textContent = `Export complete: ${result.path}`;
        } else {
          status.textContent = 'Export complete.';
        }
      } catch (error) {
        status.textContent = 'Export failed: ' + (error && error.message ? error.message : String(error));
      }
    });

    previewButton.addEventListener('click', async () => {
      const path = importPath.value.trim();
      const password = importPassword.value.trim();
      if (!path || !password) {
        status.textContent = 'Enter path and password for preview.';
        return;
      }
      status.textContent = 'Previewing import…';
      try {
        const result = await API.post('/import/preview', { path, password });
        lastPreview = { path, password, result };
        status.textContent = JSON.stringify(result, null, 2);
        commitButton.dataset.previewReady = 'true';
        if (commitButton.dataset.pro !== 'true') {
          commitButton.disabled = false;
        }
      } catch (error) {
        status.textContent = 'Preview failed: ' + (error && error.message ? error.message : String(error));
        lastPreview = null;
        commitButton.dataset.previewReady = 'false';
        enforcePreviewLock();
      }
    });

    commitButton.addEventListener('click', async () => {
      if (commitButton.dataset.previewReady !== 'true' && commitButton.dataset.pro !== 'true') {
        status.textContent = 'Run a preview before committing.';
        return;
      }
      if (!lastPreview) {
        status.textContent = 'Run a preview before committing.';
        return;
      }
      status.textContent = 'Committing import…';
      try {
        const result = await API.post('/import/commit', {
          path: lastPreview.path,
          password: lastPreview.password,
        });
        if (result && result.locked) {
          return;
        }
        status.textContent = JSON.stringify(result, null, 2);
        commitButton.dataset.previewReady = 'false';
        enforcePreviewLock();
      } catch (error) {
        status.textContent = 'Commit failed: ' + (error && error.message ? error.message : String(error));
      }
    });

    container.addEventListener('DOMNodeRemoved', event => {
      if (event.target === container) {
        document.removeEventListener('license:updated', enforcePreviewLock);
      }
    });
  }

  function init() {}

  if (window.Cards && typeof window.Cards.register === 'function') {
    window.Cards.register('backup', { init, render });
  }
})();
