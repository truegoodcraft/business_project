// Tools screen mount (minimal, no external side effects)
export function mountTools() {
  const home = document.querySelector('[data-role="home-screen"]');
  const tools = document.querySelector('[data-role="tools-screen"]');

  // Show Tools screen, hide Home
  if (home) home.classList.add('hidden');
  if (tools) {
    tools.classList.remove('hidden');

    // Simple placeholder list of tools (only if not already present)
    if (!tools.querySelector('[data-role="tools-list"]')) {
      const list = document.createElement('ul');
      list.setAttribute('data-role', 'tools-list');
      list.style.margin = '0 0 12px 0';
      list.innerHTML = `
        <li>Manufacturing</li>
        <li>Tasks</li>
        <li>Backup</li>
      `;
      tools.prepend(list);
    }
  }
}
