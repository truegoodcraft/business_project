// prelude.js — must load before any card
(function () {
  if (!window.__cardQueue) window.__cardQueue = [];
  if (typeof window.registerCard !== 'function') {
    window.registerCard = function (name, factory) {
      window.__cardQueue.push([name, factory]);
      if (window.__diag) console.log('[DIAG] prelude queued:', name);
    };
  }
  if (!window.__diag) window.__diag = { log: m => console.log('[DIAG]', m) };
  window.__diag.log('prelude installed');
})();
