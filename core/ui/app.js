import { getLicense, apiGet, apiPost } from "/ui/js/token.js";
import { mountWrites } from "/ui/js/cards/writes.js";
import { mountOrganizer } from "/ui/js/cards/organizer.js";
import { mountDev } from "/ui/js/cards/dev.js";

const mounts = {
  writes: mountWrites,
  organizer: mountOrganizer,
  dev: mountDev,
};

function setActiveTab(name, buttons) {
  buttons.forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === name);
  });
}

async function initializeLicense() {
  try {
    const lic = await getLicense();
    const badge = document.getElementById("license");
    if (badge) {
      const tier = lic && typeof lic.tier === "string" ? lic.tier : "Unknown";
      badge.textContent = `License: ${tier}`;
    }
  } catch (error) {
    console.error("Failed to load license", error);
  }
}

async function loadWritesState(toggle) {
  if (!toggle) return;
  try {
    const state = await apiGet("/dev/writes");
    const enabled = state && typeof state.enabled === "boolean" ? state.enabled : false;
    toggle.checked = enabled;
    document.body.dataset.writesEnabled = enabled ? "true" : "false";
    const label = document.getElementById("writes-toggle-status");
    if (label) {
      label.textContent = enabled ? "Writes Enabled" : "Writes Disabled";
    }
  } catch (error) {
    console.error("Failed to load writes state", error);
  }
}

function attachWritesToggle(toggle) {
  if (!toggle) return;
  toggle.addEventListener("change", async (event) => {
    if (!event.isTrusted) {
      return;
    }
    const enabled = toggle.checked;
    toggle.disabled = true;
    try {
      await apiPost("/dev/writes", { enabled });
      document.body.dataset.writesEnabled = enabled ? "true" : "false";
      const label = document.getElementById("writes-toggle-status");
      if (label) {
        label.textContent = enabled ? "Writes Enabled" : "Writes Disabled";
      }
      document.dispatchEvent(new CustomEvent("writes:changed", { detail: { enabled } }));
    } catch (error) {
      console.error("Failed to update writes", error);
      toggle.checked = !enabled;
    } finally {
      toggle.disabled = false;
    }
  });

  document.addEventListener("writes:changed", (event) => {
    if (!event || !event.detail || typeof event.detail.enabled !== "boolean") {
      return;
    }
    if (!document.contains(toggle)) {
      return;
    }
    if (toggle.checked !== event.detail.enabled) {
      toggle.checked = event.detail.enabled;
      const label = document.getElementById("writes-toggle-status");
      if (label) {
        label.textContent = event.detail.enabled ? "Writes Enabled" : "Writes Disabled";
      }
      document.body.dataset.writesEnabled = event.detail.enabled ? "true" : "false";
    }
  });
}

function mountCard(name, view) {
  const mount = mounts[name];
  if (!mount) {
    view.textContent = "Module unavailable.";
    return;
  }
  const card = document.createElement("div");
  card.className = "card";
  view.replaceChildren(card);
  try {
    const result = mount(card);
    if (result && typeof result.then === "function") {
      result.catch((error) => {
        console.error("Card mount failed", error);
        card.textContent = `Error: ${error.message}`;
      });
    }
  } catch (error) {
    console.error("Card mount failed", error);
    card.textContent = `Error: ${error.message}`;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const view = document.getElementById("view");
  if (!view) {
    return;
  }

  await initializeLicense();

  const toggle = document.getElementById("writes-toggle");
  attachWritesToggle(toggle);
  await loadWritesState(toggle);

  const buttons = Array.from(document.querySelectorAll(".sidebar-tab"));
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const tab = button.dataset.tab;
      if (!tab) return;
      setActiveTab(tab, buttons);
      mountCard(tab, view);
    });
  });

  setActiveTab("writes", buttons);
  mountCard("writes", view);
});
