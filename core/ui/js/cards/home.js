/* SPDX-License-Identifier: AGPL-3.0-or-later */
import { apiGetJson, rawFetch } from '../api.js';
import { getAuthState } from '../auth.js';
import { runUpdateCheck } from '../update-check.js';

function mountHome() { return renderHome(); }
export { mountHome as default, mountHome };

const VERSION_NOTICE_KEY = 'bus.home.versionNoticeState';
const DISMISSED_NOTICE_KEY = 'bus.home.dismissedNotices';

const ACTIONS = {
  addSupply: { href: '#/inventory', label: 'Add Supply', hint: 'Create a material or consumable' },
  adjustInventory: { href: '#/inventory', label: 'Adjust Inventory', hint: 'Stock in, consume, or correct' },
  createBlueprint: { href: '#/recipes', label: 'Create Blueprint', hint: 'Define recipe and costs' },
  buildProduct: { href: '#/manufacturing', label: 'Build Product', hint: 'Run production from a blueprint' },
};

function readJsonStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeJsonStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {}
}

function versionNoticeState() {
  const state = readJsonStorage(VERSION_NOTICE_KEY, {});
  return {
    lastSeenVersion: state?.lastSeenVersion || null,
    dismissedUpdatePairs: Array.isArray(state?.dismissedUpdatePairs) ? state.dismissedUpdatePairs : [],
  };
}

function saveVersionNoticeState(state) {
  writeJsonStorage(VERSION_NOTICE_KEY, {
    lastSeenVersion: state?.lastSeenVersion || null,
    dismissedUpdatePairs: Array.isArray(state?.dismissedUpdatePairs) ? state.dismissedUpdatePairs : [],
  });
}

function dismissedNotices() {
  const value = readJsonStorage(DISMISSED_NOTICE_KEY, []);
  return Array.isArray(value) ? value : [];
}

function dismissNotice(id) {
  const existing = dismissedNotices();
  if (!existing.includes(id)) writeJsonStorage(DISMISSED_NOTICE_KEY, [...existing, id]);
}

function asCount(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function plural(count, noun) {
  if (count === null) return `Unknown ${noun}`;
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatDateTime(value) {
  const numeric = Number(value);
  const date = Number.isFinite(numeric) ? new Date(numeric * 1000) : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function actionLink(action, extraClass = '') {
  return `<a class="bus-home-btn ${extraClass}" href="${action.href}"><span class="bus-home-btn-label">${action.label}</span><span class="bus-home-btn-hint">${action.hint}</span></a>`;
}

function statusRow(label, value, tone = '') {
  const toneAttr = tone ? ` data-tone="${tone}"` : '';
  return `<div class="bus-home-status-row"><span>${label}</span><strong${toneAttr}>${value}</strong></div>`;
}

async function setVersionInto(el) {
  try {
    const res = await rawFetch('/openapi.json', { credentials: 'include' });
    const j = await res.json();
    if (j?.info?.version) {
      el.textContent = j.info.version;
      return j.info.version;
    }
  } catch {}

  const shell = document.querySelector('[data-role="ui-version"]');
  if (shell && shell.textContent.trim()) {
    const version = shell.textContent.trim();
    el.textContent = version;
    return version;
  }
  el.textContent = 'unknown';
  return 'unknown';
}

async function fetchHomeData(currentVersion) {
  const [system, exportsRes, auth, update] = await Promise.all([
    apiGetJson('/app/system/state').catch(() => null),
    apiGetJson('/app/db/exports').catch(() => null),
    getAuthState().catch(() => null),
    runUpdateCheck().catch(() => null),
  ]);

  const counts = system?.counts || {};
  const exportsList = Array.isArray(exportsRes?.exports) ? exportsRes.exports : null;
  return {
    currentVersion: system?.build?.version || currentVersion || 'unknown',
    counts: {
      supplies: asCount(counts.items),
      blueprints: asCount(counts.recipes),
      builds: asCount(counts.manufacturing_runs),
      movements: asCount(counts.movements),
      cashEvents: asCount(counts.cash_events),
    },
    busMode: system?.bus_mode || null,
    backup: {
      exports: exportsList,
      latest: exportsList?.[0] || null,
    },
    auth,
    update,
  };
}

function shopState(counts) {
  const supplies = counts.supplies;
  const blueprints = counts.blueprints;
  const builds = counts.builds;
  if (supplies === 0) return 'no-supplies';
  if (supplies !== null && supplies > 0 && blueprints === 0) return 'no-blueprints';
  if (blueprints !== null && blueprints > 0 && builds === 0) return 'no-builds';
  return 'active';
}

function renderSetupSteps() {
  return `
    <ol class="bus-home-steps">
      <li><span>1</span><strong>Add your first supply</strong></li>
      <li><span>2</span><strong>Create a blueprint</strong></li>
      <li><span>3</span><strong>Build your first product</strong></li>
    </ol>
    <div class="bus-home-action-row">
      ${actionLink(ACTIONS.addSupply, 'bus-home-btn--primary')}
      ${actionLink(ACTIONS.createBlueprint)}
      ${actionLink(ACTIONS.buildProduct)}
    </div>`;
}

function renderNextStep(title, action) {
  return `
    <div class="bus-home-next-step">
      <p>${title}</p>
      <div class="bus-home-action-row bus-home-action-row--single">${actionLink(action, 'bus-home-btn--primary')}</div>
    </div>`;
}

function renderActiveShop(data) {
  const { counts, backup, update } = data;
  const latestExport = backup.latest ? formatDateTime(backup.latest.modified) : null;
  const attention = [];
  if (update?.update_available && update?.latest_version) attention.push(`Update available: ${escapeHtml(update.latest_version)}`);
  if (backup.exports && backup.exports.length === 0) attention.push('No local backup export found yet.');
  if (!attention.length) attention.push('No urgent items detected from available local data.');

  const activityParts = [];
  if (counts.builds !== null) activityParts.push(plural(counts.builds, 'build'));
  if (counts.movements !== null) activityParts.push(plural(counts.movements, 'inventory movement'));
  if (counts.cashEvents !== null) activityParts.push(plural(counts.cashEvents, 'cash event'));

  return `
    <div class="bus-home-ops-grid">
      <section class="bus-home-mini-card">
        <h3>What needs attention</h3>
        <ul>${attention.map((item) => `<li>${item}</li>`).join('')}</ul>
      </section>
      <section class="bus-home-mini-card">
        <h3>Shop snapshot</h3>
        ${statusRow('Supplies', counts.supplies === null ? 'Unavailable' : String(counts.supplies))}
        ${statusRow('Blueprints', counts.blueprints === null ? 'Unavailable' : String(counts.blueprints))}
        ${statusRow('Builds', counts.builds === null ? 'Unavailable' : String(counts.builds))}
      </section>
      <section class="bus-home-mini-card bus-home-mini-card--actions">
        <h3>Quick actions</h3>
        <div class="bus-home-quick-actions">
          ${actionLink(ACTIONS.addSupply)}
          ${actionLink(ACTIONS.adjustInventory)}
          ${actionLink(ACTIONS.createBlueprint)}
          ${actionLink(ACTIONS.buildProduct)}
        </div>
      </section>
      <section class="bus-home-mini-card">
        <h3>Recent activity</h3>
        <p>${activityParts.length ? activityParts.join(' · ') : 'Recent activity is not available on Home yet.'}</p>
        <p>${latestExport ? `Last export: ${escapeHtml(latestExport)}` : 'Backup history appears after your first export.'}</p>
      </section>
    </div>`;
}

function renderBench(data) {
  const state = shopState(data.counts);
  if (state === 'no-supplies') {
    return `<h2>Start your shop setup</h2>${renderSetupSteps()}`;
  }
  if (state === 'no-blueprints') {
    return `<h2>Shop bench</h2>${renderNextStep('Next useful step: Create a blueprint from your supplies.', ACTIONS.createBlueprint)}`;
  }
  if (state === 'no-builds') {
    return `<h2>Shop bench</h2>${renderNextStep('Next useful step: Build your first product from a blueprint.', ACTIONS.buildProduct)}`;
  }
  return `<h2>Shop bench</h2>${renderActiveShop(data)}`;
}

function updatePair(currentVersion, latestVersion) {
  return `${currentVersion || 'unknown'}->${latestVersion || 'unknown'}`;
}

function isUpdatePairDismissed(currentVersion, latestVersion) {
  return versionNoticeState().dismissedUpdatePairs.includes(updatePair(currentVersion, latestVersion));
}

function buildNotices(data) {
  const notices = [];
  const dismissed = dismissedNotices();
  const versionState = versionNoticeState();
  const currentVersion = data.currentVersion || 'unknown';
  const update = data.update;
  if (update?.update_available && update?.latest_version) {
    const pair = updatePair(currentVersion, update.latest_version);
    if (!versionState.dismissedUpdatePairs.includes(pair)) {
      notices.push({ id: `update:${pair}`, tone: 'warn', text: `New version available: ${update.latest_version}.` });
    }
  } else if (currentVersion !== 'unknown' && versionState.lastSeenVersion && versionState.lastSeenVersion !== currentVersion) {
    notices.push({ id: `updated:${currentVersion}`, tone: 'good', text: `Updated to current version ${currentVersion}.` });
  }

  if (data.auth && data.auth.owner_exists === false && !dismissed.includes('local-owner-missing')) {
    notices.push({ id: 'local-owner-missing', tone: 'warn', text: 'Local owner is not set yet.', actionHref: '#/security', actionText: 'Set local owner' });
  }

  if (data.backup.exports && data.backup.exports.length === 0 && !dismissed.includes('backup-export-missing')) {
    notices.push({ id: 'backup-export-missing', tone: 'warn', text: 'No local backup export has been found yet.', actionHref: '#/settings', actionText: 'Open backup settings' });
  }
  return notices;
}

function renderNotices(data) {
  const notices = buildNotices(data);
  if (!notices.length) return '<div class="bus-home-alert-strip bus-home-alert-strip--empty" aria-live="polite"></div>';
  return `<div class="bus-home-alert-strip" aria-live="polite">${notices.map((notice) => `
    <div class="bus-home-alert" data-tone="${notice.tone}" data-notice-id="${escapeHtml(notice.id)}">
      <span>${escapeHtml(notice.text)}</span>
      ${notice.actionHref ? `<a href="${notice.actionHref}">${notice.actionText}</a>` : ''}
      <button type="button" aria-label="Dismiss notice" data-dismiss-notice="${escapeHtml(notice.id)}">Dismiss</button>
    </div>`).join('')}</div>`;
}

function renderUpdateCard(data) {
  const currentVersion = data.currentVersion || 'unknown';
  const update = data.update;
  const hasUpdate = !!(update?.update_available && update?.latest_version);
  const currentSeen = versionNoticeState().lastSeenVersion === currentVersion;
  const hiddenByUpdateDismiss = hasUpdate && isUpdatePairDismissed(currentVersion, update.latest_version);
  if (hasUpdate && !hiddenByUpdateDismiss) {
    return `
      <section class="bus-home-side-card" data-role="home-update-card">
        <div class="bus-home-side-card-head"><h3>Latest update</h3><button type="button" data-dismiss-update-card>Dismiss</button></div>
        <p>Version ${escapeHtml(update.latest_version)} is available.</p>
        <a href="#/settings">Review update settings</a>
      </section>`;
  }
  if (!currentSeen && currentVersion !== 'unknown') {
    return `
      <section class="bus-home-side-card" data-role="home-update-card">
        <div class="bus-home-side-card-head"><h3>Latest update</h3><button type="button" data-dismiss-update-card>Dismiss</button></div>
        <p>Running BUS Core ${escapeHtml(currentVersion)}.</p>
      </section>`;
  }
  return `
    <section class="bus-home-side-card">
      <h3>Latest update</h3>
      <p>${update ? 'BUS Core is up to date.' : 'Update status is unavailable right now.'}</p>
    </section>`;
}

function renderSystemPanel(data) {
  const latestExport = data.backup.latest;
  const exportTime = latestExport ? formatDateTime(latestExport.modified) : null;
  const backupStatus = data.backup.exports === null
    ? 'Unavailable'
    : exportTime || 'No export found';
  return `
    <aside class="bus-home-side" aria-label="System and support">
      <section class="bus-home-side-card">
        <h3>System trust</h3>
        ${statusRow('Version', escapeHtml(data.currentVersion || 'unknown'))}
        ${statusRow('Storage', 'Local', 'good')}
        ${statusRow('Telemetry', 'Off', 'good')}
        ${statusRow('Backup', escapeHtml(backupStatus), data.backup.latest ? 'good' : 'warn')}
        <a href="#/settings">Data location</a>
      </section>
      ${renderUpdateCard(data)}
      <section class="bus-home-side-card">
        <h3>Support</h3>
        <div class="bus-home-link-list">
          <a href="/brand/README.md" target="_blank" rel="noopener noreferrer">Docs</a>
          <a href="/brand/wiki/Bug-Reports.md" target="_blank" rel="noopener noreferrer">Bug Report</a>
          <a href="https://discord.gg/qp3rc5CxdM" target="_blank" rel="noopener noreferrer">Discord</a>
          <a href="/license/LICENSE.md" target="_blank" rel="noopener noreferrer">License</a>
        </div>
      </section>
      <section class="bus-home-side-card">
        <h3>Help</h3>
        <div class="bus-home-link-list">
          <a href="/license/EULA.md" target="_blank" rel="noopener noreferrer">How BUS Core Works</a>
          <a href="/brand/docs/DATA_LIFECYCLE.md" target="_blank" rel="noopener noreferrer">Data Safety</a>
          <a href="/brand/docs/ui_validation_matrix.md" target="_blank" rel="noopener noreferrer">Known Limits</a>
        </div>
      </section>
    </aside>`;
}

function renderDashboard(root, data) {
  root.querySelector('[data-role="home-alerts"]').innerHTML = renderNotices(data);
  root.querySelector('[data-role="home-bench"]').innerHTML = renderBench(data);
  root.querySelector('[data-role="home-side-panel"]').innerHTML = renderSystemPanel(data);

  root.querySelectorAll('[data-dismiss-notice]').forEach((button) => {
    button.addEventListener('click', () => {
      const id = button.getAttribute('data-dismiss-notice') || '';
      if (id.startsWith('update:')) {
        const state = versionNoticeState();
        const pair = id.slice('update:'.length);
        if (!state.dismissedUpdatePairs.includes(pair)) state.dismissedUpdatePairs.push(pair);
        saveVersionNoticeState(state);
      } else if (id.startsWith('updated:')) {
        const state = versionNoticeState();
        state.lastSeenVersion = data.currentVersion || state.lastSeenVersion;
        saveVersionNoticeState(state);
      } else {
        dismissNotice(id);
      }
      renderDashboard(root, data);
    });
  });

  root.querySelector('[data-dismiss-update-card]')?.addEventListener('click', () => {
    const state = versionNoticeState();
    if (data.update?.update_available && data.update?.latest_version) {
      const pair = updatePair(data.currentVersion, data.update.latest_version);
      if (!state.dismissedUpdatePairs.includes(pair)) state.dismissedUpdatePairs.push(pair);
    } else {
      state.lastSeenVersion = data.currentVersion || state.lastSeenVersion;
    }
    saveVersionNoticeState(state);
    renderDashboard(root, data);
  });
}

function hostRoot() {
  return document.querySelector('[data-role="home-screen"]')
    || document.querySelector('#app')
    || document.querySelector('#page')
    || document.querySelector('[data-role="page"]')
    || document.querySelector('main')
    || document.body;
}

function renderHome() {
  document.title = 'BUS Core - Home';
  const root = hostRoot();
  if (!root) return;

  // Home owns its own internal card layout; avoid inheriting legacy screen-level card shell.
  root.classList.remove('card');
  root.classList.add('home-screen-host');

  root.innerHTML = `
  <div class="bus-home" role="main">
    <div class="bus-home-wrap">
      <header class="bus-home-header">
        <div class="bus-home-brand">
          <h1>BUS Core</h1>
          <p>Local-first operating bench for inventory, blueprints, builds, and shop records.</p>
        </div>
        <div class="bus-home-meta" aria-label="Status">
          <div class="bus-home-meta-row">Version: <code id="bus-version">...</code></div>
          <div class="bus-home-meta-row">Storage: <span class="bus-home-kbd">Local</span></div>
          <div class="bus-home-meta-row">Telemetry: <span class="bus-home-kbd">Off</span></div>
        </div>
      </header>

      <div data-role="home-alerts"></div>
      <section class="bus-home-dashboard">
        <section class="bus-home-bench" data-role="home-bench">
          <h2>Shop bench</h2>
          <p class="bus-home-sub">Loading local shop state...</p>
        </section>
        <div data-role="home-side-panel"></div>
      </section>
    </div>
  </div>`;

  const ver = root.querySelector('#bus-version');
  const versionPromise = ver ? setVersionInto(ver) : Promise.resolve('unknown');
  versionPromise.then((currentVersion) => fetchHomeData(currentVersion)).then((data) => {
    renderDashboard(root, data);
  }).catch(() => {
    renderDashboard(root, {
      currentVersion: ver?.textContent?.trim() || 'unknown',
      counts: { supplies: null, blueprints: null, builds: null, movements: null, cashEvents: null },
      busMode: null,
      backup: { exports: null, latest: null },
      auth: null,
      update: null,
    });
  });
}
