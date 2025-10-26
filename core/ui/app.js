jsimport { getToken, apiGet, getLicense } from "/ui/js/token.js";
import { mountWrites } from "/ui/js/cards/writes.js";
import { mountOrganizer } from "/ui/js/cards/organizer.js";
import { mountDev } from "/ui/js/cards/dev.js";

document.addEventListener("DOMContentLoaded", async () => {
  try {
    await getToken();
    const lic = await getLicense();
    const writes = await apiGet("/dev/writes");
    mountWrites(document.getElementById("app"));
    console.log("BOOT OK | License:", lic.tier, "| Writes:", writes.enabled);
  } catch (e) {
    console.error("BOOT FAILED:", e);
  }
});
