import { apiGet } from "/ui/js/token.js";

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

export function mountDev(container){
  const title = el("h2", {}, "Developer Tools");
  const description = el("div", { class: "badge-note" }, "Ping local plugin endpoints for debugging.");
  const pingButton = el("button", { type: "button" }, "Ping Plugin");
  const output = el("pre", { class: "status-box", style: { minHeight: "140px" } }, "Awaiting action.");

  pingButton.addEventListener("click", async () => {
    output.textContent = "Pinging…";
    try {
      const data = await apiGet("/dev/ping_plugin");
      output.textContent = JSON.stringify(data || {}, null, 2);
    } catch (error) {
      output.textContent = `Error: ${error.message}`;
    }
  });

  container.replaceChildren(
    title,
    description,
    el("section", {}, [
      el("div", { class: "section-title" }, "Diagnostics"),
      el("div", { class: "actions" }, [pingButton]),
      output,
    ]),
  );
}
