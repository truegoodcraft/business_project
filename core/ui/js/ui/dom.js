(function(){
  function $(selector, root){
    return (root || document).querySelector(selector);
  }

  function createText(value){
    return document.createTextNode(String(value));
  }

  function el(tag, attrs, children){
    const node = document.createElement(tag);
    const options = attrs || {};
    Object.entries(options).forEach(([key, value]) => {
      if (value === undefined || value === null) {
        return;
      }
      if (key === 'class' || key === 'className') {
        node.className = String(value);
      } else if (key === 'text') {
        node.textContent = String(value);
      } else if (key === 'dataset' && typeof value === 'object') {
        Object.entries(value).forEach(([dataKey, dataValue]) => {
          if (dataValue === undefined || dataValue === null) return;
          node.dataset[dataKey] = String(dataValue);
        });
      } else if (key === 'style' && typeof value === 'object') {
        Object.assign(node.style, value);
      } else if (key.startsWith('on') && typeof value === 'function') {
        node.addEventListener(key.slice(2), value);
      } else {
        node.setAttribute(key, String(value));
      }
    });

    const list = Array.isArray(children) ? children : (children !== undefined ? [children] : []);
    list.forEach(child => {
      if (child === undefined || child === null) {
        return;
      }
      if (child instanceof Node) {
        node.appendChild(child);
      } else {
        node.appendChild(createText(child));
      }
    });
    return node;
  }

  function ensureBadge(button){
    if (!button) return null;
    const existing = button.querySelector(':scope > .pro-badge');
    if (existing) return existing;
    const badge = document.createElement('span');
    badge.className = 'pro-badge';
    badge.textContent = 'Pro Feature';
    button.appendChild(badge);
    return badge;
  }

  function removeBadge(button){
    const badge = button && button.querySelector(':scope > .pro-badge');
    if (badge) {
      badge.remove();
    }
  }

  function bindDisabledWithProGate(button, featureName){
    if (!(button instanceof HTMLElement) || !featureName) {
      return;
    }
    if (button.dataset.proGateBound === 'true') {
      return;
    }
    button.dataset.proGateBound = 'true';

    function refresh(){
      const api = window.API;
      const enabled = api && typeof api.feature === 'function' ? api.feature(featureName) : false;
      if (!enabled) {
        button.disabled = true;
        button.dataset.pro = 'true';
        ensureBadge(button);
      } else {
        button.disabled = false;
        button.dataset.pro = 'false';
        removeBadge(button);
      }
    }

    document.addEventListener('license:updated', refresh);
    refresh();
    return { refresh };
  }

  window.Dom = { $, el, bindDisabledWithProGate };
  // Maintain backwards compatibility with any legacy code paths that still
  // reference the old uppercase namespace.
  window.DOM = window.Dom;
})();
