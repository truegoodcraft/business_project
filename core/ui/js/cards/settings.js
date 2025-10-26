(function(){
  const { el } = window.DOM || {};
  const API = window.API;

  async function render(container){
    if (!el || !API) {
      container.textContent = 'UI helpers unavailable.';
      return;
    }

    const title = el('h2', {}, 'Settings');
    const licensePre = el('pre', { class: 'status-box', style: { minHeight: '160px' } }, 'Loading license…');
    const featuresList = el('ul', { class: 'badge-note' });
    const reloadButton = el('button', { type: 'button' }, 'Reload License');
    const writesStatus = el('div', { class: 'status-box' }, 'Writes Enabled: true');

    container.replaceChildren(
      title,
      el('section', {}, [
        el('div', { class: 'section-title' }, 'License'),
        reloadButton,
        licensePre,
        el('div', { class: 'section-title' }, 'Features'),
        featuresList,
      ]),
      el('section', {}, [
        el('div', { class: 'section-title' }, 'Writes Toggle'),
        el('div', { class: 'badge-note' }, 'Controlled from the header. This value is read-only here.'),
        writesStatus,
      ]),
    );

    function updateWrites(){
      const enabled = document.body.dataset.writesEnabled !== 'false';
      writesStatus.textContent = `Writes Enabled: ${enabled}`;
    }

    function renderFeatures(license){
      featuresList.innerHTML = '';
      const features = (license && license.features) || {};
      const entries = Object.keys(features);
      if (!entries.length) {
        featuresList.appendChild(el('li', {}, 'No feature flags present.'));
        return;
      }
      entries.forEach(key => {
        featuresList.appendChild(el('li', {}, `${key}: ${features[key] ? 'enabled' : 'disabled'}`));
      });
    }

    function updateLicenseView(license){
      licensePre.textContent = JSON.stringify(license || {}, null, 2);
      renderFeatures(license || {});
    }

    reloadButton.addEventListener('click', async () => {
      licensePre.textContent = 'Reloading…';
      try {
        const license = await API.loadLicense(true);
        updateLicenseView(license);
      } catch (error) {
        licensePre.textContent = 'Reload failed: ' + (error && error.message ? error.message : String(error));
      }
    });

    const onLicenseUpdated = event => updateLicenseView(event.detail);
    document.addEventListener('license:updated', onLicenseUpdated);
    document.addEventListener('writes:changed', updateWrites);

    updateWrites();
    try {
      const license = await API.loadLicense();
      updateLicenseView(license);
    } catch (error) {
      licensePre.textContent = 'Failed to load license: ' + (error && error.message ? error.message : String(error));
    }

    container.addEventListener('DOMNodeRemoved', event => {
      if (event.target === container) {
        document.removeEventListener('license:updated', onLicenseUpdated);
        document.removeEventListener('writes:changed', updateWrites);
      }
    });
  }

  if (window.Cards && typeof window.Cards.register === 'function') {
    window.Cards.register('settings', { render });
  }
})();
