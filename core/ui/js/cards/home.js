// SPDX-License-Identifier: AGPL-3.0-or-later

function metricCard(title, value, accent) {
  const card = document.createElement('div');
  card.className = 'metric-card';
  card.style.borderColor = accent;
  card.style.boxShadow = `0 0 0 1px ${accent} inset`;
  const h = document.createElement('h3');
  h.textContent = title;
  const v = document.createElement('div');
  v.style.fontSize = '24px';
  v.style.fontFamily = 'JetBrains Mono, Consolas, monospace';
  v.textContent = value;
  card.append(h, v);
  return card;
}

function toolTile(title, desc, link) {
  const tile = document.createElement('a');
  tile.href = link;
  tile.className = 'card';
  tile.style.textDecoration = 'none';
  tile.innerHTML = `<h3>${title}</h3><p>${desc}</p>`;
  return tile;
}

export function mountHome() {
  const container = document.querySelector('[data-role="home-screen"]');
  if (!container) return;
  container.classList.remove('hidden');

  const statsRow = document.createElement('div');
  statsRow.className = 'metric-grid';
  statsRow.append(
    metricCard('Active Items', '0', '#7c3aed'),
    metricCard('Vendors', '0', '#2563eb'),
    metricCard('Runs (7d)', '0', '#f59e0b'),
    metricCard('Net (30d)', '$0.00', '#22c55e'),
  );

  const tools = document.createElement('div');
  tools.className = 'metric-grid';
  tools.append(
    toolTile('Inventory', 'Manage stock levels and pricing.', '#/inventory'),
    toolTile('Vendors', 'Track supplier contacts and roles.', '#'),
    toolTile('Runs', 'Review recent manufacturing activity.', '#'),
  );

  container.innerHTML = '';
  container.append(statsRow, tools);
}
