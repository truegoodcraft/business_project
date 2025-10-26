(function () {
  var state = { deps: null, cards: {} };
  function provideDeps(deps) {
    if (state.deps) return;
    state.deps = deps;
    // Replace shim with real registerCard
    window.registerCard = function (name, factory) {
      if (!name || typeof factory !== 'function') return;
      state.cards[name] = factory(state.deps);
      window.Cards = state.cards;
    };
    // Drain any queued cards from shim
    var q = window.__cardQueue || [];
    for (var i = 0; i < q.length; i++) {
      var pair = q[i];
      try { window.registerCard(pair[0], pair[1]); } catch (e) { console.error('Card init failed:', pair[0], e); }
    }
    // Clear queue reference
    window.__cardQueue = [];
    window.Cards = state.cards;
  }
  function getCard(name) { return state.cards[name]; }
  window.CardBus = { provideDeps: provideDeps, getCard: getCard };
})();
