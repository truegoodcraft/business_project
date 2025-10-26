// ESM entry: mounts cards and header, with basic error handling.
import { ensureToken, apiGet, apiPost } from "/ui/js/token.js";
import { mountWrites } from "/ui/js/cards/writes.js";
import { mountOrganizer } from "/ui/js/cards/organizer.js";
import { mountDev } from "/ui/js/cards/dev.js";

async function boot() {
  try {
    await ensureToken(); // primes token + header injection
    const app = document.getElementById("app");
    if (!app) throw new Error("app container missing");

    // Header init: license + writes
    const license = await apiGet("/dev/license");
    const writes = await apiGet("/dev/writes");

    const licBadge = document.getElementById("license-badge");
    const wrBadge = document.getElementById("writes-badge");
    const toggleBtn = document.getElementById("writes-toggle");

    function renderHdr(state) {
      if (licBadge) licBadge.textContent = `License: ${license?.tier ?? "free"}`;
      if (wrBadge) wrBadge.textContent = `Writes: ${state?.enabled ? "ON" : "OFF"}`;
    }
    renderHdr(writes);

    if (toggleBtn) {
      toggleBtn.onclick = async () => {
        try {
          const next = await apiPost("/dev/writes", { enabled: !writes.enabled });
          writes.enabled = next.enabled;
          renderHdr(writes);
        } catch (e) {
          console.error("toggle failed", e);
          alert("Failed to toggle writes");
        }
      };
    }

    // Minimal mount: show Writes card by default
    mountWrites(app, { license, writes });

    // Expose mounts if a simple hash router is later desired
    window.bus = Object.freeze({
      mountWrites: () => mountWrites(app, { license, writes }),
      mountOrganizer: () => mountOrganizer(app),
      mountDev: () => mountDev(app),
    });

    console.log("BOOT OK");
  } catch (err) {
    console.error("boot error", err);
    const app = document.getElementById("app");
    if (app) app.innerHTML = `<pre>UI failed to boot: ${String(err)}</pre>`;
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
