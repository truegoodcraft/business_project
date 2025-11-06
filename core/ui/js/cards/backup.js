import { ensureToken } from '../api.js';

export function mountBackup(container) {
  if (container) {
    container.innerHTML = `
      <div class="card">
        <button type="button" data-action="export-backup">Export</button>
        <small class="muted">Downloads current app.db (or fallback endpoint).</small>
      </div>
    `;
  }
  mountBackupExport();
}

export function mountBackupExport() {
  const btn = document.querySelector('[data-action="export-backup"]');
  if (!btn || btn.dataset.backupBound) return;
  btn.dataset.backupBound = '1';

  btn.addEventListener('click', async () => {
    try {
      const token = await ensureToken();
      const tryDownload = async (url, filename) => {
        const res = await fetch(url, {
          headers: { 'X-Session-Token': token },
        });
        if (!res.ok) return false;
        const blob = await res.blob();
        const link = document.createElement('a');
        const href = URL.createObjectURL(blob);
        link.href = href;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(href);
        return true;
      };

      if (await tryDownload('/app/backup', 'app-backup.db')) return;
      if (await tryDownload('/app.db', 'app.db')) return;
      alert('No backup endpoint found.');
    } catch (err) {
      console.error('backup export failed', err);
      alert('Could not export backup.');
    }
  });
}

export default mountBackup;
