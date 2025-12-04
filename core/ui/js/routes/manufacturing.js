// core/ui/js/routes/manufacturing.js
import { registerRoute } from '../router.js';
import { mountManufacturing, unmountManufacturing } from '../cards/manufacturing.js';

registerRoute('/manufacturing', mount);

let watcherBound = false;

function bindUnmountWatcher() {
  if (watcherBound) return;
  watcherBound = true;
  window.addEventListener('hashchange', () => {
    if (!location.hash.includes('/manufacturing')) {
      unmountManufacturing();
    }
  });
}

async function mount(root) {
  unmountManufacturing();
  root.innerHTML = '';
  let host = root.querySelector('[data-tab-panel="manufacturing"]');
  if (!host) {
    host = document.createElement('div');
    host.setAttribute('data-tab-panel', 'manufacturing');
    root.append(host);
  }
  bindUnmountWatcher();
  await mountManufacturing();
}
