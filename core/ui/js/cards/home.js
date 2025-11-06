export function mountHome() {
  const container = document.querySelector('[data-role="home-screen"]');
  if (!container) return;
  container.classList.remove('hidden');
  // stub data
  document.querySelector('[data-role="net-30"]').textContent = 'Net (Last 30 Days): $0.00';
  document.querySelector('[data-role="recent-transactions"] tbody').innerHTML = '';
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
    const res = await apiPost('/app/transactions', payload);
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
