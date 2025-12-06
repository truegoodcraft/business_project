// SPDX-License-Identifier: AGPL-3.0-or-later
// TGC BUS Core (Business Utility System Core)
// Copyright (C) 2025 True Good Craft
//
// This file is part of TGC BUS Core.
//
// TGC BUS Core is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// TGC BUS Core is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

import { apiGet, apiPost, ensureToken } from '../api.js';
import { request as authedRequest } from '../token.js';

function fmtTs(ts) {
  try {
    return new Date(ts * 1000).toLocaleString();
  } catch {
    return `${ts}`;
  }
}

export function mountAdmin(container) {
  if (!container) return;

  container.innerHTML = `
    <div class="card">
      <h2 style="margin-top:0;margin-bottom:8px;">Backup Export</h2>
      <p class="muted" style="margin-top:0;">Password-based AES-GCM export to %LOCALAPPDATA%\\BUSCore\\exports.</p>
      <form data-form="export">
        <label class="section-title">Password</label>
        <input type="password" required data-field="export-password" placeholder="Enter export password" />
        <div class="row-compact" style="gap:10px;margin-top:10px;align-items:center;">
          <button type="submit">Export</button>
          <span data-status="export" class="muted"></span>
        </div>
      </form>
    </div>

    <div class="card" style="margin-top:16px;">
      <h2 style="margin-top:0;margin-bottom:8px;">Restore (Preview then Commit)</h2>
      <p class="muted" style="margin-top:0;">Preview validates schema before replacing the DB. Commit will archive existing journals and recreate empty ones.</p>
      <div class="row-compact" style="gap:10px;align-items:flex-end;flex-wrap:wrap;">
        <div style="flex:1;min-width:240px;display:flex;flex-direction:column;gap:6px;">
          <label class="section-title" style="margin:0;">Backup file</label>
          <input type="file" data-field="import-file" accept=".gcm,.db" />
          <input type="text" data-field="import-path" placeholder="Or paste a path under exports" />
        </div>
        <div style="flex:1;min-width:200px;display:flex;flex-direction:column;gap:6px;">
          <label class="section-title" style="margin:0;">Password</label>
          <input type="password" data-field="import-password" placeholder="Required to decrypt backup" />
        </div>
      </div>
      <div style="margin-top:12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
        <button type="button" data-action="preview">Preview</button>
        <button type="button" data-action="commit" class="danger">Commit (archives journals)</button>
        <span data-status="restore" class="muted"></span>
      </div>
      <div data-role="preview-box" class="status-box hidden" style="margin-top:12px;"></div>
      <div style="margin-top:12px;">
        <div class="section-title" style="margin-top:0;">Available exports</div>
        <div data-role="exports-list" class="status-box" style="display:flex;gap:8px;flex-wrap:wrap;"></div>
      </div>
    </div>
  `;

  const exportForm = container.querySelector('[data-form="export"]');
  const exportPw = container.querySelector('[data-field="export-password"]');
  const exportStatus = container.querySelector('[data-status="export"]');

  const fileInput = container.querySelector('[data-field="import-file"]');
  const pathInput = container.querySelector('[data-field="import-path"]');
  const importPw = container.querySelector('[data-field="import-password"]');
  const previewBtn = container.querySelector('[data-action="preview"]');
  const commitBtn = container.querySelector('[data-action="commit"]');
  const restoreStatus = container.querySelector('[data-status="restore"]');
  const previewBox = container.querySelector('[data-role="preview-box"]');
  const exportsList = container.querySelector('[data-role="exports-list"]');

  let lastPreviewPath = '';

  exportForm?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    exportStatus.textContent = 'Exporting...';
    try {
      await ensureToken();
      const res = await apiPost('/app/db/export', { password: exportPw.value || '' });
      if (res?.ok) {
        exportStatus.textContent = `Saved to ${res.path}`;
        pathInput.value = res.path;
        refreshExports();
      } else {
        exportStatus.textContent = 'Export failed';
      }
    } catch (err) {
      console.error('export failed', err);
      exportStatus.textContent = err?.error || 'Export failed';
    }
  });

  async function stageUploadIfNeeded() {
    const file = fileInput?.files?.[0];
    if (!file) return pathInput.value.trim();

    await ensureToken();
    const form = new FormData();
    form.append('file', file);
    const resp = await authedRequest('/app/db/import/upload', { method: 'POST', body: form });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(text || 'Upload failed');
    }
    const payload = await resp.json();
    pathInput.value = payload.path;
    return payload.path;
  }

  async function previewRestore() {
    restoreStatus.textContent = 'Previewing...';
    previewBox.classList.add('hidden');
    try {
      const path = await stageUploadIfNeeded();
      if (!path) {
        restoreStatus.textContent = 'Select or paste a backup path';
        return;
      }
      await ensureToken();
      const res = await apiPost('/app/db/import/preview', { path, password: importPw.value || '' });
      if (!res?.ok) throw new Error(res?.error || 'Preview failed');
      lastPreviewPath = path;
      restoreStatus.textContent = 'Preview ok';
      const counts = res.table_counts || {};
      previewBox.innerHTML = `
        <div><strong>Path:</strong> ${path}</div>
        <div><strong>Schema version:</strong> ${res.schema_version ?? 'unknown'}</div>
        <div style="margin-top:8px;">Table counts:</div>
        <ul style="padding-left:18px;margin:4px 0;">
          ${Object.entries(counts).map(([k, v]) => `<li>${k}: ${v}</li>`).join('')}
        </ul>
      `;
      previewBox.classList.remove('hidden');
    } catch (err) {
      console.error('preview failed', err);
      restoreStatus.textContent = err?.error || err?.message || 'Preview failed';
    }
  }

  async function commitRestore() {
    if (!lastPreviewPath) {
      restoreStatus.textContent = 'Preview first to confirm backup';
      return;
    }
    restoreStatus.textContent = 'Committing (journals will be archived)...';
    try {
      await ensureToken();
      const res = await apiPost('/app/db/import/commit', { path: lastPreviewPath, password: importPw.value || '' });
      if (!res?.ok) throw new Error(res?.error || 'Commit failed');
      restoreStatus.textContent = res.restart_required ? 'Restore applied — restart required.' : 'Restore applied.';
      refreshExports();
    } catch (err) {
      console.error('commit failed', err);
      restoreStatus.textContent = err?.error || err?.message || 'Commit failed';
    }
  }

  previewBtn?.addEventListener('click', (ev) => {
    ev.preventDefault();
    previewRestore();
  });

  commitBtn?.addEventListener('click', (ev) => {
    ev.preventDefault();
    commitRestore();
  });

  async function refreshExports() {
    try {
      await ensureToken();
      const res = await apiGet('/app/db/exports');
      exportsList.innerHTML = '';
      (res.exports || []).forEach((item) => {
        const pill = document.createElement('button');
        pill.type = 'button';
        pill.textContent = `${item.name} (${Math.round((item.bytes || 0) / 1024)} KB)`;
        pill.style.background = '#2b2f36';
        pill.style.border = '1px solid var(--border)';
        pill.style.color = 'var(--text)';
        pill.style.cursor = 'pointer';
        pill.style.padding = '6px 10px';
        pill.style.borderRadius = '10px';
        pill.title = `Updated ${fmtTs(item.modified || 0)}`;
        pill.addEventListener('click', () => {
          pathInput.value = item.path;
          lastPreviewPath = item.path;
        });
        exportsList.appendChild(pill);
      });
      if (!res.exports?.length) {
        const empty = document.createElement('div');
        empty.textContent = 'No exports found.';
        empty.className = 'muted';
        exportsList.appendChild(empty);
      }
    } catch (err) {
      console.warn('Failed to load exports', err);
    }
  }

  refreshExports();
}

export default mountAdmin;
