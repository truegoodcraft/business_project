(function () {
  var state = { deps: null, cards: {} };
  function provideDeps(deps) {
    if (state.deps) return;
    state.deps = deps;
    window.registerCard = function (name, factory) {
      state.cards[name] = factory(state.deps);
      window.Cards = state.cards;
    };
    var q = window.__cardQueue || [];
    for (var i = 0; i < q.length; i++) { window.registerCard(q[i][0], q[i][1]); }
    window.__cardQueue = [];
  }
  function getCard(name) { return state.cards[name]; }
  window.CardBus = { provideDeps: provideDeps, getCard: getCard };
})();
