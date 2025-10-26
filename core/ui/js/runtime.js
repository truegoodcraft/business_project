(function () {
  const state = {
    deps: null,
    queue: [],
    cards: {}
  };
  function ready() { return !!state.deps; }
  function provideDeps(deps) {
    if (state.deps) return;
    state.deps = deps;
    // Drain queue
    for (const [name, factory] of state.queue) {
      state.cards[name] = factory(state.deps);
    }
    state.queue.length = 0;
    window.Cards = state.cards;
  }
  function registerCard(name, factory) {
    if (!name || typeof factory !== 'function') return;
    if (ready()) {
      state.cards[name] = factory(state.deps);
      window.Cards = state.cards;
    } else {
      state.queue.push([name, factory]);
    }
  }
  function getCard(name) { return state.cards[name]; }
  window.CardBus = { provideDeps, registerCard, getCard };
  window.registerCard = registerCard; // convenience for cards
})();
