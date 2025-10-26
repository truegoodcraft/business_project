jsexport function mountWrites(container) {
  container.innerHTML = `
    <div>
      <p>Writes: <span id="writes-status">loading...</span></p>
      <button onclick="window.toggleWrites()">Toggle</button>
    </div>
  `;
  updateWrites();
}

async function updateWrites() {
  try {
    const { enabled } = await fetch("/dev/writes", {
      headers: { "X-Session-Token": TOKEN || "" }
    }).then(r => r.json());
    document.getElementById("writes-status").textContent = enabled ? "ON" : "OFF";
  } catch (e) {
    document.getElementById("writes-status").textContent = "ERROR";
  }
}

window.toggleWrites = async () => {
  const { enabled } = await fetch("/dev/writes", {
    headers: { "X-Session-Token": TOKEN || "" }
  }).then(r => r.json());
  await fetch("/dev/writes", {
    method: "POST",
    headers: { 
      "X-Session-Token": TOKEN || "",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ enabled: !enabled })
  });
  location.reload();
};
