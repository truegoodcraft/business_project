export function mountHome() {
  const container = document.querySelector('[data-role="home-screen"]');
  if (!container) return;
  container.classList.remove('hidden');
  // stub data
  document.querySelector('[data-role="net-30"]').textContent = 'Net (Last 30 Days): $0.00';
  document.querySelector('[data-role="recent-transactions"] tbody').innerHTML = '';
  // initial data load
  if (typeof refreshHomeData === 'function') { refreshHomeData(); } else { try { refreshHomeData(); } catch(_) {} }
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
// Lightweight local GET with session token; falls back to direct fetch of /session/token.
async function _getSessionToken() {
  if (window._BUS_TOKEN) return window._BUS_TOKEN;
  try {
    const t = await fetch('/session/token').then(r => r.json());
    window._BUS_TOKEN = t.token;
    return window._BUS_TOKEN;
  } catch {
    return null;
  }
}
async function httpGetJson(path) {
  try {
    // Prefer app's apiGet if present
    if (typeof window.apiGet === 'function') return await window.apiGet(path);
    const tok = await _getSessionToken();
    const res = await fetch(path, { headers: tok ? { 'X-Session-Token': tok } : {} });
    if (!res.ok) throw new Error(res.status + ' ' + res.statusText);
    return await res.json();
  } catch (e) {
    console.error('GET', path, e);
    throw e;
  }
}
function formatUSDFromCents(cents) {
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  const dollars = Math.floor(abs / 100);
  const pennies = (abs % 100).toString().padStart(2, '0');
  return `${sign}$${dollars}.${pennies}`;
}
function renderRecentTable(items, filter) {
  const tbody = document.querySelector('[data-role="recent-transactions"] tbody');
  if (!tbody) return;
  const rows = (items || [])
    .filter(it => !filter || it.type === filter)
    .map(it => {
      const amt = formatUSDFromCents(it.amount_cents);
      const note = (it.notes || '').replace(/\s+/g,' ').trim();
      return `<tr data-type="${it.type}"><td>${it.date}</td><td>${it.type}</td><td>${amt}</td><td>${note}</td></tr>`;
    })
    .join('');
  tbody.innerHTML = rows || '';
}
let _homeFilter = null; // 'revenue' | 'expense' | null
async function refreshHomeData() {
  // Summary (30d)
  try {
    const sum = await httpGetJson('/app/transactions/summary?window=30d');
    const netEl = document.querySelector('[data-role="net-30"]');
    if (netEl) netEl.textContent = `Net (Last 30 Days): ${formatUSDFromCents(sum.net_cents)}`;
    // Donut placeholders: just write totals as text for now
    const dIn = document.querySelector('[data-role="donut-in"]');
    const dOut = document.querySelector('[data-role="donut-out"]');
    if (dIn) dIn.textContent = `In: ${formatUSDFromCents(sum.in_cents)}`;
    if (dOut) dOut.textContent = `Out: ${formatUSDFromCents(sum.out_cents)}`;
  } catch (e) {
    console.error('summary refresh failed', e);
  }
  // Recent items (limit 10; since optional)
  try {
    const today = new Date();
    const cutoff = new Date(today.getTime() - 29*24*60*60*1000).toISOString().slice(0,10); // ~30d window inclusive
    const recent = await httpGetJson(`/app/transactions?since=${cutoff}&limit=10`);
    renderRecentTable(recent.items || [], _homeFilter);
  } catch (e) {
    console.error('recent refresh failed', e);
  }
}
// Expose for other code (e.g., after save)
window.refreshHomeData = refreshHomeData;

// Donut click filter wiring
document.addEventListener('click', (e) => {
  const t = e.target;
  if (t?.matches?.('[data-role="donut-in"]')) {
    _homeFilter = _homeFilter === 'revenue' ? null : 'revenue';
    refreshHomeData();
  }
  if (t?.matches?.('[data-role="donut-out"]')) {
    _homeFilter = _homeFilter === 'expense' ? null : 'expense';
    refreshHomeData();
  }
});
