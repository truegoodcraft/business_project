# BUS Core UI Notes

## Layout IDs

- `#license-badge` — Updated by `API.loadLicense()` and displays the active license tier.
- `#writes-toggle` — Header checkbox controlling `data-writes-enabled` on `<body>`.
- `#app-version` — Populated from `window.APP_VERSION` (fallback `v0.6`).
- `#main` — Primary card container swapped by `Cards.render()`.
- `#modal-root` — Overlay target used by `ui/modals.js`.

## Script responsibilities

- `ui/js/api.js` — REST wrapper providing caching for `/dev/license`, standard headers, and write/feature gating.
- `ui/js/app.js` — Bootstraps tabs, writes toggle, license badge, and card registry.
- `ui/js/ui/dom.js` — DOM utilities (`el`, `$`) plus `bindDisabledWithProGate()` helper.
- `ui/js/ui/modals.js` — Shared alert/confirm modals rendered into `#modal-root`.
- `ui/js/cards/*.js` — Individual card renderers responsible for their section of the dashboard.

## Adding a gated control

1. Create the button/input normally inside your card render function.
2. Call `bindDisabledWithProGate(element, '<feature_key>')` after the element is created.
3. Use `API.post`/`API.request` for the action so 403 responses surface through the shared modal.
4. If the control requires additional enablement beyond licensing (e.g., preview before commit), set a custom `data-` flag and re-disable the element when the flag is not satisfied.
