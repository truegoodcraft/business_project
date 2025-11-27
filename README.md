
<p align="center">
  <img src="https://github.com/truegoodcraft/TGC-BUS-Core/raw/main/Glow-Hero.png" 
       alt="BUS Core logo" 
       width="96" height="96">



</p>




<p align="center">
  What’s new in v0.6.0
<p align="center">  
  Monolith fully purged → microkernel.
<p align="center">  
  External integrations are plugins.
<p align="center">  
  Fresh-machine boot path proven.
</p>


# BUS Core (v0.6.0 "Iron Core")

[![GitHub Repo stars](https://img.shields.io/github/stars/truegoodcraft/TGC-BUS-Core?style=social)](https://github.com/truegoodcraft/TGC-BUS-Core)
[![License](https://img.shields.io/github/license/truegoodcraft/TGC-BUS-Core)](LICENSE)
![Python](https://img.shields.io/badge/python-3.12-blue)

**BUS Core** is a local-first business core for small and micro shops — free forever, built slowly and deliberately by someone who actually runs a workshop.

I’m building it for my own workshop first: inventory, contacts, and simple manufacturing runs that live on my machine, not in someone else’s cloud. The core will always be free to run locally, with no telemetry, no tracking, and no subscription wall for basic day-to-day work.

## 🏗 Architecture: The "Iron Core"

As of **v0.6.0**, BUS Core uses a **Microkernel Architecture** ("Iron Core").
* **Lightweight Coordinator:** The Core is minimal. It handles auth, policy, journaling, and the database.
* **Plugins for Everything:** External integrations (Google Drive, Notion, etc.) are removed from the core and must be loaded as plugins.
* **Local-First Analytics:** All dashboard stats and insights are calculated from **local events** stored in your database. We do not send your data to the cloud to generate charts.

---

## 🚀 Quickstart (Windows PowerShell)

The system now uses a single unified launcher that handles environment setup, dependencies, and startup.

<p align="center">
  <img src="https://github.com/truegoodcraft/TGC-BUS-Core/raw/main/docs/demo-boot-fast-new-pc.gif" 
       alt="TGC-BUS-Core lightning-fast boot on a fresh PC" 
       width="800">
  <br>
  <em>Boot → ready in seconds on a clean Windows machine</em>
</p>

```powershell
git clone [https://github.com/truegoodcraft/TGC-BUS-Core.git](https://github.com/truegoodcraft/TGC-BUS-Core.git)
cd TGC-BUS-Core
...

```powershell
git clone [https://github.com/truegoodcraft/TGC-BUS-Core.git](https://github.com/truegoodcraft/TGC-BUS-Core.git)
cd TGC-BUS-Core

# One command to build venv, install deps, and launch:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch.ps1
````

The server will start at `http://127.0.0.1:8765`. The script automatically:

1.  Creates the `.venv` virtual environment if missing.
2.  Installs the **minimal runtime** (FastAPI, SQLite, Cryptography).
3.  Launches the server.

### Optional Integrations

To install heavy integration libraries (Google, Notion, ReportLab), run the launcher with the extras flag:

```powershell
$env:BUSCORE_EXTRAS="1"; .\scripts\launch.ps1
```

-----

## 📦 Features & Status (Public Alpha)

  - **Real, but early.** Expect rough edges.
  - **Side project.** Progress is steady, not frantic.
  - **Free forever.** No license key required for local core features.

### Current Surface

  * **Backend:** Microkernel (FastAPI + SQLite).
  * **Domain:** Items, vendors, transactions, manufacturing runs, RFQ generator.
  * **Security:** Local encrypted secrets, session token management, policy engine.
  * **UI:** Single-page shell (Home, Inventory, Contacts, Settings).

-----

## 🛠 Development

We enforce a strict **Source of Truth (SoT)** workflow. The `scripts/launch.ps1` script is the canonical entry point for both usage and development.

### Smoke Testing

To verify the build, run the smoke harness against a running instance:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
```

**Smoke Expectations:**

  * Public `GET /health` returns 200 `{"ok": true}`.
  * Protected `GET /health` (with token) returns 200 with `version`, `policy`, and `license`.
  * `GET /ui/shell.html` returns 200.

-----

## 📂 Project Structure

  * `core/` – The Microkernel application (FastAPI, domain logic, policy).
  * `core/ui/` – Front-end assets (HTML/JS/CSS).
  * `plugins/` – Directory for external capability providers.
  * `scripts/` – Lifecycle tools (`launch.ps1`, `purge_monolith.ps1`, `smoke.ps1`).
  * `docs/` – Architecture decision records and the Source of Truth.

-----

## Contributions, feedback, and pace

BUS Core is open for people to look at, fork, and contribute to — but it is still **my workshop’s core tool first**.

If you want to help:

  * **Brutal honesty is welcome.** If something is confusing, slow, or dumb, say so plainly.
  * **Pull requests are welcome.** Especially small, focused fixes and docs improvements.
  * **No entitlement.** I don’t owe anyone features or timelines. I’ll merge what fits the project and my own use first.

-----

## Monetization philosophy

The core of BUS Core will always be free to run locally with no tracking and no required online account.

If I ever charge money, it will be for **Pro automation and “power user” features** — the kind of things you only need once BUS Core is already in the middle of your daily work. If you never reach that point, you should never feel pushed to pay.

I don’t even plan to run Pro for myself until I actually need it. When I do, I’ll pay for it like everyone else.

-----

## Why I’m doing this

I got tired of running my life and my workshop through a pile of web dashboards and subscriptions that all assume I’m a SaaS customer first and a human second.

BUS Core exists for a simpler reason: I want a **local business core** I can trust to outlive any one tool, laptop, or trend — something I can install, point at a database in my own AppData, and keep using even if the original repo disappears.

This is a side project, but it is not a throwaway project. My wife and kids see the hours going into this. That matters to me. If I’m spending family time on it, it has to be something I’m willing to run my own shop on for years — not just a pretty demo.

-----

## License

The core of this project is licensed under the **GNU Affero General Public License v3.0**.

See the `LICENSE` file for full details.

*Optional PRO plugins and commercial add-ons may be offered under a separate license by True Good Craft.*
