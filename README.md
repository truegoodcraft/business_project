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
💬 **CLI + ChatGPT dual interface**  

---

## 📁 Project Structure

/tgc_bridge_bootstrap/
│
├── tgc/
│ ├── adapters/ # Modular integrations (Notion live, others stubbed)
│ ├── actions/ # Menu commands (plan → dry-run → apply → report)
│ ├── config/ # Environment & connections
│ ├── controller.py # Core engine
│ ├── bootstrap.py # Builds controller & registers adapters
│ ├── organization.py # Brand & SKU setup
│ ├── reporting.py # Logs and audit helpers
│ └── app.py # CLI entry point
│
├── docs/
│ ├── chatgpt_startup_prompt.md
│ ├── organization_reference.md
│ └── feature_roadmap.md
│
├── reports/
├── requirements.txt
└── .env

yaml
Copy code

---

## ⚙️ Getting Started

Clone  
```bash
git clone https://github.com/truegoodcraft/business_project.git
cd business_project
Setup

bash
Copy code
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Initialize

bash
Copy code
python app.py --init-org
Enter business name, SKU prefix, and contact info.
Generates /docs/organization_reference.md.

Run

bash
Copy code
python app.py
Check Status

bash
Copy code
python app.py --status
💬 Command Palette
Command	Action
update	Pull latest GitHub changes (dry-run first).
discover	Rebuild indexes and verify structure.
gmail	Import vendor quotes/orders.
csv	Import inventory data.
sheets	Sync metrics with Google Sheets.
drive	Link Drive files by SKU/reference.
contacts	Normalize vendor contacts.
settings	Manage configuration & credentials.

🧭 Author
TGC Systems
🎩 Maker. Tinkerer. Possibly the entity that accidentally builds Skynet.
🔗 https://github.com/truegoodcraft

🪙 License & Contribution
Licensed under the MIT License.
Contributions, bug reports, and survival tips welcome.

🧵 Final Thoughts
This project is equal parts workshop tool and AI playground.
It’s meant to be explored, broken, rebuilt, and improved — safely, curiously, and without fear of failure.

✨ If it works, awesome. If it explodes, we’ll fix it together.
🧠 May your logs be clean and your GPTs merciful.

If you found this project useful or entertaining, consider fueling the chaos with a coffee ☕  
[**paypal.me/truegoodcraft**](https://paypal.me/truegoodcraft)

“If it ain’t broke, don’t fix it… or was it ‘If it ain’t fixed, don’t broke it?’”
“If it’s stupid but it works, it’s not stupid.”
MTFY

</div> ```
