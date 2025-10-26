// card-queue.js — zero-dep helper
(function (w) {
  if (!w.__cardQueue) w.__cardQueue = [];
  if (typeof w.enqueueCard !== 'function') {
    w.enqueueCard = function (name, factory) { w.__cardQueue.push([name, factory]); };
  }
})(window);
