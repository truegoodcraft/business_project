<div align="center">

# 🤖 TGC Frame
### _Owner-core controller with open plugins_
**made by TGC Systems**

---

> 🧠 *An experiment in automation, curiosity, and accidental intelligence.*
> *Built by TGC Systems — powered by GPT-fu, caffeine, and a healthy dose of luck.*

---

## ⚠️ Disclaimer (Read This First!)

This project is **AI-based** and **experimental**. It blends automation, GPT logic, and modular systems in unpredictable ways.  
While it’s designed for safety and transparency, it may occasionally act in **unexpected or unintended ways**.

By using or modifying this code, you acknowledge and agree:

🧩 **Not production-ready software.**  
💥 **TGC Systems accepts no liability** for data loss, file modification, unintentional automation, or emergent AI behavior.  
🤷‍♂️ The developer has **no formal idea what they’re doing** — this is part art project, part experiment, part chaos magic.  
🕹️ If it ever becomes self-aware, please unplug it, pour it a coffee, and tell it we tried our best.  
☠️ *There’s a non-zero chance we’re accidentally building Skynet.*

Proceed with curiosity. ⚙️ Tinker responsibly. 🧤

---

## 🚀 Overview

**TGC Frame** is a universal, modular, **AI-assisted business automation platform** for creative workshops and small businesses.
It unifies **Notion**, **Google Drive**, **Google Sheets**, and more — under one local-first control system.

It’s for curious makers who want a smart assistant that helps manage their workflow… not run it.

> 🪶 “I’m not a developer. I’m just weaving GPT-fu and luck into something useful.” — *TGC Systems*

---

## 🧭 System Flow (Simplified)

👤 User  
↓  
🧠 ChatGPT / AI Layer ←→ 🤖 Controller Core (Python)  
↓  
📚 Notion 🗂️ Google Drive 📊 Google Sheets 📧 Gmail

> The AI layer interprets intent → the Controller executes → the logs tell the story.

---

## 🧩 Core Features

🧠 **AI-assisted logic** — actions & parsing guided by GPT context.  
🧩 **Single modular controller** for all integrations.  
🧾 **Traceable runs** with timestamped `plan.md / changes.md / errors.md`.  
🧱 **Beginner-friendly** defaults: dry-runs, masked secrets, clear prompts.  
💬 **ChatGPT-first interface** — use ChatGPT or CLI.  
🪄 **Auto-update** from GitHub without restarting.  
🧭 **Organization tracking** for consistent branding and SKUs.  
🔐 **Safe credential handling** — locally stored and verified.

---

## 🧩 Planned Features

<details>
<summary>🌐 Setup & Structure</summary>

One-click setup for **Google**, **Notion**, or **Sheets**.  
Choose size: **Small**, **Medium**, or **Thorough** — easily upgradable.  
Auto-builds indexes, folders, and templates.  
All changes backed up as zip archives (10-day retention).

</details>

<details>
<summary>🗂️ Data & Storage</summary>

**Non-destructive sync** between local and cloud.  
Auto-indexing for Notion pages, Drive files, and Sheets.  
**Local or hybrid cloud operation** — your choice.  
Smart rollback and recovery.

</details>

<details>
<summary>💬 Smart Assistant</summary>

Accepts **receipts, screenshots, PDFs, bank statements**.  
Parses and **suggests updates** (vendors, prices, contacts).  
Learns usage patterns for smarter workflow.

</details>

<details>
<summary>🔒 Backup & Recovery</summary>

Archives every change for 10 days.  
Optional auto-archive for logs.  
One-click restore for lost or overwritten data.

</details>

<details>
<summary>⚙️ User Experience</summary>

Clean CLI + ChatGPT menu.  
Toggle modules on/off anytime.  
Guided onboarding with tooltips.  
Fully reversible — **idiot-proof by design.**

</details>

<details>
<summary>📊 Analytics (Optional)</summary>

Anonymous, privacy-safe metrics only.  
Tracks inventory trends & usage.  
All outbound data previewed before sending.

</details>

<details>
<summary>💡 Future Plans</summary>

Role-based access (Admin / Manager / Employee).  
Plugin framework for custom extensions.  
Hybrid deployment (desktop + web dashboard).  
Low-cost subscription model ($1–$2 / month).

</details>

---

## 🛠️ Tech Stack

🐍 **Python 3.12+**  
⚙️ **Flask**, **Notion SDK**, **Google API Client**  
💾 **JSON / SQLite** local data, optional **Google Sheets** backend  
💬 **CLI + ChatGPT** dual interface

---

## 📁 Project Structure

```
/tgc_bridge_bootstrap/
│
├── tgc/
│   ├── adapters/           # Modular integrations (Notion live, others stubbed)
│   ├── actions/            # Menu commands (plan → dry-run → apply → report)
│   ├── config/             # Environment & connections
│   ├── controller.py       # Core engine
│   ├── bootstrap.py        # Builds controller & registers adapters
│   ├── organization.py     # Brand & SKU setup
│   ├── reporting.py        # Logs and audit helpers
│   └── app.py              # CLI entry point
│
├── docs/
│   ├── chatgpt_startup_prompt.md
│   ├── organization_reference.md
│   └── feature_roadmap.md
│
├── reports/
├── requirements.txt
└── .env
```

---

## ⚙️ Getting Started

### Clone

```bash
git clone https://github.com/tgc-systems/business_project.git
cd business_project
```

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Initialize

```bash
python app.py --init-org
```

Enter business name, SKU prefix, and contact info.  
Generates `/docs/organization_reference.md`.

### Run

```bash
python app.py
```

### Check Status

```bash
python app.py --status
```

## Startup & Plugins Hub

At launch, TGC Frame prints a readiness banner:

```
TGC Frame — Ready: <True/False> • Plugins OK: <X/Y> • SafeMode: <ON/OFF> • Subprocess: <ON/OFF>
APIs: Notion=<READY/MISSING> • Drive=<READY/MISSING> • Sheets=<READY/MISSING>
```

Open **Plugins Hub** to:
- Discover installed plugins and view health
- Auto-connect (checks required env keys; shows what’s missing)
- Test a plugin (health check)
- Configure (see env schema and secret file locations)
- Enable/Disable plugins
- Debug broken connections (batch health hints)

Secrets are not captured in the CLI. Set them via:
- `.env` (global), or
- `plugins/<plugin>/plugin.secrets.local.env` (gitignored)

## 🧮 CLI Layout

The interactive CLI now shows a normalized banner and grouped menu. Behavior is unchanged; the same keys trigger the same actions.

```
TGC Frame — Controller Menu
made by: TGC Systems
tagline: Owner-core controller with open plugins

Core
  0   System Check — Validate credentials and status
  1   Discover & Audit — Read-only adapter audit
  U   Update from repository — Fetch and merge latest code

Build
  12  Build Master Index — Notion, Drive, (Sheets) → Markdown
  13  Master Index Snapshot (debug) — Print JSON for inspection
  14  Build Sheets Index — Enumerate spreadsheets & tabs

Imports & Sync
  2   Import from Gmail — Stage vendor quotes/orders (optional)
  3   Import CSV → Inventory — Map CSV columns
  4   Sync metrics → Google Sheets — Preview/push

Linking & Data
  5   Link Drive PDFs to Notion — Match and attach
  6   Contacts & Vendors — Normalize & dedupe

Config & Reports
  7   Settings & IDs — View environment and saved queries
  8   Logs & Reports — List recent run directories
  10  Google Drive Module — Configure sharing & validation
  11  Notion Module — Review access & troubleshooting
  15  Plugin Consents — Grant or revoke scopes
  17  Retention Cleanup — Preview or prune historical runs

Optional
  9   Wave — Discover Wave data and plan exports

Exit
  q   Quit
```

### 🔐 Plugin configuration

Each integration plugin now declares the environment variables it needs in
`plugins/<name>/config.schema.json`. To configure credentials locally:

1. Copy the checked-in `plugin.secrets.example.env` file to
   `plugin.secrets.local.env` within the same plugin directory.
2. Provide values only for the keys listed in the corresponding
   `config.schema.json` file.

The local secrets files are gitignored so that credentials stay on your
machine, while the schema keeps the whitelist of supported variables obvious.

### Notion setup

Create a **Sources** database in Notion to catalog linked systems alongside the inventory tracker. Configure these lean properties:

- **Name** — Title property for each source record.
- **Type** — Select property with options `Drive`, `Sheets`, `Notion`.
- **Key** — Rich text property for canonical IDs such as `drive:<fileId>`, `sheets:<spreadsheetId>#<sheetId>`, or `notion:<dbId>`.
- **Title** — Rich text property capturing the human-readable name.
- **URL** — URL property linking directly to the source document or database.
- **Path** — Rich text property for a concise parent path (for example, a Drive folder path).
- **Status** — Select property with options `Ready`, `Missing`, `Error`.
- **Last Indexed** — Date property noting the most recent sync or audit.
- **Extra** — Rich text property for short, optional notes.

Add the new database ID to your `.env` file:

```bash
NOTION_DB_SOURCES_ID=your_sources_database_id
```

### 💬 Command Palette

| Command    | Action                                                |
|------------|-------------------------------------------------------|
| `update`   | Fetch and merge latest code (dry-run first).           |
| `discover` | Read-only adapter audit.                               |
| `gmail`    | Stage vendor quotes/orders (optional).                 |
| `csv`      | Map CSV columns into inventory.                        |
| `sheets`   | Preview/push metrics to Google Sheets.                 |
| `drive`    | Match and attach Drive PDFs to inventory.              |
| `contacts` | Normalize & dedupe contact records.                    |
| `settings` | View environment and saved queries.                    |
| `logs`     | List recent run directories.                           |
| `wave`     | Discover Wave data and plan exports.                   |
| `drive-mod`| Configure Google Drive module sharing & validation.    |
| `notion`   | Review Notion module access & troubleshooting prompts. |

🧭 **Author**  
TGC Systems  
🎩 Maker. Tinkerer. Possibly the entity that accidentally builds Skynet.  
🔗 https://github.com/tgc-systems

🪙 **License & Contribution**  
Licensed under the MIT License.  
Contributions, bug reports, and survival tips welcome.

🧵 **Final Thoughts**  
This project is equal parts workshop tool and AI playground.  
It’s meant to be explored, broken, rebuilt, and improved — safely, curiously, and without fear of failure.

✨ If it works, awesome. If it explodes, we’ll fix it together.  
🧠 May your logs be clean and your GPTs merciful.

If you found this project useful or entertaining, consider fueling the chaos with a coffee ☕  
[**paypal.me/tgcsystems**](https://paypal.me/tgcsystems)

“**If it ain’t broke, don’t fix it… or was it ‘If it ain’t fixed, don’t broke it?’**”  
“**If it’s stupid but it works, it’s not stupid.**”  
**MTFY**

</div>

## Security

Plugin signatures (Ed25519) are verified when PyNaCl is installed.
Install with: `python -m pip install "pynacl>=1.5,<2"`
Without PyNaCl, TGC Frame will skip signature verification and log a warning.

## Transparency & Architecture

The Core controller is owned and kept private to protect integrity and user data. All integrations are plugins that declare:
- what they can access (scopes),
- what they can do (capabilities),
- and whether they require network access.

Nothing runs unless scopes are explicitly granted, and every run is audited to `reports/audit.log`. Secrets are not logged. You can enable:

- **SAFE MODE**: `OFFLINE_SAFE_MODE=true` blocks networked capabilities.
- **Subprocess Isolation**: `PLUGIN_SUBPROCESS=true` runs plugins in a separate process with a whitelisted environment and an enforced timeout (`PLUGIN_TIMEOUT_S`, default 60s).

## Prompt Firewall (Placeholder)

This repo includes a **non-enforcing** Prompt Firewall scaffold:

- Policy files (versioned): `registry/policy.rules.yaml`, `registry/commands.allowlist.json`, `registry/denylist.json`
- Evaluator: `core/policy_engine.py` (currently **always ALLOW**)
- Logging: `reports/policy.log` records inputs (hashed) and decisions
- Environment switch: `POLICY_PLACEHOLDER_ENABLED=true` (default). This only logs; it does **not** block or change behavior.

### Why now?
We want a stable surface to iterate safety rules while we build features. Once rules are ready, we will enable enforcement behind a separate flag and CI checks.

### Roadmap
- Add schema validation per command
- Denylist + compatibility gate integration
- Optional enforcement mode
- Red-team tests in CI

## Retention (keep last N runs)

The controller can prune old runs to keep the repo tidy.

- Env:
  - `LOG_RETENTION_RUNS=20` (default)
  - `RETENTION_ENABLE=true` (default)
  - `UNIFIED_MAX_LINES=25000` (truncate long logs)
- Menu: “Prune old runs (keep last N)” supports a preview (dry-run).
- Auto-prune: after successful apply, if `RETENTION_ENABLE=true`.

Unified events are written to `reports/all.log` with types:
`retention.scan` • `retention.prune` • `retention.truncate` • `retention.summary` • `retention.error`

## CLI Layout (normalized)

Banner:
TGC Frame — Controller Menu
made by: TGC Systems

Sample menu:
Core
  0)  System Check — Validate credentials and status
  0U) Update from repository — Fetch and merge latest code
  1)  Discover & Audit — Read-only adapter audit

Build
  12) Build Master Index — Notion, Drive, (Sheets) → Markdown
  15) Build Sheets Index — Enumerate spreadsheets & tabs

Imports & Sync
  2)  Import from Gmail — Stage vendor quotes/orders
  3)  Import CSV → Inventory — Map CSV columns
  4)  Sync metrics → Google Sheets — Preview/push

Linking & Data
  5)  Link Drive PDFs to Notion — Match and attach
  6)  Contacts/Vendors — Normalize & dedupe

Config & Reports
  7)  Settings & IDs — View environment and saved queries
  8)  Logs & Reports — List recent run directories

Optional
  9)  Wave — Discover Wave data and plan exports

Exit
  q)  Quit
