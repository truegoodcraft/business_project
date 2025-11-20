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

export function mountHome() {
  const container = document.querySelector('[data-role="home-screen"]');
  if (!container) return;
  container.classList.remove('hidden');
  // stub data
  const netEl = document.querySelector('[data-role="net-30"]');
  if (netEl) netEl.textContent = 'Net (Last 30 Days): $0.00';
  const tbody = document.querySelector('[data-role="recent-transactions"] tbody');
  if (tbody) tbody.innerHTML = '';
  // initial data load will be triggered on DOMContentLoaded below
}

// ===== Expense modal wiring (MVP) =====
const expenseModal = document.querySelector('[data-role="expense-modal"]');
const expenseForm  = expenseModal?.querySelector('[data-role="expense-form"]');

function openExpenseModal() {
  if (!expenseModal) return;
  expenseModal.classList.remove('hidden');
  expenseModal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('no-scroll');
  if (expenseForm) {
    expenseForm.reset();
    const d = new Date();
    if (expenseForm.elements?.date) expenseForm.elements.date.valueAsDate = d;
    if (expenseForm.elements?.amount) expenseForm.elements.amount.focus();
  }
}
function closeExpenseModal() {
  if (!expenseModal) return;
  expenseModal.classList.add('hidden');
  expenseModal.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('no-scroll');
}

document.addEventListener('click', (e) => {
  const t = e.target;
  if (t?.matches?.('[data-action="open-expense-modal"]')) openExpenseModal();
  if (t?.matches?.('[data-action="close-expense-modal"]')) closeExpenseModal();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && expenseModal && !expenseModal.classList.contains('hidden')) closeExpenseModal();
});

expenseForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(expenseForm);
  const amt = Number(fd.get('amount'));
  if (!Number.isFinite(amt) || amt <= 0) { alert('Enter a valid amount'); return; }
  const amount_cents = -Math.round(Math.abs(amt) * 100); // expenses negative

  const payload = {
    type: 'expense',
    amount_cents,
    category: (fd.get('category') || '').trim() || null,
    date: fd.get('date') || new Date().toISOString().slice(0,10),
    notes: (fd.get('notes') || '').trim() || null
  };

  try {
    // Prefer global apiPost; otherwise use a local POST shim.
    const poster = (typeof window.apiPost === 'function')
      ? window.apiPost
      : async (path, body) => {
          const tok = await _getSessionToken();
          const res = await fetch(path, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(tok ? { 'X-Session-Token': tok } : {})
            },
            body: JSON.stringify(body)
          });
          if (!res.ok) {
            const txt = await res.text().catch(() => res.statusText);
            throw new Error(`POST ${path} -> ${res.status} ${txt}`);
          }
          return res.json();
        };
    const res = await poster('/app/transactions', payload);
    closeExpenseModal();
    if (typeof showToast === 'function') showToast('Saved.');
    else alert('Saved.');
    if (typeof refreshHomeData === 'function') refreshHomeData();
  } catch (err) {
    console.error(err);
    alert('Save failed');
  }
});

// ---- SMOKE probe (no deps) ----
window.SMOKE = window.SMOKE || {};
window.SMOKE.homeExpense = () => ({
  modalExists: !!document.querySelector('[data-role="expense-modal"]'),
  formExists:  !!document.querySelector('[data-role="expense-form"]'),
  canOpen:     (() => { openExpenseModal(); const open = expenseModal && !expenseModal.classList.contains('hidden'); closeExpenseModal(); return !!open; })(),
});

// ===== Home data refresh (summary + recent) =====
let activeFilter = null; // 'expense' | 'revenue' | null

// Reuse apiGet if present; otherwise fallback to existing httpGetJson()
async function _getJson(path){
  if (typeof window.apiGet === 'function') return await window.apiGet(path);
  if (typeof window.httpGetJson === 'function') return await window.httpGetJson(path);
  // Last resort: tiny inline GET
  const tok = (await (window._getSessionToken?.() ?? null)) || null;
  const res = await fetch(path, { headers: tok ? { 'X-Session-Token': tok } : {} });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status} ${res.statusText}`);
  return res.json();
}

function formatUSD(cents){
  const abs = Math.abs(cents) / 100;
  const str = abs.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return cents < 0 ? `-$${str}` : `$${str}`;
}

function renderRecentTable(items, filter) {
  const tbody = document.querySelector('[data-role="recent-transactions"] tbody');
  if (!tbody) return;
  const arr = (items || []);
  const filtered = filter ? arr.filter(it => it.type === filter) : arr;
  const html = filtered.map(it => {
    const amt = formatUSD(it.amount_cents);
    const note = (it.notes || '').replace(/\s+/g,' ').trim();
    return `<tr data-type="${it.type}"><td>${it.date}</td><td>${it.type}</td><td>${amt}</td><td>${note}</td></tr>`;
  }).join('');
  tbody.innerHTML = html || '';
}
async function refreshHomeData() {
  try {
    // Compute since (30 days back, inclusive)
    const since = new Date();
    since.setDate(since.getDate() - 30);
    const sinceStr = since.toISOString().slice(0,10);

    const [summary, recentResp] = await Promise.all([
      _getJson('/app/transactions/summary?window=30d'),
      _getJson(`/app/transactions?since=${sinceStr}&limit=10`)
    ]);

    // Net line
    const netEl = document.querySelector('[data-role="net-30"]');
    if (netEl) netEl.textContent = `Net (Last 30 Days): ${formatUSD(summary.net_cents)}`;

    // Donuts remain blank circles; attach amounts as titles (hover) and aria-labels
    const dIn  = document.querySelector('[data-role="donut-in"].donut');
    const dOut = document.querySelector('[data-role="donut-out"].donut');
    if (dIn)  { dIn.title  = `In: ${formatUSD(summary.in_cents)}`;  dIn.setAttribute('aria-label', dIn.title); }
    if (dOut) { dOut.title = `Out: ${formatUSD(summary.out_cents)}`; dOut.setAttribute('aria-label', dOut.title); }

    // Recent table
    const items = (recentResp && recentResp.items) ? recentResp.items : [];
    renderRecentTable(items, activeFilter);

    // Title
    const titleEl = document.querySelector('.table-title');
    if (titleEl) {
      if (activeFilter === 'expense') titleEl.textContent = 'Expenses Only (Last 10)';
      else if (activeFilter === 'revenue') titleEl.textContent = 'Revenue Only (Last 10)';
      else titleEl.textContent = 'Last transactions (10)';
    }
  } catch (err) {
    console.error('refreshHomeData failed', err);
  }
}
// Expose for other code (e.g., after save)
window.refreshHomeData = refreshHomeData;

// Delegate donut clicks (bind once)
if (!window._homeDonutBound) {
  document.addEventListener('click', (e) => {
    const donut = e.target?.closest?.('.donut');
    if (!donut) return;
    const isIn = donut.classList.contains('donut-in');
    const type = isIn ? 'revenue' : 'expense';
    activeFilter = (activeFilter === type) ? null : type;
    // toggle active class for visual state (CSS may style .active later)
    document.querySelectorAll('.donut').forEach(d => d.classList.remove('active'));
    if (activeFilter && donut) donut.classList.add('active');
    refreshHomeData();
  });
  window._homeDonutBound = true;
}

// Initial load (once DOM is ready)
if (!window._homeInitBound) {
  document.addEventListener('DOMContentLoaded', () => {
    try { refreshHomeData(); } catch (_) {}
  });
  window._homeInitBound = true;
}
