export function mountHome() {
  const container = document.querySelector('[data-role="home-screen"]');
  if (!container) return;
  container.classList.remove('hidden');
  // stub data
  document.querySelector('[data-role="net-30"]').textContent = 'Net (Last 30 Days): $0.00';
  document.querySelector('[data-role="recent-transactions"] tbody').innerHTML = '';
}
