# TGC BUS Core (Business Utility System Core)

**Owner:** True Good Craft  
**License:** GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)

## What is this?

TGC BUS Core (“BUS” = **Business Utility System**) is a local-first operations core for tiny shops, makers, and small businesses.

- Single-machine, offline-capable
- No telemetry
- SQLite + journals, not a cloud SaaS
- Designed to be extended with plugins (including future PRO plugins)

Right now this is an **alpha** aimed at developers and power users, not yet a polished end-user product.

## Status

- **Backend:** Working alpha
  - Items, vendors, tasks
  - Transactions (money in/out)
  - RFQ generator
  - Inventory runs with journaling
  - Encrypted export/import
- **UI:** Rough / work-in-progress
  - Home dashboard  (donuts + last 10)
  - Inventory & vendors screens
  - Settings (writes toggle, business profile)
- **Not ready** for general non-technical users yet.

## Core principles

- Local-first, offline-capable
- No telemetry, no phone-home
- No forced cloud service
- Data is exportable and migratable (no lock-in)
- Clear separation between:
  - **Free core** (AGPL)
  - **Optional PRO plugins** (separate commercial license)

## Getting started (dev)

Prereqs:

- Python 3.11+
- Git
- Windows (v1 focus; other platforms later)

Clone and set up:

```bash
git clone <YOUR_REPO_URL> tgc-bus-core
cd tgc-bus-core

python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

Run the backend (adjust entrypoint if different):

```bash
python app.py
```

Then open the UI in your browser (adjust path if needed):

```text
http://localhost:8000/ui/shell.html
```

## Project structure (high level)

* `core/` – backend application (FastAPI, domain logic, RFQ, inventory, export/import, etc.)
* `core/ui/` – front-end (HTML/JS/CSS, cards, dashboard)
* `launcher/` – helper scripts / launchers
* `docs/`

  * `SOT.md` – Source of Truth (design, rules, constraints)
  * `ARCHITECTURE.md` – architecture overview
  * `ROADMAP.md` – versioned roadmap and scope

## Contributing

Right now, help is especially welcome on:

* UI cleanup and consistency (Home, Inventory, Vendors, RFQ, Settings)
* User flows and error handling
* Tests for key backend flows

Basic expectations:

* Respect the local-first, no-telemetry constraints.
* Don’t introduce background schedulers / hidden network calls.
* Keep changes small and focused; open issues/PRs for discussion.

## License

The core of this project is licensed under the **GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)**.

See the `LICENSE` file for full details.

Optional PRO plugins and commercial add-ons may be offered under a separate license by True Good Craft.
