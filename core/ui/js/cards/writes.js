export function mountWrites(container, ctx = {}) {
  container.innerHTML = `
    <section>
      <h2>Writes Control</h2>
      <p>This card reflects and toggles write capability for the current session.</p>
      <ul>
        <li><strong>License:</strong> ${ctx.license?.tier ?? "free"}</li>
        <li><strong>Writes:</strong> ${ctx.writes?.enabled ? "ON" : "OFF"}</li>
      </ul>
      <p>Use the header "Toggle" button to flip writes.</p>
    </section>
  `;
}
