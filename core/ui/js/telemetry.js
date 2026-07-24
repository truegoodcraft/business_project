import { apiGet, apiPost } from './api.js';

async function saveChoice(enabled) {
  await apiPost('/app/telemetry/preference', { enabled: !!enabled });
}

export async function showTelemetryDisclosureIfNeeded() {
  let config;
  try {
    config = await apiGet('/app/config');
  } catch {
    return;
  }
  const telemetry = config?.telemetry || {};
  if (telemetry.disclosure_acknowledged === true) return;

  const dialog = document.createElement('dialog');
  dialog.setAttribute('aria-labelledby', 'telemetry-disclosure-title');
  dialog.style.maxWidth = '620px';
  dialog.style.padding = '1.5rem';
  dialog.innerHTML = `
    <h2 id="telemetry-disclosure-title">Help improve BUS Core</h2>
    <p>BUS Core can send limited technical and product-usage events: app version, release channel, operating-system category, one-time successful feature-use milestones, update results, and reliability events.</p>
    <p>It does not send customers, suppliers, employees, item or recipe names, invoice contents, email addresses, documents, file paths, financial values, quantities, database records, usernames, or machine fingerprints.</p>
    <p>Telemetry is optional, never blocks local work, and can be changed later in Settings. <a href="https://buscore.ca/telemetry" target="_blank" rel="noopener noreferrer">Read the exact privacy explanation</a>.</p>
    <div style="display:flex;gap:.75rem;justify-content:flex-end;flex-wrap:wrap">
      <button type="button" class="btn btn-secondary" data-choice="off">Don't share</button>
      <button type="button" class="btn btn-primary" data-choice="on">Share limited telemetry</button>
    </div>`;
  document.body.appendChild(dialog);

  await new Promise((resolve) => {
    dialog.querySelector('[data-choice="off"]')?.addEventListener('click', async () => {
      try { await saveChoice(false); } catch {}
      dialog.close();
      resolve();
    });
    dialog.querySelector('[data-choice="on"]')?.addEventListener('click', async () => {
      try { await saveChoice(true); } catch {}
      dialog.close();
      resolve();
    });
    dialog.addEventListener('close', () => {
      dialog.remove();
      resolve();
    }, { once: true });
    if (typeof dialog.showModal === 'function') {
      dialog.showModal();
    } else {
      saveChoice(window.confirm('Share limited, disclosed BUS Core telemetry? You can change this later in Settings.'))
        .catch(() => {})
        .finally(resolve);
    }
  });
  dialog.remove();
}
