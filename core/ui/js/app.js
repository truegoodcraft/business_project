(function(){
  const initializedCards = new WeakSet();

  if (!window.Cards || typeof window.Cards.register !== 'function') {
    window.Cards = {
      register(name, module){
        if (!name || !module || typeof module.render !== 'function') {
          console.warn('Card registration skipped for', name);
          return;
        }
        if (typeof window.registerCard === 'function') {
          window.registerCard(name, () => module);
        }
      }
    };
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

  function initVersion(){
    const node = document.getElementById('app-version');
    if (!node) return;
    const value = (typeof window.APP_VERSION === 'string' && window.APP_VERSION.trim()) ? window.APP_VERSION.trim() : 'v0.6';
    node.textContent = value;
  }

  function ensureCardInit(name, card){
    if (!card || typeof card.init !== 'function' || initializedCards.has(card)) {
      return;
    }
    try {
      card.init();
    } catch (error) {
      console.error('Card init failed:', name, error);
    } finally {
      initializedCards.add(card);
    }
  }

  async function renderCard(name, main){
    if (!main || !window.CardBus) {
      return;
    }
    main.innerHTML = '';
    const container = document.createElement('div');
    container.className = 'card';
    main.appendChild(container);
    const card = window.CardBus.getCard(name);
    if (!card || typeof card.render !== 'function') {
      container.textContent = 'Module unavailable.';
      return;
    }
    ensureCardInit(name, card);
    try {
      await Promise.resolve(card.render(container));
    } catch (error) {
      container.textContent = 'Error: ' + (error && error.message ? error.message : String(error));
      console.error('Card render failed:', name, error);
    }
  }

  function initTabs(main){
    const buttons = Array.from(document.querySelectorAll('.sidebar-tab'));
    async function activate(name){
      buttons.forEach(button => {
        const isActive = button.dataset.tab === name;
        button.classList.toggle('active', isActive);
      });
      if (name) {
        await renderCard(name, main);
      }
    }
    buttons.forEach(button => {
      button.addEventListener('click', event => {
        event.preventDefault();
        const { tab } = button.dataset || {};
        if (tab) {
          activate(tab);
        }
      });
    });
    return { buttons, activate };
  }

  document.addEventListener('DOMContentLoaded', async () => {
    if (!window.API || !window.Dom || !window.Modals || !window.CardBus) {
      console.error('Bootstrap deps missing');
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

    let licenseData = null;
    try {
      licenseData = await window.API.loadLicense();
    } catch (error) {
      console.error('License load failed', error);
    }

    CardBus.provideDeps({ API: window.API, Dom: window.Dom, Modals: window.Modals });

    if (licenseData) {
      updateLicenseBadge(licenseData);
    } else {
      updateLicenseBadge(null);
    }

    const main = document.getElementById('main');
    if (!main) {
      return;
    }

    const tabs = initTabs(main);

    const defaultCard = window.CardBus.getCard('inventory');
    if (defaultCard && typeof defaultCard.render === 'function') {
      tabs.activate('inventory');
      return;
    }

    const available = Object.keys(window.Cards || {}).filter(name => {
      const card = window.CardBus.getCard(name);
      return card && typeof card.render === 'function';
    });

    if (available.length > 0) {
      tabs.activate(available[0]);
    } else {
      console.warn('No cards registered.');
    }
  });
})();
