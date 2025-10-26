import { getLicense, apiGet, apiPost } from "/ui/js/token.js";
import { mountWrites }    from "/ui/js/cards/writes.js";
import { mountOrganizer } from "/ui/js/cards/organizer.js";
import { mountDev }       from "/ui/js/cards/dev.js";

const mounts = { writes: mountWrites, organizer: mountOrganizer, dev: mountDev };

function setActiveTab(name, buttons){
  buttons.forEach(b => b.classList.toggle("active", b.dataset.tab === name));
}

function mountCard(name, view){
  const fn = mounts[name]; if (!fn) { view.textContent = "Module unavailable."; return; }
  const card = document.createElement("div"); card.className = "card";
  view.replaceChildren(card);
  const r = fn(card); if (r && typeof r.catch === "function") r.catch(e => { card.textContent = String(e); });
}

async function initializeLicense(){
  try {
    const lic = await getLicense();
    const badge = document.getElementById("license");
    if (badge && lic && lic.tier) badge.textContent = `License: ${lic.tier}`;
  } catch {}
}

async function loadWritesState(toggle){
  if (!toggle) return;
  try {
    const state = await apiGet("/dev/writes");
    const enabled = !!(state && state.enabled);
    toggle.checked = enabled;
    document.body.dataset.writesEnabled = enabled ? "true" : "false";
    const label = document.getElementById("writes-toggle-status");
    if (label) label.textContent = enabled ? "Writes Enabled" : "Writes Disabled";
  } catch {}
}

function attachWritesToggle(toggle){
  if (!toggle) return;
  toggle.addEventListener("change", async () => {
    const enabled = toggle.checked; toggle.disabled = true;
    try {
      await apiPost("/dev/writes", { enabled });
      document.dispatchEvent(new CustomEvent("writes:changed", { detail: { enabled } }));
    } finally { toggle.disabled = false; }
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  const view = document.getElementById("view"); if (!view) return;
  await initializeLicense();
  const toggle = document.getElementById("writes-toggle");
  attachWritesToggle(toggle);
  await loadWritesState(toggle);

  const buttons = Array.from(document.querySelectorAll(".sidebar-tab"));
  buttons.forEach(btn => btn.addEventListener("click", () => {
    const tab = btn.dataset.tab; setActiveTab(tab, buttons); mountCard(tab, view);
  }));
  setActiveTab("writes", buttons); mountCard("writes", view);
});
