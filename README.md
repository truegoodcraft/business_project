<div align="center">

# 🤖 TGC Systems — True Good Craft Controller  
### _Universal AI-Driven Business Controller for Makers, Builders & Brave Souls_

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

The **TGC Systems Controller** is a universal, modular, **AI-assisted business automation platform** for creative workshops and small businesses.  
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
git clone https://github.com/truegoodcraft/business_project.git
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

| Command   | Action                                           |
|-----------|--------------------------------------------------|
| `update`  | Pull latest GitHub changes (dry-run first).      |
| `discover`| Rebuild indexes and verify structure.            |
| `gmail`   | Import vendor quotes/orders.                     |
| `csv`     | Import inventory data.                           |
| `sheets`  | Sync metrics with Google Sheets.                 |
| `drive`   | Link Drive files by SKU/reference.               |
| `contacts`| Normalize vendor contacts.                       |
| `settings`| Manage configuration & credentials.              |

🧭 **Author**  
TGC Systems  
🎩 Maker. Tinkerer. Possibly the entity that accidentally builds Skynet.  
🔗 https://github.com/truegoodcraft

🪙 **License & Contribution**  
Licensed under the MIT License.  
Contributions, bug reports, and survival tips welcome.

🧵 **Final Thoughts**  
This project is equal parts workshop tool and AI playground.  
It’s meant to be explored, broken, rebuilt, and improved — safely, curiously, and without fear of failure.

✨ If it works, awesome. If it explodes, we’ll fix it together.  
🧠 May your logs be clean and your GPTs merciful.

If you found this project useful or entertaining, consider fueling the chaos with a coffee ☕  
[**paypal.me/truegoodcraft**](https://paypal.me/truegoodcraft)

“**If it ain’t broke, don’t fix it… or was it ‘If it ain’t fixed, don’t broke it?’**”  
“**If it’s stupid but it works, it’s not stupid.**”  
**MTFY**

</div>

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
