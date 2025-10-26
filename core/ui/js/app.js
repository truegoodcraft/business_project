(function(){
  const existing = (window.Cards && typeof window.Cards === 'object') ? window.Cards : {};
  const registry = existing.registry && typeof existing.registry === 'object' ? existing.registry : {};

  const Cards = Object.assign(existing, {
    registry,
    active: existing.active || null,
    register(name, module){
      if (!name || typeof module !== 'object' || typeof module.render !== 'function') {
        console.warn('Card registration skipped for', name);
        return;
      }
      this.registry[name] = module;
      this[name] = module;
      if (typeof module.init === 'function') {
        try {
          module.init();
        } catch (error) {
          console.error('Card init failed:', name, error);
        }
      }
    },
    async render(name){
      const main = document.getElementById('main');
      if (!main) return;
      this.active = name;
      main.innerHTML = '';
      const cardContainer = document.createElement('div');
      cardContainer.className = 'card';
      main.appendChild(cardContainer);
      const card = this.registry[name];
      if (!card || typeof card.render !== 'function') {
        cardContainer.textContent = 'Module unavailable.';
        return;
      }
      try {
        await Promise.resolve(card.render(cardContainer));
      } catch (error) {
        cardContainer.textContent = 'Error: ' + (error && error.message ? error.message : String(error));
        console.error('Card render failed:', name, error);
      }
    },
  });

  window.Cards = Cards;

  function helpersReady(){
    let ok = true;
    if (!window.API) {
      console.error('Missing helper: API');
      ok = false;
    }
    if (!window.Dom) {
      console.error('Missing helper: Dom');
      ok = false;
    }
    if (!window.Modals) {
      console.error('Missing helper: Modals');
      ok = false;
    }
    return ok;
  }

  function updateLicenseBadge(license){
    const badge = document.getElementById('license-badge');
    if (!badge) return;
    const tier = license && typeof license.tier === 'string' ? license.tier.trim() : '';
    badge.textContent = tier ? tier : 'Unknown';
  }

  function syncWritesToggle(toggle){
    const enabled = toggle.checked;
    document.body.dataset.writesEnabled = enabled ? 'true' : 'false';
    toggle.setAttribute('aria-checked', String(enabled));
    const label = document.getElementById('writes-toggle-status');
    if (label) {
      label.textContent = enabled ? 'Writes Enabled' : 'Writes Disabled';
    }
    document.dispatchEvent(new CustomEvent('writes:changed', { detail: { enabled } }));
  }

  function initTabs(){
    const buttons = Array.from(document.querySelectorAll('.sidebar-tab'));
    function activate(name){
      buttons.forEach(button => {
        const isActive = button.dataset.tab === name;
        button.classList.toggle('active', isActive);
      });
      if (name) {
        Cards.render(name);
      }
    }
    buttons.forEach(button => {
      button.addEventListener('click', event => {
        event.preventDefault();
        const { tab } = button.dataset;
        activate(tab);
      });
    });
    return { buttons, activate };
  }

  function initVersion(){
    const node = document.getElementById('app-version');
    if (!node) return;
    const value = (typeof window.APP_VERSION === 'string' && window.APP_VERSION.trim()) ? window.APP_VERSION.trim() : 'v0.6';
    node.textContent = value;
  }

  async function bootstrapLicense(){
    try {
      const license = await window.API.loadLicense();
      updateLicenseBadge(license);
    } catch (error) {
      updateLicenseBadge(null);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (!helpersReady()) {
      console.error('UI initialization halted due to missing helpers.');
      return;
    }

    if (!document.body.dataset.writesEnabled) {
      document.body.dataset.writesEnabled = 'true';
    }

    initVersion();

    const toggle = document.getElementById('writes-toggle');
    if (toggle) {
      if (toggle.checked === undefined) {
        toggle.checked = true;
      }
      syncWritesToggle(toggle);
      toggle.addEventListener('change', () => syncWritesToggle(toggle));
    }

    document.addEventListener('license:updated', event => {
      updateLicenseBadge(event.detail);
    });

    bootstrapLicense();

    const tabs = initTabs();
    const defaultTab = Cards.inventory ? 'inventory' : Object.keys(Cards.registry)[0];
    if (defaultTab) {
      tabs.activate(defaultTab);
    } else {
      console.warn('No cards registered.');
    }
  });
})();
