(function () {
  var state = { deps: null, cards: {} };
  function provideDeps(deps) {
    if (state.deps) return;
    state.deps = deps;
    __diag && __diag.log('runtime.provideDeps');
    window.registerCard = function (name, factory) {
      if (!name || typeof factory !== 'function') return;
      __diag && __diag.log('runtime.registerCard: ' + name);
      state.cards[name] = factory(state.deps);
      window.Cards = state.cards;
    };
    var q = window.__cardQueue || [];
    __diag && __diag.log('runtime.drain size=' + q.length);
    for (var i = 0; i < q.length; i++) { try { window.registerCard(q[i][0], q[i][1]); } catch(e){ console.error('Card init failed:', q[i][0], e); } }
    window.__cardQueue = [];
  }
  function getCard(name){ return state.cards[name]; }
  window.CardBus = { provideDeps: provideDeps, getCard: getCard };
  __diag && __diag.log('runtime loaded');
})();
