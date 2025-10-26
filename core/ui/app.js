import { getLicense, apiGet, apiPost } from "/ui/js/token.js";
import { mountWrites } from "/ui/js/cards/writes.js";
import { mountOrganizer } from "/ui/js/cards/organizer.js";
import { mountDev } from "/ui/js/cards/dev.js";

const mounts = {
  writes: mountWrites,
  organizer: mountOrganizer,
  dev: mountDev,
};

function setActiveTab(active, buttons) {
  buttons.forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === active);
  });
}

async function loadLicenseBadge() {
  try {
    const license = await getLicense();
    const badge = document.getElementById("license");
    if (badge && license && typeof license.tier === "string") {
      badge.textContent = `License: ${license.tier}`;
    }
  } catch (error) {
    console.error("Failed to load license", error);
  }
}

async function refreshWritesToggle(toggle) {
  if (!toggle) return;
  try {
    const data = await apiGet("/dev/writes");
    const enabled = data && typeof data.enabled === "boolean" ? data.enabled : false;
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

function wireWritesToggle(toggle) {
  if (!toggle) return;
  toggle.addEventListener("change", async (event) => {
    if (!event.isTrusted) {
      return;
    }
    const enabled = Boolean(toggle.checked);
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
    const { enabled } = event.detail;
    if (toggle.checked !== enabled) {
      toggle.checked = enabled;
      const label = document.getElementById("writes-toggle-status");
      if (label) {
        label.textContent = enabled ? "Writes Enabled" : "Writes Disabled";
      }
      document.body.dataset.writesEnabled = enabled ? "true" : "false";
    }
  });
}

function mountView(tab, view) {
  const mount = mounts[tab];
  if (!mount) {
    view.textContent = "Module unavailable.";
    return;
  }
  const result = mount(view);
  if (result && typeof result.then === "function") {
    result.catch((error) => {
      console.error("Card mount failed", error);
      view.textContent = `Error: ${error.message}`;
    });
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const view = document.getElementById("view");
  if (!view) {
    return;
  }

  await loadLicenseBadge();

  const toggle = document.getElementById("writes-toggle");
  wireWritesToggle(toggle);
  await refreshWritesToggle(toggle);

  const buttons = Array.from(document.querySelectorAll(".sidebar-tab"));
  const showTab = (name) => {
    setActiveTab(name, buttons);
    mountView(name, view);
  };

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const tab = button.dataset.tab;
      if (!tab) return;
      showTab(tab);
    });
  });

  showTab("writes");
});
