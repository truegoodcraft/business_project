(function () {
  const TOKEN_STORAGE_KEY = "tgc_token";
  const panels = {};
  let currentToken = "";
  let googleRowInitialized = false;
  let settingsInitialized = false;
  let refreshOutputsPanel = null;

  const tokenInput = document.getElementById("token-input");
  const saveTokenBtn = document.getElementById("save-token");
  const refreshAllBtn = document.getElementById("refresh-all");
  const tokenBanner = document.getElementById("token-banner");
  const logsAutoscroll = document.getElementById("logs-autoscroll");
  const probeServices = document.getElementById("probe-services");
  const runProbeBtn = document.getElementById("run-probe");
  const tabDashboardBtn = document.getElementById("tab-btn-dashboard");
  const tabSettingsBtn = document.getElementById("tab-btn-settings");
  const tabDashboard = document.getElementById("tab-dashboard");
  const tabSettings = document.getElementById("tab-settings");

  document.querySelectorAll(".panel[data-panel]").forEach((section) => {
    const panelName = section.dataset.panel;
    if (!panelName) {
      return;
    }
    panels[panelName] = {
      section,
      content: section.querySelector('[data-role="content"]'),
      error: section.querySelector('[data-role="error"]'),
      timing: section.querySelector('[data-role="timing"]'),
      timestamp: section.querySelector('[data-role="timestamp"]'),
      refreshBtn: section.querySelector('button[data-action="refresh"]'),
    };
  });

  function loadToken() {
    const stored = window.localStorage.getItem(TOKEN_STORAGE_KEY) || "";
    currentToken = stored;
    if (tokenInput) {
      tokenInput.value = stored;
    }
    updateTokenBanner(!currentToken);
  }

  function saveToken() {
    const nextToken = (tokenInput ? tokenInput.value.trim() : "");
    window.localStorage.setItem(TOKEN_STORAGE_KEY, nextToken);
    currentToken = nextToken;
    updateTokenBanner(!currentToken);
    if (currentToken) {
      refreshAll();
      initGoogleRow();
    } else {
      renderGoogleHealthState("Missing token", false);
      renderGsStatus("Not configured");
      const clientIdInput = document.getElementById("gs-client-id");
      const clientSecretInput = document.getElementById("gs-client-secret");
      if (clientIdInput) {
        clientIdInput.placeholder = "";
        clientIdInput.value = "";
      }
      if (clientSecretInput) {
        clientSecretInput.placeholder = "";
        clientSecretInput.value = "";
      }
    }
  }

  function hasToken() {
    return Boolean(currentToken);
  }

  function getSessionToken() {
    if (!currentToken) {
      throw new Error("Session token required");
    }
    return currentToken;
  }

  function tokenHeader() {
    if (!currentToken) {
      throw new Error("Session token required");
    }
    return { "X-Session-Token": currentToken };
  }

  function renderGsStatus(state) {
    const el = document.getElementById("gs-status");
    if (!el) {
      return;
    }
    const variant = state === "Connected" ? "ok" : state === "Ready" ? "warn" : state === "Error" ? "bad" : "bad";
    el.textContent = state;
    el.className = variant ? `status-pill ${variant}` : "status-pill";
  }

  function renderGoogleHealthState(state, connected) {
    const statusEl = document.getElementById("google-status");
    const disconnectBtn = document.getElementById("google-disconnect");
    const checkEl = document.getElementById("google-check");
    if (!statusEl || !disconnectBtn || !checkEl) {
      return;
    }
    let variant = "bad";
    if (state === "Connected") {
      variant = "ok";
    } else if (state === "Ready") {
      variant = "warn";
    } else if (state === "Error") {
      variant = "bad";
    }
    statusEl.textContent = state;
    statusEl.className = variant ? `status-pill ${variant}` : "status-pill";
    if (connected) {
      disconnectBtn.style.display = "inline-block";
      checkEl.style.display = "inline-block";
    } else {
      disconnectBtn.style.display = "none";
      checkEl.style.display = "none";
    }
  }

  function applyGoogleSettingsState(data) {
    if (!data || typeof data !== "object") {
      renderGsStatus("Not configured");
      renderGoogleHealthState("Missing info", false);
      return;
    }
    const ready = Boolean(data.has_client_id && data.has_client_secret);
    const connected = Boolean(data.connected);
    renderGsStatus(connected ? "Connected" : ready ? "Ready" : "Not configured");
    renderGoogleHealthState(connected ? "Connected" : ready ? "Ready" : "Missing info", connected);
  }

  async function gsFetch(method, path, body) {
    const headers = { ...tokenHeader(), "Content-Type": "application/json" };
    const response = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `${response.status}`);
    }
    return response.json();
  }

  async function gsLoad() {
    const payload = await gsFetch("GET", "/settings/google");
    const clientIdInput = document.getElementById("gs-client-id");
    const clientSecretInput = document.getElementById("gs-client-secret");
    if (clientIdInput) {
      clientIdInput.placeholder = payload.has_client_id ? payload.client_id_mask || "••••" : "";
      clientIdInput.value = "";
    }
    if (clientSecretInput) {
      clientSecretInput.placeholder = payload.has_client_secret ? "••••" : "";
      clientSecretInput.value = "";
    }
    applyGoogleSettingsState(payload);
  }

  async function gsSave() {
    const cidEl = document.getElementById("gs-client-id");
    const secEl = document.getElementById("gs-client-secret");
    const cid = cidEl ? cidEl.value.trim() : "";
    const sec = secEl ? secEl.value.trim() : "";
    const payload = {};
    if (cid) {
      payload.client_id = cid;
    }
    if (sec) {
      payload.client_secret = sec;
    }
    if (!payload.client_id && !payload.client_secret) {
      window.alert("Nothing to save.");
      return;
    }
    await gsFetch("POST", "/settings/google", payload);
    if (cidEl) {
      cidEl.value = "";
    }
    if (secEl) {
      secEl.value = "";
    }
    await gsLoad();
    window.alert("Saved.");
  }

  async function gsRemove() {
    if (!window.confirm("Remove Google OAuth client and disconnect?")) {
      return;
    }
    await gsFetch("DELETE", "/settings/google");
    await gsLoad();
  }

  async function gsTest() {
    try {
      const status = await gsFetch("GET", "/oauth/google/status");
      if (status && status.connected) {
        window.alert("Already connected.");
        return;
      }
      const response = await fetch("/oauth/google/start", {
        method: "POST",
        headers: { ...tokenHeader(), "Content-Type": "application/json" },
        body: "{}",
        cache: "no-store",
      });
      if (response.ok) {
        const payload = await response.json().catch(() => ({}));
        const authUrl = payload && payload.auth_url;
        window.alert("Client configured. Use Connect in Health to authorize.");
        if (typeof authUrl === "string" && authUrl) {
          // Optionally open the consent screen in a new tab for convenience.
          try {
            window.open(authUrl, "_blank");
          } catch (err) {
            // Ignore window.open failures (popup blockers, etc.).
          }
        }
      } else {
        const text = await response.text();
        window.alert(text || "Failed to start OAuth.");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      window.alert("Error: " + message);
    }
  }

  function initSettingsTab() {
    const saveBtn = document.getElementById("gs-save");
    const removeBtn = document.getElementById("gs-remove");
    const testBtn = document.getElementById("gs-test");
    if (!settingsInitialized) {
      if (saveBtn) {
        saveBtn.onclick = () => {
          gsSave().catch((error) => {
            const message = error instanceof Error ? error.message : String(error);
            window.alert(message);
          });
        };
      }
      if (removeBtn) {
        removeBtn.onclick = () => {
          gsRemove().catch((error) => {
            const message = error instanceof Error ? error.message : String(error);
            window.alert(message);
          });
        };
      }
      if (testBtn) {
        testBtn.onclick = () => {
          gsTest().catch((error) => {
            const message = error instanceof Error ? error.message : String(error);
            window.alert(message);
          });
        };
      }
      settingsDriveScopeInit();
      settingsInitialized = true;
    }
    gsLoad().catch(() => {
      renderGsStatus("Not configured");
      renderGoogleHealthState("Missing info", false);
    });
  }

  async function refreshGoogleStatus() {
    if (!hasToken()) {
      renderGoogleHealthState("Missing token", false);
      renderGsStatus("Not configured");
      return;
    }
    try {
      const payload = await gsFetch("GET", "/settings/google");
      applyGoogleSettingsState(payload);
    } catch (error) {
      renderGsStatus("Error");
      renderGoogleHealthState("Error", false);
    }
  }

  function showTab(name) {
    if (tabDashboardBtn) {
      tabDashboardBtn.classList.toggle("active", name === "dashboard");
    }
    if (tabSettingsBtn) {
      tabSettingsBtn.classList.toggle("active", name === "settings");
    }
    if (tabDashboard) {
      tabDashboard.style.display = name === "dashboard" ? "block" : "none";
    }
    if (tabSettings) {
      tabSettings.style.display = name === "settings" ? "block" : "none";
    }
    if (name === "settings") {
      initSettingsTab();
    }
  }

  function updateTokenBanner(show) {
    if (!tokenBanner) {
      return;
    }
    if (show) {
      tokenBanner.classList.remove("hidden");
    } else {
      tokenBanner.classList.add("hidden");
    }
  }

  function updatePanelMeta(panel, elapsedMs) {
    if (!panel) {
      return;
    }
    panel.timing.textContent = typeof elapsedMs === "number" ? `${elapsedMs} ms` : "—";
    panel.timestamp.textContent = new Date().toLocaleTimeString();
  }

  function setPanelError(panel, message) {
    if (!panel) {
      return;
    }
    panel.error.textContent = message || "";
  }

  function setPanelContent(panel, text) {
    if (!panel) {
      return;
    }
    panel.content.textContent = text;
  }

  function ensureToken(panel) {
    if (!currentToken) {
      updateTokenBanner(true);
      setPanelError(panel, "Session token required.");
      panel.timing.textContent = "—";
      panel.timestamp.textContent = "—";
      return false;
    }
    return true;
  }

  async function requestJSON(path, options, panelName) {
    const panel = panels[panelName];
    if (!panel) {
      return;
    }
    if (!ensureToken(panel)) {
      return;
    }

    const requestOptions = Object.assign({ method: "GET" }, options || {});
    const headers = Object.assign({}, requestOptions.headers || {}, {
      "X-Session-Token": currentToken,
    });
    if (requestOptions.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    requestOptions.headers = headers;

    setPanelError(panel, "");
    setPanelContent(panel, "Loading…");

    const start = performance.now();
    try {
      const response = await fetch(path, requestOptions);
      const elapsed = Math.round(performance.now() - start);
      if (!response.ok) {
        updatePanelMeta(panel, elapsed);
        let errorText = `${response.status} ${response.statusText}`;
        try {
          const payload = await response.clone().json();
          if (payload && payload.detail) {
            errorText += ` – ${payload.detail}`;
          }
        } catch (err) {
          // ignore JSON parsing failure for error body
        }
        if (response.status === 401) {
          updateTokenBanner(true);
        }
        setPanelError(panel, errorText);
        setPanelContent(panel, "");
        return;
      }

      const data = await response.json();
      updatePanelMeta(panel, Math.round(performance.now() - start));
      updateTokenBanner(false);
      renderPanel(panelName, data);
    } catch (error) {
      panel.timing.textContent = "—";
      panel.timestamp.textContent = "—";
      setPanelError(panel, error instanceof Error ? error.message : String(error));
      setPanelContent(panel, "");
    }
  }

  function renderPanel(panelName, data) {
    const panel = panels[panelName];
    if (!panel) {
      return;
    }
    setPanelError(panel, "");
    if (panelName === "logs") {
      const lines = Array.isArray(data.logs) ? data.logs : [];
      const text = lines.join("\n");
      setPanelContent(panel, text);
      if (logsAutoscroll && logsAutoscroll.checked) {
        panel.content.scrollTop = panel.content.scrollHeight;
      }
      return;
    }
    setPanelContent(panel, JSON.stringify(data, null, 2));
  }

  function getProbeServices() {
    try {
      const source = probeServices ? probeServices.value : "[]";
      const parsed = JSON.parse(source || "[]");
      if (Array.isArray(parsed)) {
        return parsed.map((item) => String(item));
      }
    } catch (error) {
      // handled by caller
    }
    return null;
  }

  async function refreshHealth() {
    await requestJSON("/health", { method: "GET" }, "health");
  }

  async function refreshPlugins() {
    await requestJSON("/plugins", { method: "GET" }, "plugins");
  }

  async function refreshCapabilities() {
    await requestJSON("/capabilities", { method: "GET" }, "capabilities");
  }

  async function refreshLogs() {
    await requestJSON("/logs", { method: "GET" }, "logs");
  }

  async function runProbe() {
    const panel = panels.probe;
    if (!panel) {
      return;
    }
    if (!ensureToken(panel)) {
      return;
    }
    const services = getProbeServices();
    if (!services) {
      setPanelError(panel, "Services must be a JSON array.");
      return;
    }
    await requestJSON(
      "/probe",
      {
        method: "POST",
        body: JSON.stringify({ services }),
      },
      "probe"
    );
  }

  function refreshAll() {
    refreshHealth();
    refreshPlugins();
    refreshCapabilities();
    refreshLogs();
    if (typeof refreshOutputsPanel === "function") {
      refreshOutputsPanel();
    }
  }

  async function gdRevoke() {
    const headers = tokenHeader();
    const response = await fetch(`/oauth/google/revoke`, {
      method: "POST",
      headers,
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error("revoke failed");
    }
  }

  async function initGoogleRow() {
    const disconnectBtn = document.getElementById("google-disconnect");
    if (!disconnectBtn) {
      return;
    }

    if (!googleRowInitialized) {
      disconnectBtn.onclick = () => {
        gdRevoke()
          .then(() => refreshGoogleStatus())
          .catch((error) => {
            const message = error instanceof Error ? error.message : String(error);
            window.alert(message);
          });
      };
      googleRowInitialized = true;
    }

    await refreshGoogleStatus();
  }

  function attachEvents() {
    if (saveTokenBtn) {
      saveTokenBtn.addEventListener("click", saveToken);
    }
    if (tokenInput) {
      tokenInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          saveToken();
        }
      });
    }
    if (refreshAllBtn) {
      refreshAllBtn.addEventListener("click", refreshAll);
    }
    if (panels.health?.refreshBtn) {
      panels.health.refreshBtn.addEventListener("click", refreshHealth);
    }
    if (panels.plugins?.refreshBtn) {
      panels.plugins.refreshBtn.addEventListener("click", refreshPlugins);
    }
    if (panels.capabilities?.refreshBtn) {
      panels.capabilities.refreshBtn.addEventListener("click", refreshCapabilities);
    }
    if (panels.logs?.refreshBtn) {
      panels.logs.refreshBtn.addEventListener("click", refreshLogs);
    }
    if (panels.probe?.refreshBtn) {
      panels.probe.refreshBtn.addEventListener("click", runProbe);
    }
    if (runProbeBtn) {
      runProbeBtn.addEventListener("click", runProbe);
    }
    if (tabDashboardBtn) {
      tabDashboardBtn.addEventListener("click", () => showTab("dashboard"));
    }
    if (tabSettingsBtn) {
      tabSettingsBtn.addEventListener("click", () => showTab("settings"));
    }
  }

  async function apiPluginRead(service, body) {
    const token = getSessionToken();
    const response = await fetch(`/plugins/${service}/read`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Token": token,
      },
      body: JSON.stringify(body || {}),
      cache: "no-store",
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || "Plugin read failed");
    }
    try {
      return await response.json();
    } catch (error) {
      return {};
    }
  }

  async function apiCatalogOpen(source, scope, options) {
    const token = getSessionToken();
    const response = await fetch(`/catalog/open`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Token": token,
      },
      body: JSON.stringify({ source, scope, options }),
    });
    if (!response.ok) {
      throw new Error("catalog open failed");
    }
    return response.json();
  }

  async function apiCatalogNext(streamId, maxItems = 500, timeBudgetMs = 600) {
    const token = getSessionToken();
    const response = await fetch(`/catalog/next`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Token": token,
      },
      body: JSON.stringify({
        stream_id: streamId,
        max_items: maxItems,
        time_budget_ms: timeBudgetMs,
      }),
    });
    if (!response.ok) {
      throw new Error("catalog next failed");
    }
    return response.json();
  }

  async function loadDriveScope() {
    const token = getSessionToken();
    const response = await fetch(`/settings/reader`, {
      method: "GET",
      headers: { "X-Session-Token": token },
    });
    if (!response.ok) {
      throw new Error("load drive scope failed");
    }
    const data = await response.json();
    return (data && data.drive_includes) || {};
  }

  async function saveDriveScope(driveIncludes) {
    const token = getSessionToken();
    const response = await fetch(`/settings/reader`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Token": token,
      },
      body: JSON.stringify({ drive_includes: driveIncludes }),
    });
    if (!response.ok) {
      throw new Error("save drive scope failed");
    }
    return response.json();
  }

  async function fetchSharedDrives() {
    const token = getSessionToken();
    const response = await fetch(`/drive/available_drives`, {
      method: "GET",
      headers: { "X-Session-Token": token },
    });
    if (!response.ok) {
      return { drives: [] };
    }
    try {
      return await response.json();
    } catch (error) {
      return { drives: [] };
    }
  }

  function settingsDriveScopeInit() {
    const cbMy = document.getElementById("di-my");
    const cbShared = document.getElementById("di-shared");
    const listEl = document.getElementById("di-shared-list");
    const saveBtn = document.getElementById("di-save");
    const pickBtn = document.getElementById("di-pick-root");
    const rootLabel = document.getElementById("di-root-label");

    if (!cbMy || !cbShared || !listEl || !saveBtn || !pickBtn || !rootLabel) {
      return;
    }

    let model = {
      include_my_drive: true,
      my_drive_root_id: null,
      include_shared_drives: true,
      shared_drive_ids: [],
    };

    function updateRootLabel() {
      rootLabel.textContent = model.my_drive_root_id
        ? `Root: ${model.my_drive_root_id}`
        : "Root: actual My Drive root";
    }

    function syncSharedDisabled() {
      const disabled = !cbShared.checked;
      listEl.querySelectorAll("input[type='checkbox']").forEach((node) => {
        node.disabled = disabled;
      });
    }

    (async () => {
      try {
        const di = await loadDriveScope();
        if (di && typeof di === "object") {
          model = {
            ...model,
            ...di,
            shared_drive_ids: Array.isArray(di.shared_drive_ids)
              ? Array.from(
                  new Set(
                    di.shared_drive_ids.filter((value) => typeof value === "string" && value)
                  )
                )
              : [],
          };
        }
      } catch (error) {
        // ignore load errors
      }

      cbMy.checked = Boolean(model.include_my_drive);
      cbShared.checked = Boolean(model.include_shared_drives);
      updateRootLabel();

      try {
        const data = await fetchSharedDrives();
        listEl.innerHTML = "";
        (data.drives || []).forEach((drive) => {
          if (!drive || typeof drive !== "object") {
            return;
          }
          const id = String(drive.id || "");
          const name = String(drive.name || id);
          const row = document.createElement("div");
          row.className = "drive-row";
          const cb = document.createElement("input");
          cb.type = "checkbox";
          cb.checked = model.shared_drive_ids.includes(id);
          cb.onchange = () => {
            if (cb.checked) {
              if (!model.shared_drive_ids.includes(id)) {
                model.shared_drive_ids.push(id);
              }
            } else {
              model.shared_drive_ids = model.shared_drive_ids.filter((x) => x !== id);
            }
          };
          const label = document.createElement("span");
          label.textContent = `${name} (${id})`;
          row.appendChild(cb);
          row.appendChild(label);
          listEl.appendChild(row);
        });
      } catch (error) {
        listEl.innerHTML = "<span class='muted'>Unable to load shared drives</span>";
      }

      syncSharedDisabled();
    })();

    cbMy.onchange = () => {
      model.include_my_drive = cbMy.checked;
    };

    cbShared.onchange = () => {
      model.include_shared_drives = cbShared.checked;
      syncSharedDisabled();
    };

    pickBtn.onclick = () => {
      const currentValue = model.my_drive_root_id || "";
      const next = window.prompt(
        "Enter My Drive folder ID (leave blank for actual My Drive root):",
        currentValue.startsWith("drive:") ? currentValue : currentValue ? `drive:${currentValue}` : ""
      );
      if (next && next.trim()) {
        const cleaned = next.trim();
        model.my_drive_root_id = cleaned.startsWith("drive:") ? cleaned : `drive:${cleaned}`;
      } else {
        model.my_drive_root_id = null;
      }
      updateRootLabel();
    };

    saveBtn.onclick = async () => {
      const payload = {
        include_my_drive: Boolean(model.include_my_drive),
        my_drive_root_id: model.my_drive_root_id,
        include_shared_drives: Boolean(model.include_shared_drives),
        shared_drive_ids: Array.isArray(model.shared_drive_ids)
          ? Array.from(
              new Set(
                model.shared_drive_ids.filter((value) => typeof value === "string" && value)
              )
            )
          : [],
      };
      try {
        await saveDriveScope(payload);
        window.alert("Drive scope saved.");
      } catch (error) {
        window.alert("Failed to save drive scope.");
      }
    };
  }

  async function apiCatalogClose(streamId) {
    const token = getSessionToken();
    await fetch(`/catalog/close`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Token": token,
      },
      body: JSON.stringify({ stream_id: streamId }),
    });
  }

  function readerTreeInit() {
    const treeEl = document.getElementById("reader-tree");
    const sourceSelect = document.getElementById("reader-source");
    const refreshBtn = document.getElementById("outputs-refresh");
    const indexBtn = document.getElementById("reader-index-all");
    if (!treeEl || !sourceSelect || !refreshBtn) {
      return;
    }

    async function loadChildren(nodeId, source) {
      const data = await apiPluginRead("reader", {
        op: "children",
        params: { source, parent_id: nodeId },
      });
      const children = data && Array.isArray(data.children) ? data.children : [];
      return children;
    }

    function renderList(parentEl, nodes, source) {
      const listEl = document.createElement("ul");
      nodes.forEach((node) => {
        if (!node || typeof node !== "object") {
          return;
        }
        const li = document.createElement("li");
        const row = document.createElement("div");
        row.className = "node";
        const toggle = document.createElement("span");
        toggle.className = "toggle";
        toggle.textContent = node.has_children ? "▸" : "•";
        row.appendChild(toggle);
        const label = document.createElement("span");
        label.textContent = node.name || node.id;
        row.appendChild(label);
        li.appendChild(row);
        if (node.has_children) {
          let expanded = false;
          let childList = null;
          toggle.addEventListener("click", async () => {
            if (!expanded) {
              toggle.textContent = "▾";
              try {
                const children = await loadChildren(node.id, source);
                if (childList) {
                  childList.remove();
                }
                childList = renderList(li, children, source);
                expanded = true;
              } catch (error) {
                toggle.textContent = "▸";
                const message = error instanceof Error ? error.message : String(error);
                li.querySelectorAll(".tree-error").forEach((el) => el.remove());
                const errNode = document.createElement("div");
                errNode.className = "tree-error";
                errNode.textContent = message;
                li.appendChild(errNode);
              }
            } else {
              if (childList) {
                childList.remove();
                childList = null;
              }
              toggle.textContent = "▸";
              expanded = false;
            }
          });
        }
        listEl.appendChild(li);
      });
      parentEl.appendChild(listEl);
      return listEl;
    }

    async function renderRoot() {
      if (!hasToken()) {
        treeEl.textContent = "Session token required.";
        return;
      }
      treeEl.textContent = "Loading…";
      const source = sourceSelect.value;
      const rootId = source === "local" ? "local:root" : "drive:root";
      try {
        const nodes = await loadChildren(rootId, source);
        treeEl.innerHTML = "";
        if (!nodes.length) {
          treeEl.textContent = "No entries.";
          return;
        }
        renderList(treeEl, nodes, source);
      } catch (error) {
        treeEl.textContent = error instanceof Error ? error.message : String(error);
      }
    }

    refreshBtn.addEventListener("click", () => {
      renderRoot();
    });
    if (indexBtn) {
      indexBtn.addEventListener("click", async () => {
        if (!hasToken()) {
          window.alert("Session token required.");
          return;
        }
        const source = sourceSelect.value;
        const scope = source === "drive" ? "allDrives" : "local_roots";
        const provider = source === "drive" ? "google_drive" : "local_fs";
        let streamId;
        try {
          const openPayload = await apiCatalogOpen(provider, scope, {
            recursive: true,
            page_size: 500,
            fingerprint: false,
          });
          streamId = openPayload?.stream_id;
          if (!streamId) {
            throw new Error("Missing stream id");
          }
          try {
            for (;;) {
              const { items, done } = await apiCatalogNext(streamId, 500, 600);
              if (done) {
                break;
              }
              if (!items || !Array.isArray(items) || !items.length) {
                await new Promise((resolve) => setTimeout(resolve, 50));
              }
            }
          } finally {
            await apiCatalogClose(streamId);
          }
          window.alert("Indexing complete (metadata persisted under data/catalog/)");
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          window.alert(`Indexing failed: ${message}`);
        } finally {
          renderRoot();
        }
      });
    }
    sourceSelect.addEventListener("change", () => {
      renderRoot();
    });

    refreshOutputsPanel = renderRoot;
    renderRoot();
  }

  function readerOutputsInit() {
    const statusEl = document.getElementById("reader-status");
    const sourceSel = document.getElementById("reader-source");
    const btnFull = document.getElementById("reader-fullpull");
    const btnCancel = document.getElementById("reader-cancelpull");
    const progEl = document.getElementById("reader-progress");
    const logEl = document.getElementById("reader-log");

    if (!statusEl || !btnFull || !btnCancel || !progEl) {
      return;
    }

    function logReset() {
      if (!logEl) {
        return;
      }
      logEl.textContent = "No entries.";
    }

    function logAppend(lines) {
      if (!logEl) {
        return;
      }
      const text = Array.isArray(lines) ? lines.join("\n") : String(lines);
      if (logEl.textContent === "No entries.") {
        logEl.textContent = "";
      }
      logEl.textContent += `${text}\n`;
      logEl.scrollTop = logEl.scrollHeight;
    }

    // --- Auto-check on load ---
    (async () => {
      try {
        const s = await apiPluginRead("reader", { op: "autocheck", params: {} });
        const bits = [];
        if (s.drive) {
          const ok = s.drive.configured && s.drive.can_exchange_token;
          bits.push(`Drive: ${ok ? "ready" : s.drive.configured ? "auth error" : "not configured"}`);
        }
        if (s.local) {
          bits.push(`Local: ${s.local.configured ? "configured" : "not configured"}`);
        }
        statusEl.textContent = bits.join(" • ");
      } catch (error) {
        statusEl.textContent = "Status: unavailable";
      }
    })();

    // --- Full pull state ---
    let pulling = false;
    let streamId = null;
    let total = 0;

    async function doFullPull() {
      pulling = true;
      total = 0;
      btnFull.disabled = true;
      btnCancel.disabled = true; // enabled after open succeeds
      progEl.textContent = "Opening…";
      logReset();

      try {
        const src = sourceSel ? sourceSel.value : "drive";
        const opened = await apiPluginRead("reader", {
          op: "start_full_pull",
          params: { source: src, recursive: true, page_size: 500 },
        });
        streamId = opened.stream_id;
        if (!streamId) {
          throw new Error("no stream");
        }

        btnCancel.disabled = false;

        while (pulling) {
          const page = await apiCatalogNext(streamId, 500, 600);
          const items = Array.isArray(page.items) ? page.items : [];
          total += items.length;

          const preview = items
            .slice(0, 5)
            .map((item) => `• ${item.name} (${item.type})`);
          if (preview.length) {
            logAppend(preview);
          }

          progEl.textContent = page.done
            ? `Done. Indexed ${total} items.`
            : `Fetched ${total} items…`;

          if (page.done) {
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 50));
        }
      } catch (error) {
        progEl.textContent = "Full pull failed";
        logAppend("! error during full pull");
      } finally {
        try {
          if (streamId) {
            await apiCatalogClose(streamId);
          }
        } catch (closeError) {
          // ignore
        }
        btnFull.disabled = false;
        btnCancel.disabled = true;
        pulling = false;
        streamId = null;
      }
    }

    btnFull.onclick = () => {
      if (pulling) {
        return;
      }
      if (!hasToken()) {
        window.alert("Session token required.");
        return;
      }
      doFullPull();
    };
    btnCancel.onclick = () => {
      if (!pulling) {
        return;
      }
      pulling = false;
      progEl.textContent = "Cancelling…";
    };
  }

  loadToken();
  attachEvents();
  if (currentToken) {
    refreshAll();
  }

  window.addEventListener("DOMContentLoaded", () => {
    if (hasToken()) {
      initGoogleRow();
    } else {
      renderGoogleHealthState("Missing token", false);
      renderGsStatus("Not configured");
    }
    readerOutputsInit();
    readerTreeInit();
  });
})();
