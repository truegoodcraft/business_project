(function () {
  const previewBtn = document.getElementById("btn-preview");
  const executeBtn = document.getElementById("btn-execute");
  const downloadBtn = document.getElementById("btn-download");
  const rollbackBtn = document.getElementById("btn-rollback");
  const planInput = document.getElementById("plan-json");
  const previewSummary = document.getElementById("preview-summary");
  const previewTable = document.getElementById("preview-table");
  const crossDriveNote = document.getElementById("cross-drive-note");
  const jobStatus = document.getElementById("job-status");
  const logEl = document.getElementById("log");

  const STORAGE_KEY = "tgc.organizer.plan";
  let lastPlan = [];
  let currentJobId = null;
  let pollTimer = null;

  function log(message) {
    if (!logEl) {
      return;
    }
    const now = new Date().toISOString();
    const line = `[${now}] ${message}`;
    logEl.textContent = `${line}\n${logEl.textContent || ""}`;
  }

  function fetchJson(path, options = {}) {
    const fetchImpl = window.tgcAuthenticatedFetch || window.fetch;
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const opts = Object.assign({}, options, { headers });
    return fetchImpl(path, opts).then(async (response) => {
      if (!response.ok) {
        const text = await response.text().catch(() => "");
        const error = new Error(`Request failed: ${response.status}`);
        error.status = response.status;
        error.body = text;
        throw error;
      }
      if (response.status === 204) {
        return {};
      }
      return response.json();
    });
  }

  function parsePlanInput() {
    if (!planInput) {
      return [];
    }
    const raw = planInput.value.trim();
    if (!raw) {
      return [];
    }
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed;
      }
      if (parsed && Array.isArray(parsed.batches)) {
        return parsed.batches;
      }
    } catch (error) {
      throw new Error("Plan JSON must be an array or {batches: []}");
    }
    throw new Error("Plan JSON must be an array or {batches: []}");
  }

  function savePlanToStorage(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch (error) {
      // ignore storage errors
    }
  }

  function loadPlanFromStorage() {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored && planInput) {
        planInput.value = stored;
      }
    } catch (error) {
      // ignore
    }
  }

  function renderPreview(result) {
    if (!result || !previewSummary || !previewTable) {
      return;
    }
    const summary = result.summary || {};
    previewSummary.textContent = `OK: ${summary.ok || 0} • Deny: ${summary.deny || 0} • Error: ${summary.error || 0}`;

    const batches = Array.isArray(result.batches) ? result.batches : [];
    const table = document.createElement("table");
    const head = document.createElement("thead");
    head.innerHTML = "<tr><th>Operation</th><th>Source</th><th>Target</th><th>Status</th><th>Reason</th></tr>";
    table.appendChild(head);
    const body = document.createElement("tbody");
    let crossDrive = false;
    batches.forEach((batch) => {
      const op = batch.op || "";
      const results = Array.isArray(batch.results) ? batch.results : [];
      results.forEach((item) => {
        const tr = document.createElement("tr");
        const itemData = item.item || {};
        const warnings = Array.isArray(item.warnings) ? item.warnings : [];
        if (warnings.includes("cross_drive_copy_quarantine")) {
          crossDrive = true;
        }
        tr.innerHTML = `
          <td>${op}</td>
          <td>${itemData.old_path || itemData.path || ""}</td>
          <td>${item.resolved_path || ""}</td>
          <td class="status-${String(item.status || "").toLowerCase()}">${item.status || ""}</td>
          <td>${item.reason || ""}</td>
        `;
        body.appendChild(tr);
      });
    });
    table.appendChild(body);
    previewTable.innerHTML = "";
    previewTable.appendChild(table);
    if (crossDrive && crossDriveNote) {
      crossDriveNote.style.display = "block";
      crossDriveNote.textContent = "Will copy to target and quarantine the original for cross-drive moves.";
    } else if (crossDriveNote) {
      crossDriveNote.style.display = "none";
      crossDriveNote.textContent = "";
    }
  }

  function hasBlockingIssues(result) {
    if (!result) {
      return true;
    }
    const summary = result.summary || {};
    return (summary.error || 0) > 0 || (summary.deny || 0) > 0;
  }

  function enableExecute(enabled) {
    if (executeBtn) {
      executeBtn.disabled = !enabled;
    }
  }

  function stopPolling() {
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function schedulePoll(jobId) {
    stopPolling();
    pollTimer = setTimeout(() => pollJob(jobId), 500);
  }

  function pollJob(jobId) {
    fetchJson(`/jobs/${jobId}`)
      .then((job) => {
        currentJobId = jobId;
        if (jobStatus) {
          const progress = job.progress || { done: 0, total: 0 };
          jobStatus.textContent = `Status: ${job.status} • ${progress.done}/${progress.total}`;
        }
        if (job.status === "running") {
          schedulePoll(jobId);
        } else {
          stopPolling();
          if (job.status === "done") {
            log(`Job ${jobId} finished.`);
            enableExecute(false);
            if (rollbackBtn) {
              rollbackBtn.style.display = "inline-block";
            }
          } else {
            log(`Job ${jobId} failed: ${(job.errors || []).join(", ")}`);
          }
        }
      })
      .catch((error) => {
        stopPolling();
        log(`Failed to poll job: ${error}`);
      });
  }

  function onPreview() {
    if (!planInput) {
      return;
    }
    try {
      const batches = parsePlanInput();
      savePlanToStorage(planInput.value);
      lastPlan = batches;
      if (!batches.length) {
      if (previewSummary) {
        previewSummary.textContent = "Provide at least one batch to preview.";
      }
      if (previewTable) {
        previewTable.innerHTML = "";
      }
        enableExecute(false);
        return;
      }
      log("Preview → submitting batches");
      fetchJson("/plan.preview", {
        method: "POST",
        body: JSON.stringify({ batches }),
      })
          .then((result) => {
            renderPreview(result);
          const ready = !hasBlockingIssues(result);
          enableExecute(ready);
          if (jobStatus) {
            jobStatus.textContent = ready
              ? "Preview succeeded. Ready to execute."
              : "Preview blocked. Resolve Deny/Error items.";
          }
          log("Preview → received response");
        })
        .catch((error) => {
          enableExecute(false);
          if (previewSummary) {
            previewSummary.textContent = "Preview failed.";
          }
          if (previewTable) {
            previewTable.innerHTML = "";
          }
          log(`Preview failed: ${error.body || error}`);
        });
    } catch (error) {
      enableExecute(false);
      if (previewSummary) {
        previewSummary.textContent = error.message;
      }
      if (previewTable) {
        previewTable.innerHTML = "";
      }
    }
  }

  function onExecute() {
    if (!lastPlan || !lastPlan.length) {
      return;
    }
    enableExecute(false);
    if (jobStatus) {
      jobStatus.textContent = "Submitting job…";
    }
    log("Execute → submitting batches");
    fetchJson("/plan.execute", {
      method: "POST",
      body: JSON.stringify({ batches: lastPlan }),
    })
      .then((result) => {
        if (result.accepted) {
          log(`Job ${result.job_id} accepted.`);
          schedulePoll(result.job_id);
        } else {
          log(`Job reused existing id ${result.job_id}.`);
          schedulePoll(result.job_id);
        }
      })
      .catch((error) => {
        log(`Execute failed: ${error.body || error}`);
        enableExecute(true);
      });
  }

  function onDownload() {
    if (!planInput) {
      return;
    }
    const blob = new Blob([planInput.value || "[]"], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `plan-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  if (previewBtn) {
    previewBtn.addEventListener("click", onPreview);
  }
  if (executeBtn) {
    executeBtn.addEventListener("click", onExecute);
  }
  if (downloadBtn) {
    downloadBtn.addEventListener("click", onDownload);
  }
  if (rollbackBtn) {
    rollbackBtn.addEventListener("click", () => {
      log("Rollback will be available in a future release.");
    });
  }
  if (planInput) {
    planInput.addEventListener("input", () => {
      savePlanToStorage(planInput.value);
    });
  }

  loadPlanFromStorage();
})();
