import { apiGet, apiPost } from "/ui/js/token.js";

function el(tag, attributes = {}, children = []){
  const node = document.createElement(tag);
  Object.entries(attributes).forEach(([key, value]) => {
    if (value === null || value === undefined) {
      return;
    }
    if (key === "class") {
      node.className = value;
      return;
    }
    if (key === "for") {
      node.htmlFor = value;
      return;
    }
    if (key === "style" && typeof value === "object") {
      Object.assign(node.style, value);
      return;
    }
    node.setAttribute(key, value);
  });
  const content = Array.isArray(children) ? children : [children];
  content.forEach(child => {
    if (child === null || child === undefined) {
      return;
    }
    if (typeof child === "string") {
      node.appendChild(document.createTextNode(child));
    } else {
      node.appendChild(child);
    }
  });
  return node;
}

function updateHeader(enabled){
  const headerToggle = document.getElementById("writes-toggle");
  if (headerToggle && headerToggle.checked !== enabled) {
    headerToggle.checked = enabled;
  }
  const label = document.getElementById("writes-toggle-status");
  if (label) {
    label.textContent = enabled ? "Writes Enabled" : "Writes Disabled";
  }
  document.body.dataset.writesEnabled = enabled ? "true" : "false";
}

export function mountWrites(container){
  const title = el("h2", {}, "Writes Control");
  const description = el("div", { class: "badge-note" }, "Toggle local API writes for diagnostics and development.");
  const toggle = el("input", { type: "checkbox", id: "writes-card-toggle" });
  const toggleLabel = el("label", { class: "writes-card-toggle", for: "writes-card-toggle" }, [
    toggle,
    el("span", { class: "toggle-label" }, "Enable writes via API"),
  ]);
  const refreshButton = el("button", { type: "button", class: "secondary" }, "Refresh State");
  const status = el("pre", { class: "status-box", style: { minHeight: "160px" } }, "Loading…");

  async function refresh(){
    status.textContent = "Loading…";
    try {
      const data = await apiGet("/dev/writes");
      const enabled = data && typeof data.enabled === "boolean" ? data.enabled : false;
      toggle.checked = enabled;
      updateHeader(enabled);
      status.textContent = JSON.stringify(data || {}, null, 2);
    } catch (error) {
      status.textContent = `Error: ${error.message}`;
    }
  }

  async function update(enabled){
    status.textContent = "Updating…";
    try {
      const data = await apiPost("/dev/writes", { enabled });
      updateHeader(enabled);
      document.dispatchEvent(new CustomEvent("writes:changed", { detail: { enabled } }));
      status.textContent = JSON.stringify(data || {}, null, 2);
    } catch (error) {
      status.textContent = `Error: ${error.message}`;
      toggle.checked = !enabled;
    } finally {
      await refresh();
    }
  }

  refreshButton.addEventListener("click", () => {
    refresh().catch(error => {
      status.textContent = `Error: ${error.message}`;
    });
  });

  toggle.addEventListener("change", event => {
    if (!event.isTrusted) {
      return;
    }
    update(toggle.checked).catch(error => {
      status.textContent = `Error: ${error.message}`;
    });
  });

  const handleExternal = event => {
    if (!container.isConnected) {
      document.removeEventListener("writes:changed", handleExternal);
      return;
    }
    if (event && event.detail && typeof event.detail.enabled === "boolean") {
      const { enabled } = event.detail;
      if (toggle.checked !== enabled) {
        toggle.checked = enabled;
      }
      updateHeader(enabled);
    }
  };

  document.addEventListener("writes:changed", handleExternal);

  container.replaceChildren(
    title,
    description,
    el("section", {}, [
      el("div", { class: "section-title" }, "Control"),
      toggleLabel,
      el("div", { class: "actions" }, [refreshButton]),
    ]),
    el("section", {}, [
      el("div", { class: "section-title" }, "State"),
      status,
    ]),
  );

  refresh().catch(error => {
    status.textContent = `Error: ${error.message}`;
  });
}
