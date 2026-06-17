/* SPDX-License-Identifier: AGPL-3.0-or-later */
import { apiGetJson, rawFetch } from '../api.js';
import { getAuthState } from '../auth.js';
import { runUpdateCheck } from '../update-check.js';

function mountHome() { return renderHome(); }
export { mountHome as default, mountHome };

const VERSION_NOTICE_KEY = 'bus.home.versionNoticeState';
const DISMISSED_NOTICE_KEY = 'bus.home.dismissedNotices';
const DISCORD_URL = 'https://discord.gg/qp3rc5CxdM';

const ACTIONS = {
  addSupply: { href: '#/inventory', label: 'Add Supply', hint: 'Create a material or consumable' },
  adjustInventory: { href: '#/inventory', label: 'Adjust Inventory', hint: 'Stock in, consume, or correct' },
  createBlueprint: { href: '#/recipes', label: 'Create Blueprint', hint: 'Define recipe and costs' },
  buildProduct: { href: '#/manufacturing', label: 'Build Product', hint: 'Run production from a blueprint' },
  viewJobs: { href: '#/jobs', label: 'View Jobs', hint: 'Open work commitments' },
};

const CLOSED_JOB_STATUSES = new Set(['done', 'cancelled']);

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

function formatDate(value) {
  if (!value) return 'No due date';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'No due date';
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatMoney(cents) {
  const value = Number(cents || 0) / 100;
  return value.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
}

function actionLink(action, extraClass = '') {
  return `<a class="bus-home-btn ${extraClass}" href="${action.href}"><span class="bus-home-btn-label">${action.label}</span><span class="bus-home-btn-hint">${action.hint}</span></a>`;
}

function statusRow(label, value, tone = '') {
  const toneAttr = tone ? ` data-tone="${tone}"` : '';
  return `<div class="bus-home-status-row"><span>${label}</span><strong${toneAttr}>${value}</strong></div>`;
}

function jobDueMeta(job) {
  if (!job?.due_date || CLOSED_JOB_STATUSES.has(job.status)) return { due: null, overdue: false, dueSoon: false };
  const due = new Date(job.due_date);
  if (Number.isNaN(due.getTime())) return { due: null, overdue: false, dueSoon: false };
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dueDay = new Date(due);
  dueDay.setHours(0, 0, 0, 0);
  const diffDays = Math.floor((dueDay.getTime() - today.getTime()) / 86400000);
  return { due, overdue: diffDays < 0, dueSoon: diffDays >= 0 && diffDays <= 7 };
}

function rankJobPressure(job) {
  const due = jobDueMeta(job);
  if (due.overdue) return 0;
  if (job.status === 'blocked') return 1;
  if (due.dueSoon) return 2;
  if (job.status === 'ready') return 3;
  if (job.status === 'active') return 4;
  return 5;
}

async function fetchJobsPressureData() {
  try {
    const jobs = await apiGetJson('/app/jobs');
    const list = Array.isArray(jobs) ? jobs : [];
    const attentionCandidates = list
      .filter((job) => !CLOSED_JOB_STATUSES.has(job.status))
      .sort((a, b) => {
        const rank = rankJobPressure(a) - rankJobPressure(b);
        if (rank !== 0) return rank;
        return String(a.due_date || '9999').localeCompare(String(b.due_date || '9999'));
      })
      .slice(0, 3);
    const details = await Promise.all(attentionCandidates.map((job) => apiGetJson(`/app/jobs/${job.id}`).catch(() => null)));
    return { available: true, jobs: list, details: details.filter(Boolean) };
  } catch (error) {
    return { available: false, jobs: [], details: [] };
  }
}

function summarizeJobsPressure(pressure) {
  if (!pressure?.available) {
    return {
      available: false,
      dueCount: null,
      dueSoonCount: null,
      overdueCount: null,
      blockedCount: null,
      readyCount: null,
      activeValueCents: null,
      attentionJobs: [],
      recentEvents: [],
    };
  }
  const openJobs = pressure.jobs.filter((job) => !CLOSED_JOB_STATUSES.has(job.status));
  const dueMeta = new Map(openJobs.map((job) => [job.id, jobDueMeta(job)]));
  const dueCount = openJobs.filter((job) => {
    const due = dueMeta.get(job.id);
    return due.overdue || due.dueSoon;
  }).length;
  const overdueCount = openJobs.filter((job) => dueMeta.get(job.id)?.overdue).length;
  const dueSoonCount = openJobs.filter((job) => dueMeta.get(job.id)?.dueSoon).length;
  const blockedCount = openJobs.filter((job) => job.status === 'blocked').length;
  const readyCount = openJobs.filter((job) => job.status === 'ready').length;
  const activeValueCents = openJobs.reduce((sum, job) => sum + Number(job.estimated_value_cents || 0), 0);
  const pressureJobs = openJobs.filter((job) => {
    const due = dueMeta.get(job.id);
    return due?.overdue || due?.dueSoon || ['blocked', 'ready', 'active'].includes(job.status);
  });
  const attentionJobs = pressureJobs
    .sort((a, b) => {
      const rank = rankJobPressure(a) - rankJobPressure(b);
      if (rank !== 0) return rank;
      return String(a.due_date || '9999').localeCompare(String(b.due_date || '9999'));
    })
    .slice(0, 3);
  const recentEvents = pressure.details
    .flatMap((job) => (Array.isArray(job.events) ? job.events.map((event) => ({ ...event, job })) : []))
    .sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
    .slice(0, 2);
  return { available: true, dueCount, dueSoonCount, overdueCount, blockedCount, readyCount, activeValueCents, attentionJobs, recentEvents };
}

function renderJobsPressureBoard(pressure) {
  const summary = summarizeJobsPressure(pressure);
  if (!summary.available) {
    return `
      <section class="bus-home-jobs-pressure" data-role="home-jobs-pressure">
        <div class="bus-home-section-head"><h3>Jobs Pressure</h3><a href="#/jobs">View Jobs</a></div>
        <p>Jobs data is unavailable from Home right now.</p>
      </section>`;
  }

  const attention = summary.attentionJobs.length
    ? summary.attentionJobs.map((job) => {
        const due = jobDueMeta(job);
        const tone = due.overdue ? 'overdue' : due.dueSoon ? 'soon' : job.status;
        return `<li data-tone="${escapeHtml(tone)}"><a href="#/jobs">${escapeHtml(job.title || `Job #${job.id}`)}</a><span>${escapeHtml(job.status || 'draft')} · ${escapeHtml(formatDate(job.due_date))}</span></li>`;
      }).join('')
    : '<li><span>No active job pressure.</span></li>';
  const events = summary.recentEvents.length
    ? `<div class="bus-home-jobs-events">${summary.recentEvents.map((event) => `
        <p><strong>${escapeHtml(event.job?.title || 'Job')}</strong><span>${escapeHtml(event.event_type || 'note')} · ${escapeHtml(formatDateTime(event.created_at) || 'recent')}</span></p>`).join('')}</div>`
    : '';

  return `
    <section class="bus-home-jobs-pressure" data-role="home-jobs-pressure">
      <div class="bus-home-section-head"><h3>Jobs Pressure</h3><a href="#/jobs">View Jobs</a></div>
      <div class="bus-home-jobs-metrics">
        ${statusRow('Overdue / due soon', String(summary.dueCount), summary.overdueCount > 0 ? 'danger' : summary.dueSoonCount > 0 ? 'warn' : 'good')}
        ${statusRow('Blocked', String(summary.blockedCount), summary.blockedCount > 0 ? 'danger' : 'good')}
        ${statusRow('Ready', String(summary.readyCount), summary.readyCount > 0 ? 'good' : '')}
        ${statusRow('Active value', escapeHtml(formatMoney(summary.activeValueCents)))}
      </div>
      <ul class="bus-home-jobs-attention">${attention}</ul>
      ${events}
    </section>`;
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
  const [system, exportsRes, auth, update, jobsPressure] = await Promise.all([
    apiGetJson('/app/system/state').catch(() => null),
    apiGetJson('/app/db/exports').catch(() => null),
    getAuthState().catch(() => null),
    runUpdateCheck().catch(() => null),
    fetchJobsPressureData(),
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
    jobsPressure,
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
    <div class="bus-home-next-step">
      <span class="bus-home-next-label">Start your shop setup</span>
    </div>
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

function renderNextStep(message, action, helper = '') {
  return `
    <div class="bus-home-next-step">
      <span class="bus-home-next-label">Next useful step</span>
      <p class="bus-home-next-copy">${message}</p>
      ${helper ? `<p class="bus-home-helper">${helper}</p>` : ''}
      <div class="bus-home-action-row bus-home-action-row--single">${actionLink(action, 'bus-home-btn--primary')}</div>
    </div>`;
}

function renderActiveShop(data) {
  const { backup, update } = data;
  const jobSummary = summarizeJobsPressure(data.jobsPressure);
  const backupWarning = backup.exports && backup.exports.length === 0;
  const attention = [];
  if (update?.update_available && update?.latest_version) attention.push(`Update available: ${escapeHtml(update.latest_version)}`);
  if (backupWarning) attention.push('No local backup export found yet.');
  if (jobSummary.available) {
    if (jobSummary.dueCount > 0) attention.push(`${plural(jobSummary.dueCount, 'job')} overdue or due soon.`);
    if (jobSummary.blockedCount > 0) attention.push(`${plural(jobSummary.blockedCount, 'blocked job')} needs a decision.`);
    if (jobSummary.readyCount > 0) attention.push(`${plural(jobSummary.readyCount, 'ready job')} can move forward.`);
  } else {
    attention.push('Job pressure is unavailable right now.');
  }

  const allClear = !attention.length && jobSummary.available;
  const body = allClear
    ? `<div class="bus-home-all-clear"><strong>All clear</strong><p>No overdue jobs, no blocked jobs, no backup warnings.</p></div>`
    : `<ul class="bus-home-attention-list">${attention.map((item) => `<li>${item}</li>`).join('')}</ul>`;

  return `
    <section class="bus-home-attention-card">
      <h3>What needs attention</h3>
      ${body}
      <div class="bus-home-bench-actions">
        ${actionLink(ACTIONS.buildProduct, 'bus-home-btn--primary')}
        ${actionLink(ACTIONS.addSupply)}
      </div>
    </section>`;
}

function renderBench(data) {
  const state = shopState(data.counts);
  if (state === 'no-supplies') {
    return `<h2>Shop Bench</h2>${renderSetupSteps()}`;
  }
  if (state === 'no-blueprints') {
    return `<h2>Shop Bench</h2>${renderNextStep('Create a blueprint from your supplies.', ACTIONS.createBlueprint)}`;
  }
  if (state === 'no-builds') {
    return `<h2>Shop Bench</h2>${renderNextStep('Build your first product from a blueprint.', ACTIONS.buildProduct, 'This proves your supply to blueprint to product flow and starts real costing.')}`;
  }
  return `<h2>Shop Bench</h2>${renderActiveShop(data)}`;
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
      notices.push({ id: `update:${pair}`, tone: 'warn', text: `Update available: ${update.latest_version}.`, actionHref: '#/settings', actionText: 'Review update settings' });
    }
  }

  if (data.backup.exports && data.backup.exports.length === 0 && !dismissed.includes('backup-export-missing')) {
    notices.push({ id: 'backup-export-missing', tone: 'warn', text: 'No local backup export has been found yet.', actionHref: '#/settings', actionText: 'Open backup settings' });
  }
  if (data.busMode === 'demo' && !dismissed.includes('demo-data-active')) {
    notices.push({ id: 'demo-data-active', tone: 'warn', text: 'Demo data active.' });
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
  const versionLine = currentVersion === 'unknown' ? 'BUS Core' : `BUS Core ${escapeHtml(currentVersion)}`;
  const updateLine = hasUpdate && !hiddenByUpdateDismiss
    ? `<p class="bus-home-update-available">Update available: ${escapeHtml(update.latest_version)}.</p>`
    : '';
  if (currentSeen && (!hasUpdate || hiddenByUpdateDismiss)) {
    return `
      <section class="bus-home-side-card" data-role="home-update-card">
        <h3>Latest Update</h3>
        <p>${versionLine}</p>
        <a href="/brand/CHANGELOG.md" target="_blank" rel="noopener noreferrer">Read full changelog</a>
      </section>`;
  }
  return `
    <section class="bus-home-side-card" data-role="home-update-card">
      <div class="bus-home-side-card-head"><h3>Latest Update</h3><button type="button" data-dismiss-update-card>Dismiss</button></div>
      <p class="bus-home-release-version">${versionLine}</p>
      ${updateLine}
      <p class="bus-home-side-label">What changed:</p>
      <ul class="bus-home-release-list">
        <li>Jobs line entry now uses clearer quantity and unit validation.</li>
        <li>Jobs can create and link contacts without leaving the screen.</li>
        <li>Desktop shell scroll ownership is more stable at Windows zoom levels.</li>
        <li>Home now gives Discord a clearer community call to action.</li>
      </ul>
      <p class="bus-home-side-label">Why it matters:</p>
      <p>Daily work capture is tighter, contact linking is faster, and the operator shell is steadier.</p>
      <div class="bus-home-side-actions">
        <a href="/brand/CHANGELOG.md" target="_blank" rel="noopener noreferrer">Read full changelog</a>
      </div>
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
        <h3>System Trust</h3>
        ${statusRow('Version', escapeHtml(data.currentVersion || 'unknown'))}
        ${statusRow('Storage', 'Local', 'good')}
        ${statusRow('Telemetry', 'Off', 'good')}
        ${statusRow('Backup', escapeHtml(backupStatus), data.backup.latest ? 'good' : 'warn')}
        <a href="#/settings">Data location</a>
      </section>
      ${renderUpdateCard(data)}
      <section class="bus-home-side-card">
        <h3>Support Development</h3>
        <p>BUS Core is free and local-first. If it saves you time or helps your shop, consider supporting the project.</p>
        <a class="bus-home-support-action" href="https://buscore.ca/support" target="_blank" rel="noopener noreferrer">Support BUS Core</a>
      </section>
      <section class="bus-home-side-card">
        <h3>Discord Community</h3>
        <p>Join the BUS Core Discord for beta feedback, questions, and shop-floor discussion.</p>
        <a class="bus-home-support-action bus-home-discord-action" href="${DISCORD_URL}" target="_blank" rel="noopener noreferrer">Join the Discord</a>
      </section>
      <section class="bus-home-side-card">
        <h3>Help & Community</h3>
        <div class="bus-home-link-groups">
          <div>
            <span>Help</span>
            <a href="/license/EULA.md" target="_blank" rel="noopener noreferrer">How BUS Core Works</a>
            <a href="/brand/docs/DATA_LIFECYCLE.md" target="_blank" rel="noopener noreferrer">Data Safety</a>
            <a href="/brand/docs/ui_validation_matrix.md" target="_blank" rel="noopener noreferrer">Known Limits</a>
          </div>
          <div>
            <span>Community</span>
            <a href="/brand/README.md" target="_blank" rel="noopener noreferrer">Docs</a>
            <a href="/brand/wiki/Bug-Reports.md" target="_blank" rel="noopener noreferrer">Bug Report</a>
            <a href="${DISCORD_URL}" target="_blank" rel="noopener noreferrer">Discord</a>
            <a href="/license/LICENSE.md" target="_blank" rel="noopener noreferrer">License</a>
          </div>
        </div>
      </section>
    </aside>`;
}

function renderDashboard(root, data) {
  root.querySelector('[data-role="home-alerts"]').innerHTML = renderNotices(data);
  root.querySelector('[data-role="home-bench"]').innerHTML = renderBench(data);
  root.querySelector('[data-role="home-jobs-pressure-slot"]').innerHTML = renderJobsPressureBoard(data.jobsPressure);
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
        <div class="bus-home-main-column">
          <section class="bus-home-bench" data-role="home-bench">
            <h2>Shop Bench</h2>
            <p class="bus-home-sub">Loading local shop state...</p>
          </section>
          <div data-role="home-jobs-pressure-slot">
            <section class="bus-home-jobs-pressure" data-role="home-jobs-pressure">
              <div class="bus-home-section-head"><h3>Jobs Pressure</h3><a href="#/jobs">View Jobs</a></div>
              <p>Loading job pressure...</p>
            </section>
          </div>
        </div>
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
      jobsPressure: { available: false, jobs: [], details: [] },
    });
  });
}
