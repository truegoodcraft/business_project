import { apiPost } from "/ui/js/token.js";

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

function ensurePlanId(planInput){
  const value = planInput.value.trim();
  if (!value) {
    alert("Set a plan ID before continuing.");
    return null;
  }
  return value;
}

export function mountOrganizer(container){
  const title = el("h2", {}, "Organizer");
  const description = el("div", { class: "badge-note" }, "Create, preview, and commit organizer plans.");

  const startInput = el("input", { type: "text", placeholder: "Start folder", style: { minWidth: "320px" } });
  const quarantineInput = el("input", { type: "text", placeholder: "Quarantine folder (optional)", style: { minWidth: "320px" } });
  const planInput = el("input", { type: "text", placeholder: "Plan ID", style: { minWidth: "320px" } });

  const duplicatesButton = el("button", { type: "button" }, "Duplicates -> Plan");
  const renameButton = el("button", { type: "button" }, "Normalize -> Plan");
  const previewButton = el("button", { type: "button", class: "secondary" }, "Preview Plan");
  const commitButton = el("button", { type: "button" }, "Commit Plan");
  const status = el("pre", { class: "status-box", style: { minHeight: "180px" } }, "Awaiting action.");

  async function withStatus(task){
    status.textContent = "Working…";
    try {
      const result = await task();
      status.textContent = JSON.stringify(result || {}, null, 2);
      return result;
    } catch (error) {
      status.textContent = `Error: ${error.message}`;
      throw error;
    }
  }

  duplicatesButton.addEventListener("click", async () => {
    const startPath = startInput.value.trim();
    if (!startPath) {
      alert("Provide a start folder.");
      return;
    }
    try {
      const result = await withStatus(() => apiPost("/organizer/duplicates/plan", {
        start_path: startPath,
        quarantine_dir: quarantineInput.value.trim() || null,
      }));
      if (result && result.plan_id) {
        planInput.value = result.plan_id;
      }
    } catch {
      // handled by withStatus
    }
  });

  renameButton.addEventListener("click", async () => {
    const startPath = startInput.value.trim();
    if (!startPath) {
      alert("Provide a start folder.");
      return;
    }
    try {
      const result = await withStatus(() => apiPost("/organizer/rename/plan", {
        start_path: startPath,
      }));
      if (result && result.plan_id) {
        planInput.value = result.plan_id;
      }
    } catch {
      // handled by withStatus
    }
  });

  previewButton.addEventListener("click", async () => {
    const planId = ensurePlanId(planInput);
    if (!planId) return;
    try {
      await withStatus(() => apiPost(`/plans/${encodeURIComponent(planId)}/preview`, {}));
    } catch {
      // handled by withStatus
    }
  });

  commitButton.addEventListener("click", async () => {
    const planId = ensurePlanId(planInput);
    if (!planId) return;
    try {
      await withStatus(() => apiPost(`/plans/${encodeURIComponent(planId)}/commit`, {}));
    } catch {
      // handled by withStatus
    }
  });

  container.replaceChildren(
    title,
    description,
    el("section", {}, [
      el("div", { class: "section-title" }, "Create plan"),
      el("div", { class: "form-grid" }, [
        el("label", {}, ["Start folder", startInput]),
        el("label", {}, ["Quarantine folder", quarantineInput]),
      ]),
      el("div", { class: "actions" }, [duplicatesButton, renameButton]),
    ]),
    el("section", {}, [
      el("div", { class: "section-title" }, "Manage plan"),
      el("div", { class: "form-grid" }, [
        el("label", {}, ["Plan ID", planInput]),
      ]),
      el("div", { class: "actions" }, [previewButton, commitButton]),
    ]),
    status,
  );
}
