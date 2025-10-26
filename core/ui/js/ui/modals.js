(function(){
  const { el } = window.Dom || {};

  function factory(){
    return typeof el === 'function' ? el : function(tag, attrs, children){
      const node = document.createElement(tag);
      if (attrs) {
        Object.entries(attrs).forEach(([key, value]) => {
          if (value === undefined || value === null) return;
          if (key === 'class') node.className = String(value);
          else node.setAttribute(key, String(value));
        });
      }
      const list = Array.isArray(children) ? children : [children];
      list.forEach(child => {
        if (child === undefined || child === null) return;
        if (child instanceof Node) node.appendChild(child);
        else node.appendChild(document.createTextNode(String(child)));
      });
      return node;
    };
  }

  const makeEl = factory();

  function getRoot(){
    return document.getElementById('modal-root');
  }

  function close(){
    const root = getRoot();
    if (root) {
      root.innerHTML = '';
    }
    document.body.classList.remove('modal-open');
  }

  function render(title, content, actions){
    const root = getRoot();
    if (!root) return;
    root.innerHTML = '';

    const overlay = makeEl('div', { class: 'modal-overlay' });
    const modal = makeEl('div', { class: 'modal' });
    const heading = makeEl('h3', null, title || 'Notice');

    let bodyContent;
    if (content instanceof Node) {
      bodyContent = content;
    } else {
      bodyContent = makeEl('p', null, content || '');
    }

    const buttons = makeEl('div', { class: 'modal-actions' });
    (actions || []).forEach(action => {
      const variant = action.variant || (action.danger ? 'danger' : '');
      const classes = ['modal-btn'];
      if (variant === 'secondary') classes.push('secondary');
      if (variant === 'danger' || action.danger) classes.push('danger');
      const button = makeEl('button', { type: 'button', class: classes.join(' ') }, action.label || 'OK');
      button.addEventListener('click', () => {
        try {
          if (typeof action.onClick === 'function') {
            action.onClick();
          }
        } finally {
          if (!action.keepOpen) {
            close();
          }
        }
      });
      buttons.appendChild(button);
    });

    modal.appendChild(heading);
    modal.appendChild(bodyContent);
    modal.appendChild(buttons);
    overlay.appendChild(modal);

    overlay.addEventListener('click', event => {
      if (event.target === overlay) {
        close();
      }
    });

    root.appendChild(overlay);
    document.body.classList.add('modal-open');
  }

  const Modals = {
    alert(title, message){
      render(title, message, [
        { label: 'Close', variant: 'secondary' },
      ]);
    },
    confirm(title, message, onYes){
      render(title, message, [
        { label: 'Cancel', variant: 'secondary' },
        { label: 'Confirm', variant: 'danger', onClick: () => { if (typeof onYes === 'function') onYes(); } },
      ]);
    },
    close,
  };

  window.Modals = window.Modals || {};
  Object.assign(window.Modals, Modals);
})();
