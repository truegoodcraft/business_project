(function () {
  const TOKEN_STORAGE_KEY = "tgc_token";
  const panels = {};
  let currentToken = "";
  let googleRowInitialized = false;

  const tokenInput = document.getElementById("token-input");
  const saveTokenBtn = document.getElementById("save-token");
  const refreshAllBtn = document.getElementById("refresh-all");
  const tokenBanner = document.getElementById("token-banner");
  const logsAutoscroll = document.getElementById("logs-autoscroll");
  const probeServices = document.getElementById("probe-services");
  const runProbeBtn = document.getElementById("run-probe");

  document.querySelectorAll(".panel").forEach((section) => {
    const panelName = section.dataset.panel;
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
      renderGdUI(false);
    }
  }

  function hasToken() {
    return Boolean(currentToken);
  }

  function tokenHeader() {
    if (!currentToken) {
      throw new Error("Session token required");
    }
    return { "X-Session-Token": currentToken };
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
  }

  async function gdStatus() {
    const headers = tokenHeader();
    const response = await fetch(`/oauth/google/status`, { headers });
    if (!response.ok) {
      throw new Error("status failed");
    }
    return response.json();
  }

  async function gdStart() {
    const headers = { ...tokenHeader(), "Content-Type": "application/json" };
    const redirect = `${window.location.origin}/oauth/google/callback`;
    const response = await fetch(`/oauth/google/start`, {
      method: "POST",
      headers,
      body: JSON.stringify({ redirect }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.auth_url) {
      throw new Error(payload.error || "auth failed");
    }
    window.open(payload.auth_url, "_blank");
  }

  async function gdRevoke() {
    const headers = tokenHeader();
    const response = await fetch(`/oauth/google/revoke`, {
      method: "POST",
      headers,
    });
    if (!response.ok) {
      throw new Error("revoke failed");
    }
  }

  function renderGdUI(connected) {
    const statusEl = document.getElementById("google-status");
    const connectBtn = document.getElementById("google-connect");
    const disconnectBtn = document.getElementById("google-disconnect");
    const checkEl = document.getElementById("google-check");
    if (!statusEl || !connectBtn || !disconnectBtn || !checkEl) {
      return;
    }
    if (connected) {
      statusEl.textContent = "Connected";
      statusEl.classList.add("ok");
      connectBtn.style.display = "none";
      disconnectBtn.style.display = "inline-block";
      checkEl.style.display = "inline-block";
    } else {
      statusEl.textContent = "Not connected";
      statusEl.classList.remove("ok");
      connectBtn.style.display = "inline-block";
      disconnectBtn.style.display = "none";
      checkEl.style.display = "none";
    }
  }

  async function initGoogleRow() {
    const connectBtn = document.getElementById("google-connect");
    const disconnectBtn = document.getElementById("google-disconnect");
    if (!connectBtn || !disconnectBtn) {
      return;
    }

    if (!googleRowInitialized) {
      connectBtn.onclick = async () => {
        try {
          await gdStart();
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          window.alert(message);
        }
      };
      disconnectBtn.onclick = async () => {
        try {
          await gdRevoke();
          renderGdUI(false);
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          window.alert(message);
        }
      };
      googleRowInitialized = true;
    }

    if (!hasToken()) {
      renderGdUI(false);
      return;
    }

    try {
      const status = await gdStatus();
      renderGdUI(Boolean(status?.connected));
    } catch (error) {
      renderGdUI(false);
    }
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
      renderGdUI(false);
    }
  });
})();
