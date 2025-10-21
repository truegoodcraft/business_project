(function () {
  const TOKEN_STORAGE_KEY = "tgc_token";
  let currentToken = "";
  let settingsInitialized = false;

  const tokenInput = document.getElementById("token-input");
  const saveTokenBtn = document.getElementById("save-token");
  const refreshAllBtn = document.getElementById("refresh-all");
  const tokenBanner = document.getElementById("token-banner");
  const tabDashboardBtn = document.getElementById("tab-btn-dashboard");
  const tabSettingsBtn = document.getElementById("tab-btn-settings");
  const tabDashboard = document.getElementById("tab-dashboard");
  const tabSettings = document.getElementById("tab-settings");
  const logsAutoscroll = document.getElementById("logs-autoscroll");

  let healthRefresh = () => {};
  let capsRefresh = () => {};
  let pluginsRefresh = () => {};
  let logsRefresh = () => {};
  let outputsRefresh = () => {};
  let settingsLocalRefresh = () => Promise.resolve();
  let settingsLocalInitialized = false;

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

  function loadToken() {
    const stored = window.localStorage.getItem(TOKEN_STORAGE_KEY) || "";
    currentToken = stored;
    if (tokenInput) {
      tokenInput.value = stored;
    }
    updateTokenBanner(!currentToken);
  }

  function saveToken() {
    const next = tokenInput ? tokenInput.value.trim() : "";
    window.localStorage.setItem(TOKEN_STORAGE_KEY, next);
    currentToken = next;
    updateTokenBanner(!currentToken);
    refreshAll();
  }

  function getSessionToken() {
    if (!currentToken) {
      throw new Error("Session token required");
    }
    return currentToken;
  }

  function latestToken() {
    return getSessionToken();
  }

  async function apiJson(path, method = "GET", body = null) {
    const headers = {
      "Content-Type": "application/json",
      "X-Session-Token": latestToken(),
    };
    const response = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });
    if (!response.ok) {
      let text = "";
      try {
        text = await response.text();
      } catch (error) {
        text = "";
      }
      const err = new Error(`${path} failed ${response.status}${text ? `: ${text}` : ""}`);
      err.status = response.status;
      if (text) {
        try {
          const parsed = JSON.parse(text);
          err.body = parsed;
          if (parsed && typeof parsed === "object" && "detail" in parsed) {
            err.detail = parsed.detail;
          }
        } catch (parseError) {
          err.body = text;
        }
      }
      throw err;
    }
    if (response.status === 204) {
      return {};
    }
    return response.json();
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

  function renderGsStatus(state) {
    const el = document.getElementById("gs-status");
    if (!el) {
      return;
    }
    const variant = state === "Connected" ? "ok" : state === "Ready" ? "warn" : state === "Error" ? "bad" : "bad";
    el.textContent = state;
    el.className = variant ? `status-pill ${variant}` : "status-pill";
  }

  async function gsLoad() {
    if (!currentToken) {
      renderGsStatus("Not configured");
      return;
    }
    try {
      const payload = await apiJson("/settings/google");
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
      const ready = Boolean(payload.has_client_id && payload.has_client_secret);
      const connected = Boolean(payload.connected);
      renderGsStatus(connected ? "Connected" : ready ? "Ready" : "Not configured");
    } catch (error) {
      renderGsStatus("Error");
    }
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
    try {
      await apiJson("/settings/google", "POST", payload);
      if (cidEl) {
        cidEl.value = "";
      }
      if (secEl) {
        secEl.value = "";
      }
      await gsLoad();
      window.alert("Saved.");
    } catch (error) {
      window.alert("Failed to save settings.");
    }
  }

  async function gsRemove() {
    if (!window.confirm("Remove Google OAuth client and disconnect?")) {
      return;
    }
    try {
      await apiJson("/settings/google", "DELETE", {});
      await gsLoad();
    } catch (error) {
      window.alert("Failed to remove client.");
    }
  }

  async function gsTest() {
    try {
      const status = await apiJson("/oauth/google/status");
      if (status && status.connected) {
        window.alert("Already connected.");
        return;
      }
    } catch (error) {
      // ignore status errors and continue
    }
    try {
      const payload = await apiJson("/oauth/google/start", "POST", {});
      window.alert("Client configured. Use Connect in Health to authorize.");
      if (payload && payload.auth_url) {
        try {
          window.open(payload.auth_url, "_blank");
        } catch (err) {
          // ignore popup blockers
        }
      }
    } catch (error) {
      window.alert("Failed to start OAuth.");
    }
  }

  async function loadDriveScope() {
    const data = await apiJson("/settings/reader");
    return (data && data.drive_includes) || {};
  }

  async function saveDriveScope(driveIncludes) {
    await apiJson("/settings/reader", "POST", { drive_includes: driveIncludes });
  }

  async function fetchSharedDrives() {
    try {
      return await apiJson("/drive/available_drives");
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
        const includes = await loadDriveScope();
        if (includes && typeof includes === "object") {
          model = {
            ...model,
            ...includes,
            shared_drive_ids: Array.isArray(includes.shared_drive_ids)
              ? Array.from(
                  new Set(
                    includes.shared_drive_ids.filter((value) => typeof value === "string" && value)
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
              new Set(model.shared_drive_ids.filter((value) => typeof value === "string" && value))
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

  async function settingsLocalInit() {
    const scanBtn = document.getElementById("ls-scan");
    const folderIn = document.getElementById("ls-folder");
    const validateBtn = document.getElementById("ls-validate");
    const addBtn = document.getElementById("ls-add");
    const msgEl = document.getElementById("ls-msg");
    const drivesEl = document.getElementById("ls-drives");
    const selectedEl = document.getElementById("ls-selected");
    const saveBtn = document.getElementById("ls-save");

    if (
      !scanBtn ||
      !folderIn ||
      !validateBtn ||
      !addBtn ||
      !msgEl ||
      !drivesEl ||
      !selectedEl ||
      !saveBtn
    ) {
      return;
    }

    if (settingsLocalInitialized) {
      await settingsLocalRefresh().catch(() => {});
      return;
    }

    settingsLocalInitialized = true;

    let model = { roots: [] };

    function note(text) {
      msgEl.textContent = text || "";
    }

    function syncDriveChecks() {
      drivesEl.querySelectorAll("input[type='checkbox']").forEach((node) => {
        const path = node.dataset ? node.dataset.path || "" : "";
        if (path) {
          node.checked = model.roots.includes(path);
        }
      });
    }

    function renderSelected() {
      selectedEl.innerHTML = "";
      if (!model.roots.length) {
        const empty = document.createElement("div");
        empty.className = "muted";
        empty.textContent = "None";
        selectedEl.appendChild(empty);
      } else {
        model.roots.forEach((path) => {
          const row = document.createElement("div");
          row.style.display = "flex";
          row.style.alignItems = "center";
          row.style.justifyContent = "space-between";
          row.style.gap = "12px";
          const label = document.createElement("span");
          label.textContent = path;
          const removeBtn = document.createElement("button");
          removeBtn.className = "btn btn-secondary";
          removeBtn.textContent = "Remove";
          removeBtn.onclick = () => {
            model.roots = model.roots.filter((item) => item !== path);
            renderSelected();
          };
          row.appendChild(label);
          row.appendChild(removeBtn);
          selectedEl.appendChild(row);
        });
      }
      syncDriveChecks();
    }

    async function loadCurrent() {
      try {
        const settings = await apiJson("/settings/reader", "GET");
        const roots = Array.isArray(settings.local_roots)
          ? settings.local_roots.filter((value) => typeof value === "string" && value)
          : [];
        model.roots = Array.from(new Set(roots));
      } catch (error) {
        model.roots = [];
      }
      renderSelected();
    }

    scanBtn.onclick = async () => {
      drivesEl.innerHTML = "Scanning…";
      try {
        const response = await apiJson("/local/available_drives", "GET");
        drivesEl.innerHTML = "";
        const drives = Array.isArray(response.drives) ? response.drives : [];
        drives.forEach((drive) => {
          if (!drive || typeof drive !== "object") {
            return;
          }
          const path = String(drive.path || "").trim();
          if (!path) {
            return;
          }
          const row = document.createElement("div");
          row.style.display = "flex";
          row.style.alignItems = "center";
          row.style.gap = "6px";
          const cb = document.createElement("input");
          cb.type = "checkbox";
          cb.dataset.path = path;
          cb.checked = model.roots.includes(path);
          cb.onchange = () => {
            if (cb.checked) {
              if (!model.roots.includes(path)) {
                model.roots.push(path);
                model.roots = Array.from(new Set(model.roots));
              }
            } else {
              model.roots = model.roots.filter((item) => item !== path);
            }
            renderSelected();
          };
          const label = document.createElement("span");
          const suffix = drive.label ? ` — ${drive.label}` : "";
          label.textContent = `${path}${suffix}`;
          row.appendChild(cb);
          row.appendChild(label);
          const addSub = document.createElement("button");
          addSub.className = "btn btn-secondary";
          addSub.textContent = "Add subfolder…";
          addSub.style.marginLeft = "8px";
          addSub.onclick = () => {
            folderIn.value = path;
            folderIn.focus();
            note(`Enter a subfolder inside ${path} then Validate → Add`);
          };
          row.appendChild(addSub);
          drivesEl.appendChild(row);
        });
        if (!drivesEl.children.length) {
          const empty = document.createElement("div");
          empty.className = "muted";
          empty.textContent = "No drives found";
          drivesEl.appendChild(empty);
        }
        syncDriveChecks();
      } catch (error) {
        drivesEl.textContent = "Failed to scan drives";
      }
    };

    validateBtn.onclick = async () => {
      const inputPath = folderIn.value.trim();
      if (!inputPath) {
        note("Enter a folder path");
        return;
      }
      try {
        const result = await apiJson(
          `/local/validate_path?path=${encodeURIComponent(inputPath)}`,
          "GET"
        );
        if (result && result.ok) {
          note(`OK: ${result.path}`);
          folderIn.value = result.path || inputPath;
        } else {
          const reason = result && result.reason ? result.reason : "invalid";
          note(`Invalid: ${reason}`);
        }
      } catch (error) {
        note("Validate failed");
      }
    };

    addBtn.onclick = () => {
      const path = folderIn.value.trim();
      if (!path) {
        note("Enter a folder path");
        return;
      }
      if (!model.roots.includes(path)) {
        model.roots.push(path);
        model.roots = Array.from(new Set(model.roots));
      }
      renderSelected();
      note("");
    };

    saveBtn.onclick = async () => {
      try {
        await apiJson("/settings/reader", "POST", { local_roots: model.roots });
        note("Saved.");
        await loadCurrent();
      } catch (error) {
        note("Save failed");
      }
    };

    settingsLocalRefresh = () => loadCurrent();

    await loadCurrent();
  }

  function initSettingsTab() {
    if (settingsInitialized) {
      gsLoad().catch(() => renderGsStatus("Error"));
      settingsLocalRefresh().catch(() => {});
      return;
    }
    const saveBtn = document.getElementById("gs-save");
    const removeBtn = document.getElementById("gs-remove");
    const testBtn = document.getElementById("gs-test");
    if (saveBtn) {
      saveBtn.onclick = () => {
        gsSave().catch(() => window.alert("Failed to save settings."));
      };
    }
    if (removeBtn) {
      removeBtn.onclick = () => {
        gsRemove().catch(() => window.alert("Failed to remove client."));
      };
    }
    if (testBtn) {
      testBtn.onclick = () => {
        gsTest().catch(() => window.alert("Failed to start OAuth."));
      };
    }
    settingsDriveScopeInit();
    settingsLocalInit().catch(() => {});
    settingsInitialized = true;
    gsLoad().catch(() => renderGsStatus("Error"));
    settingsLocalRefresh().catch(() => {});
  }

  function healthInit() {
    const driveStatus = document.getElementById("health-drive-status");
    const btnDisc = document.getElementById("btn-drive-disconnect");
    const btnReboot = document.getElementById("btn-server-restart");
    if (!driveStatus || !btnDisc || !btnReboot) {
      return;
    }

    async function load() {
      if (!currentToken) {
        driveStatus.textContent = "Token required";
        driveStatus.classList.add("muted");
        btnDisc.disabled = true;
        return;
      }
      btnDisc.disabled = false;
      try {
        const status = await apiJson("/plugins/reader/read", "POST", { op: "autocheck", params: {} });
        const connected = Boolean(status.drive && status.drive.can_exchange_token);
        driveStatus.textContent = connected ? "Connected" : "Not connected";
        driveStatus.classList.toggle("muted", !connected);
      } catch (error) {
        driveStatus.textContent = "Unavailable";
        driveStatus.classList.add("muted");
      }
    }

    btnDisc.onclick = async () => {
      if (!currentToken) {
        return;
      }
      try {
        await apiJson("/oauth/google/revoke", "POST", {});
        window.alert("Disconnected");
        await load();
      } catch (error) {
        window.alert("Failed to disconnect");
      }
    };

    btnReboot.onclick = async () => {
      if (!window.confirm("Exit process now? Restart manually.")) {
        return;
      }
      try {
        await apiJson("/server/restart", "POST", {});
      } catch (error) {
        // ignore; process may exit before response
      }
    };

    load();
    healthRefresh = load;
  }

  function capsInit() {
    const list = document.getElementById("cap-list");
    const filter = document.getElementById("cap-filter");
    if (!list || !filter) {
      return;
    }

    let caps = [];

    function render(query = "") {
      list.innerHTML = "";
      const q = query.toLowerCase();
      const groups = {};
      caps.forEach((cap) => {
        if (!cap || typeof cap !== "object") {
          return;
        }
        const provider = String(cap.provider || "unknown");
        const ability = String(cap.cap || "");
        if (q && !(ability.toLowerCase().includes(q) || provider.toLowerCase().includes(q))) {
          return;
        }
        (groups[provider] ||= []).push({ ability, status: cap.status || "" });
      });

      const providers = Object.keys(groups);
      if (!providers.length) {
        const empty = document.createElement("div");
        empty.className = "muted";
        empty.textContent = q ? "No matches." : caps.length ? "No capabilities." : "Token required.";
        list.appendChild(empty);
        return;
      }

      providers.forEach((provider) => {
        const header = document.createElement("div");
        header.style.cursor = "pointer";
        header.innerHTML = `<strong>${provider}</strong> <span class="muted">(${groups[provider].length})</span>`;
        const body = document.createElement("div");
        body.style.margin = "4px 0 8px 10px";
        groups[provider].forEach((cap) => {
          const row = document.createElement("div");
          const statusIcon = cap.status === "ready" ? "✓" : "•";
          row.textContent = `${statusIcon} ${cap.ability}`;
          body.appendChild(row);
        });
        let collapsed = false;
        header.onclick = () => {
          collapsed = !collapsed;
          body.style.display = collapsed ? "none" : "block";
        };
        list.appendChild(header);
        list.appendChild(body);
      });
    }

    async function load() {
      if (!currentToken) {
        caps = [];
        render(filter.value);
        return;
      }
      try {
        const data = await apiJson("/capabilities");
        caps = Array.isArray(data.capabilities) ? data.capabilities : [];
        render(filter.value);
      } catch (error) {
        list.innerHTML = "<div class='muted'>Failed to load capabilities.</div>";
      }
    }

    filter.oninput = () => {
      render(filter.value);
    };

    load();
    capsRefresh = load;
  }

  function pluginsInit() {
    const list = document.getElementById("plugin-list");
    const filter = document.getElementById("plugin-filter");
    if (!list || !filter) {
      return;
    }

    let items = [];

    function render(query = "") {
      list.innerHTML = "";
      const q = query.toLowerCase();
      const filtered = items.filter((item) => {
        const id = String(item.id || "");
        const name = String(item.name || "");
        return !q || id.toLowerCase().includes(q) || name.toLowerCase().includes(q);
      });
      if (!filtered.length) {
        const empty = document.createElement("div");
        empty.className = "muted";
        empty.textContent = q ? "No matches." : items.length ? "No plugins." : "Token required.";
        list.appendChild(empty);
        return;
      }
      filtered.forEach((item) => {
        const row = document.createElement("div");
        const badge = item.builtin ? " [built-in]" : "";
        row.textContent = `${item.id} — ${item.name} (v${item.version || "?"})${badge} `;

        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.checked = !!item.enabled;
        cb.onchange = async () => {
          try {
            await apiJson(`/plugins/${item.id}/enable`, "POST", { enabled: cb.checked });
            await load();
          } catch (error) {
            cb.checked = !cb.checked;
            window.alert("Failed to update plugin state.");
          }
        };

        const enabledText = document.createElement("span");
        enabledText.textContent = "[Enabled ";
        enabledText.style.marginLeft = "4px";
        row.appendChild(enabledText);
        row.appendChild(cb);
        const closing = document.createTextNode("]");
        row.appendChild(closing);
        list.appendChild(row);
      });
    }

    async function load() {
      if (!currentToken) {
        items = [];
        render(filter.value);
        return;
      }
      try {
        const data = await apiJson("/plugins");
        items = Array.isArray(data.plugins)
          ? data.plugins.map((p) => ({
              id: p.id,
              name: p.name,
              version: p.version,
              builtin: !!p.builtin,
              enabled: p.enabled !== false,
            }))
          : [];
        render(filter.value);
      } catch (error) {
        list.innerHTML = "<div class='muted'>Failed to load plugins.</div>";
      }
    }

    filter.oninput = () => {
      render(filter.value);
    };

    load();
    pluginsRefresh = load;
  }

  function logsInit() {
    const content = document.getElementById("logs-content");
    const refreshBtn = document.getElementById("logs-refresh");
    if (!content) {
      return;
    }

    async function load() {
      if (!currentToken) {
        content.textContent = "Token required.";
        return;
      }
      try {
        const data = await apiJson("/logs");
        const lines = Array.isArray(data.logs) ? data.logs : [];
        content.textContent = lines.join("\n");
        if (logsAutoscroll && logsAutoscroll.checked) {
          content.scrollTop = content.scrollHeight;
        }
      } catch (error) {
        content.textContent = "Failed to load logs.";
      }
    }

    if (refreshBtn) {
      refreshBtn.onclick = () => {
        load();
      };
    }

    load();
    logsRefresh = load;
  }

  function outputsInit() {
    const srcSel = document.getElementById("out-source");
    const listEl = document.getElementById("out-list");
    const bcEl = document.getElementById("out-breadcrumb");
    const backBtn = document.getElementById("out-back");
    const searchEl = document.getElementById("out-search");
    const logEl = document.getElementById("out-log");
    const indexBtn = document.getElementById("out-index");
    const refreshBtn = document.getElementById("outputs-refresh");
    const ctxMenu = document.getElementById("ctx-menu");
    if (!srcSel || !listEl || !bcEl || !backBtn || !searchEl || !logEl || !indexBtn || !refreshBtn || !ctxMenu) {
      return;
    }

    const stack = [];
    let currentItems = [];

    function log(message) {
      if (logEl.textContent === "No entries.") {
        logEl.textContent = "";
      }
      logEl.textContent += message + "\n";
      logEl.scrollTop = logEl.scrollHeight;
    }

    function setListMessage(message) {
      listEl.innerHTML = `<div class="muted">${message}</div>`;
    }

    function updateBreadcrumb() {
      bcEl.textContent = stack.map((entry) => entry.name).join(" / ");
      backBtn.disabled = stack.length <= 1;
    }

    function current() {
      return stack[stack.length - 1];
    }

    function rootFor(source) {
      if (source === "local") {
        return { parent_id: "local:root", name: "Local", source: "local" };
      }
      if (source === "drive") {
        return { parent_id: "drive:root", name: "Drive", source: "drive" };
      }
      return { parent_id: "drive:root", name: "Reader", source: "reader" };
    }

    async function loadChildrenBySource(source, parentId) {
      if (source === "reader") {
        const response = await apiJson("/plugins/reader/read", "POST", {
          op: "children",
          params: { source: "drive", parent_id: parentId, page_size: 200 },
        });
        return Array.isArray(response.children) ? response.children : [];
      }
      if (source === "drive") {
        const response = await apiJson("/plugins/google_drive/read", "POST", {
          op: "children",
          params: { parent_id: parentId, page_size: 200 },
        });
        return Array.isArray(response.children) ? response.children : [];
      }
      if (source === "local") {
        const response = await apiJson("/plugins/local/read", "POST", {
          op: "children",
          params: { parent_id: parentId },
        });
        return Array.isArray(response.children) ? response.children : [];
      }
      return [];
    }

    async function loadChildren(source, parentId) {
      if (!currentToken) {
        throw new Error("token_required");
      }
      try {
        return await loadChildrenBySource(source, parentId);
      } catch (error) {
        if (error && (error.status === 403 || error.detail === "plugin_disabled")) {
          error.code = "plugin_disabled";
        }
        throw error;
      }
    }

    function draw() {
      ctxMenu.style.display = "none";
      listEl.innerHTML = "";
      const query = (searchEl.value || "").toLowerCase();
      const filtered = currentItems.filter((item) => {
        const name = String(item.name || "");
        return !query || name.toLowerCase().includes(query);
      });
      if (!filtered.length) {
        const empty = document.createElement("div");
        empty.className = "muted";
        empty.textContent = currentItems.length ? "No matches." : "No items.";
        listEl.appendChild(empty);
        return;
      }

      filtered.forEach((item) => {
        const row = document.createElement("div");
        row.className = "row";
        const icon = item.type === "folder" || item.type === "shortcut" ? "📁" : "📄";
        row.textContent = `${icon} ${item.name}`;
        row.style.cursor = item.type === "folder" || item.type === "shortcut" ? "pointer" : "default";

        row.onclick = async () => {
          if (item.type === "folder" || item.type === "shortcut") {
            const entry = { source: srcSel.value, parent_id: item.id, name: item.name || "" };
            stack.push(entry);
            updateBreadcrumb();
            try {
              const children = await loadChildren(entry.source, entry.parent_id);
              currentItems = children;
              draw();
            } catch (error) {
              stack.pop();
              updateBreadcrumb();
              if (error && error.code === "plugin_disabled") {
                setListMessage("Plugin disabled.");
              } else {
                setListMessage("Failed to load items.");
              }
            }
          }
        };

        row.oncontextmenu = (event) => {
          event.preventDefault();
          ctxMenu.innerHTML = "";
          const menuItems = [];

          const source = item.source || (srcSel.value === "reader" ? "drive" : srcSel.value);
          if (source === "google_drive" || source === "drive") {
            const isFolder = item.type === "folder" || String(item.mimeType || "").includes("folder");
            const raw = String(item.id || "").replace(/^drive:/, "");
            const url = isFolder
              ? `https://drive.google.com/drive/folders/${raw}`
              : `https://drive.google.com/file/d/${raw}/view`;
            menuItems.push({
              label: "Open in Drive (browser)",
              action: () => {
                window.open(url, "_blank");
              },
            });
          }

          if (source === "local_fs" || source === "local") {
            menuItems.push({
              label: "Open in Explorer",
              action: async () => {
                try {
                  await apiJson("/open/local", "POST", { id: item.id });
                } catch (error) {
                  window.alert("Failed to open item.");
                }
              },
            });
          }

          if (!menuItems.length) {
            ctxMenu.style.display = "none";
            return;
          }

          menuItems.forEach((menuItem) => {
            const option = document.createElement("div");
            option.textContent = menuItem.label;
            option.style.padding = "4px 8px";
            option.style.cursor = "pointer";
            option.onclick = () => {
              ctxMenu.style.display = "none";
              menuItem.action();
            };
            ctxMenu.appendChild(option);
          });

          ctxMenu.style.left = `${event.pageX}px`;
          ctxMenu.style.top = `${event.pageY}px`;
          ctxMenu.style.display = "block";
        };

        listEl.appendChild(row);
      });
    }

    document.body.addEventListener("click", () => {
      ctxMenu.style.display = "none";
    });

    searchEl.oninput = () => {
      draw();
    };

    async function getIndexStatus() {
      return apiJson("/index/status", "GET");
    }

    async function updateIndexState(partial) {
      return apiJson("/index/state", "POST", partial);
    }

    async function refreshIndexButton() {
      if (!indexBtn) {
        return;
      }
      if (!currentToken) {
        indexBtn.disabled = false;
        indexBtn.title = "Index";
        return;
      }
      try {
        const status = await getIndexStatus();
        const upToDate = Boolean(status && status.overall_up_to_date);
        indexBtn.disabled = upToDate;
        indexBtn.title = upToDate ? "Index up-to-date" : "Index";
      } catch (error) {
        indexBtn.disabled = false;
        indexBtn.title = "Index";
      }
    }

    async function indexDrive(logFn) {
      if (!currentToken) {
        logFn("Drive index skipped (token required).");
        return null;
      }
      let streamId;
      try {
        const opened = await apiJson("/catalog/open", "POST", {
          source: "google_drive",
          scope: "allDrives",
          options: { recursive: true, page_size: 500, fingerprint: false },
        });
        streamId = opened ? opened.stream_id : null;
        if (!streamId) {
          logFn("Drive index failed.");
          return null;
        }
        let total = 0;
        try {
          for (;;) {
            const page = await apiJson("/catalog/next", "POST", {
              stream_id: streamId,
              max_items: 500,
              time_budget_ms: 600,
            });
            const items = Array.isArray(page.items) ? page.items : [];
            total += items.length;
            if (page.done) {
              logFn(`Drive indexed ${total} items.`);
              return total;
            }
            await new Promise((resolve) => setTimeout(resolve, 60));
          }
        } finally {
          if (streamId) {
            await apiJson("/catalog/close", "POST", { stream_id: streamId }).catch(() => {});
          }
        }
      } catch (error) {
        logFn("Drive index failed.");
      }
      return null;
    }

    async function indexLocal(logFn) {
      if (!currentToken) {
        logFn("Local index skipped (token required).");
        return null;
      }
      let streamId;
      try {
        const opened = await apiJson("/catalog/open", "POST", {
          source: "local_fs",
          scope: "local_roots",
          options: { recursive: true, page_size: 500, fingerprint: false },
        });
        streamId = opened ? opened.stream_id : null;
        if (!streamId) {
          logFn("Local index failed.");
          return null;
        }
        let total = 0;
        try {
          for (;;) {
            const page = await apiJson("/catalog/next", "POST", {
              stream_id: streamId,
              max_items: 500,
              time_budget_ms: 600,
            });
            const items = Array.isArray(page.items) ? page.items : [];
            total += items.length;
            if (page.done) {
              logFn(`Local indexed ${total} items.`);
              return total;
            }
            await new Promise((resolve) => setTimeout(resolve, 60));
          }
        } finally {
          if (streamId) {
            await apiJson("/catalog/close", "POST", { stream_id: streamId }).catch(() => {});
          }
        }
      } catch (error) {
        logFn("Local index failed.");
      }
      return null;
    }

    const reloadOutputs = async () => {
      await loadCurrent();
      await refreshIndexButton();
    };

    async function loadCurrent() {
      const entry = current();
      if (!entry) {
        return;
      }
      if (!currentToken) {
        currentItems = [];
        setListMessage("Token required.");
        return;
      }
      try {
        const children = await loadChildren(entry.source, entry.parent_id);
        currentItems = children;
        draw();
      } catch (error) {
        currentItems = [];
        if (error && error.code === "plugin_disabled") {
          setListMessage("Plugin disabled.");
        } else {
          setListMessage("Failed to load items.");
        }
      }
    }

    backBtn.onclick = async () => {
      if (stack.length <= 1) {
        return;
      }
      stack.pop();
      updateBreadcrumb();
      await loadCurrent();
      refreshIndexButton().catch(() => {});
    };

    refreshBtn.onclick = () => {
      reloadOutputs();
    };

    indexBtn.onclick = async () => {
      if (!currentToken) {
        log("Index requires a session token.");
        return;
      }
      const logFn = (message) => {
        log(message);
      };
      indexBtn.disabled = true;
      indexBtn.title = "Index";
      logFn("Index → starting …");
      await Promise.all([indexDrive(logFn), indexLocal(logFn)]);
      let status = null;
      try {
        status = await getIndexStatus();
      } catch (error) {
        status = null;
      }
      if (status) {
        const payload = {};
        if (status.drive && status.drive.current_token) {
          payload.drive = {
            token: status.drive.current_token,
            last_indexed_at: Date.now(),
          };
        }
        if (status.local && status.local.current_sig) {
          payload.local = {
            roots_sig: status.local.current_sig,
            last_indexed_at: Date.now(),
          };
        }
        if (Object.keys(payload).length) {
          await updateIndexState(payload).catch(() => {});
        }
        const upToDate = Boolean(status.overall_up_to_date);
        indexBtn.disabled = upToDate;
        indexBtn.title = upToDate ? "Index up-to-date" : "Index";
        logFn(`Done. Up-to-date = ${upToDate}.`);
      } else {
        indexBtn.disabled = false;
        indexBtn.title = "Index";
        logFn("Done.");
      }
    };

    srcSel.onchange = async () => {
      stack.length = 0;
      stack.push(rootFor(srcSel.value));
      updateBreadcrumb();
      await loadCurrent();
      refreshIndexButton().catch(() => {});
    };

    stack.push(rootFor(srcSel.value));
    updateBreadcrumb();
    reloadOutputs();

    outputsRefresh = reloadOutputs;
  }

  function refreshAll() {
    healthRefresh();
    capsRefresh();
    pluginsRefresh();
    logsRefresh();
    outputsRefresh();
    settingsLocalRefresh().catch(() => {});
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadToken();

    if (saveTokenBtn) {
      saveTokenBtn.addEventListener("click", saveToken);
    }

    if (refreshAllBtn) {
      refreshAllBtn.addEventListener("click", refreshAll);
    }

    if (tabDashboardBtn) {
      tabDashboardBtn.addEventListener("click", () => showTab("dashboard"));
    }
    if (tabSettingsBtn) {
      tabSettingsBtn.addEventListener("click", () => showTab("settings"));
    }

    healthInit();
    capsInit();
    pluginsInit();
    logsInit();
    outputsInit();
    settingsLocalInit().catch(() => {});

    if (currentToken) {
      refreshAll();
    }
  });
})();
