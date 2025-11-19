// Tools screen mount (list-only; no external side effects)
export function mountTools() {
  const toolsScreen = document.querySelector('[data-role="tools-screen"]');
  const legacyToolsSection = toolsScreen?.querySelector('section[data-route="tools"]');
  const toolsList = toolsScreen?.querySelector('[data-role="tools-list"]');

  if (!toolsScreen) return;

  // Show Tools surface; ensure only list shows
  toolsScreen.classList.remove('hidden');
  if (legacyToolsSection) legacyToolsSection.classList.add('hidden');
  if (toolsList) toolsList.classList.remove('hidden');

  // Defensive: hide any stray "Contacts" card inside Tools wrapper if present
  toolsScreen.querySelectorAll('*').forEach(el => {
    const heading = el.matches('h2,h3,h4') ? el.textContent?.trim().toLowerCase() : '';
    if (heading === 'contacts') {
      const card = el.closest('.card, section, div');
      if (card) card.classList.add('hidden');
    }
  });
}
