/* SPDX-License-Identifier: AGPL-3.0-or-later */
// core/ui/js/routes/home.js
import { registerRoute } from '../router.js';
import { mountHome } from '../cards/home.js';

registerRoute('/home', (root) => {
  const container = document.createElement('div');
  container.setAttribute('data-role', 'home-screen');
  root.innerHTML = '';
  root.appendChild(container);
  // mountHome looks up [data-role="home-screen"] in the document
  mountHome();
});
