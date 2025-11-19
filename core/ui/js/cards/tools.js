// Tools screen mount: list-only, prevent legacy content from showing
export function mountTools() {
  const toolsScreen = document.querySelector('[data-role="tools-screen"]');
  if (!toolsScreen) return;

  // Ensure only the list is visible
  const toolsList = toolsScreen.querySelector('[data-role="tools-list"]');
  const legacySection = toolsScreen.querySelector('section[data-route="tools"]');

  toolsScreen.classList.remove('hidden');
  if (toolsList) toolsList.classList.remove('hidden');
  if (legacySection) legacySection.classList.add('hidden');

  // Extra safety: hide any Contacts card accidentally injected under Tools
  toolsScreen.querySelectorAll('.card, section, div').forEach(el => {
    const h = el.querySelector('h2,h3,h4');
    if (h && h.textContent && h.textContent.trim().toLowerCase() === 'contacts') {
      el.classList.add('hidden');
    }
  });
}
