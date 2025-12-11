import { apiGet } from "./api.js";

let _cursor = null;
let _loading = false;

function rowEl(ev) {
  const dt = new Date(ev.ts);
  const dateStr = dt.toLocaleDateString();
  const timeStr = dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  let summary = "";
  if (ev.domain === "inventory") {
    const sign = (ev.qty_change ?? 0) >= 0 ? "+" : "";
    summary = `${ev.kind} • item #${ev.item_id} • ${sign}${ev.qty_change} ea`;
  } else if (ev.domain === "manufacturing") {
    const name = ev.recipe_name || (ev.recipe_id != null ? `Recipe #${ev.recipe_id}` : "ad-hoc");
    summary = `run • ${name} • x${ev.output_qty}`;
  } else if (ev.domain === "recipes") {
    summary = `${ev.kind} • ${ev.recipe_name || `(id ${ev.recipe_id})`}`;
  } else {
    summary = ev.kind || ev.domain || "event";
  }

  const div = document.createElement("div");
  div.className = "logs-row";
  div.innerHTML = `
    <div class="logs-col when">${dateStr} ${timeStr}</div>
    <div class="logs-col domain">${ev.domain}</div>
    <div class="logs-col summary">${summary}</div>
  `;
  return div;
}

function injectCssOnce() {
  if (document.getElementById("logs-css")) return;
  const style = document.createElement("style");
  style.id = "logs-css";
  style.textContent = `
  .logs-wrap{display:flex;flex-direction:column;gap:8px}
  .logs-head,.logs-row{display:grid;grid-template-columns:180px 140px 1fr;gap:8px;align-items:center}
  .logs-head{font-weight:600;opacity:.85;position:sticky;top:0;backdrop-filter:blur(2px)}
  .logs-scroller{overflow:auto;max-height:70vh;border-radius:8px}
  .logs-empty{opacity:.7;padding:8px}
  .logs-load{padding:8px;text-align:center;opacity:.8;cursor:pointer}
  `;
  document.head.appendChild(style);
}

async function fetchMore() {
  if (_loading) return;
  _loading = true;
  try {
    const url = _cursor ? `/app/logs?limit=200&cursor=${encodeURIComponent(_cursor)}` : "/app/logs?limit=200";
    const { events, next_cursor } = await apiGet(url);
    const body = document.getElementById("logs-body");
    if (!events || !events.length) {
      if (!body.children.length) body.innerHTML = `<div class="logs-empty">No logs.</div>`;
      const more = document.getElementById("logs-more");
      if (more) more.style.display = "none";
      return;
    }
    const frag = document.createDocumentFragment();
    events.forEach(ev => frag.appendChild(rowEl(ev)));
    body.appendChild(frag);
    _cursor = next_cursor || null;
    const more = document.getElementById("logs-more");
    if (more) more.style.display = _cursor ? "" : "none";
  } finally {
    _loading = false;
  }
}

export function mountLogsPage(root) {
  injectCssOnce();
  root.innerHTML = `
    <div class="card">
      <div class="card-title">Logs</div>
      <div class="logs-wrap">
        <div class="logs-head"><div>Date/Time</div><div>Domain</div><div>Summary</div></div>
        <div class="logs-scroller" id="logs-scroll">
          <div id="logs-body"></div>
          <div id="logs-more" class="logs-load">Load older…</div>
        </div>
      </div>
    </div>
  `;
  const more = document.getElementById("logs-more");
  if (more) more.addEventListener("click", fetchMore);
  const sc = document.getElementById("logs-scroll");
  if (sc) {
    sc.addEventListener("scroll", () => {
      if (!_cursor) return;
      if (sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 10) fetchMore();
    });
  }
  _cursor = null;
  const body = document.getElementById("logs-body");
  if (body) body.innerHTML = "";
  fetchMore();
}
