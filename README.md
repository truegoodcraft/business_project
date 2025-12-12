# TGC BUS Core (Beta)

![License](https://img.shields.io/badge/License-AGPLv3-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-blue.svg)
![Status](https://img.shields.io/badge/Status-Beta-orange.svg)

**The local-first ERP for makers. Inventory, Manufacturing, and Contacts—no cloud required.**

BUS Core is a free, open-source business utility system designed for small workshops and makers. It runs entirely on your local machine, giving you ownership of your data without subscriptions or cloud dependencies.

## Key Features

* **Zero-License:** Completely free and open source (AGPLv3). No tiers, no "Pro" upselling, no locked features.
* **Precision Inventory:** Integer-based metric tracking (mg, mm, ml, count) with strict FIFO valuation and batch management.
* **Manufacturing:** Recipe-based production runs with automatic cost rollups, shortage detection, and atomic stock commits.
* **Ledger & Logs:** Full history of stock movements, including specific tracking for sales, loss, and theft.
* **Local & Private:** Powered by a local SQLite database. Includes AES-GCM encrypted backups.

## Getting Started

### Prerequisites
* Python 3.10+
* Windows (Primary support), Linux, or macOS

### Installation

1.  Clone the repository.
2.  Run the launcher:
    ```powershell
    scripts/launch.ps1
    # Or: python launcher.py
    ```

**Note for Windows Users:** The application runs in the **System Tray**. If the browser does not open automatically, or if you close the window, double-click the tray icon to access the dashboard.

*(If Windows blocks the script, run: `PowerShell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\launch.ps1"`)*

## Dev Mode

For developers contributing to the core:

```bash
python launcher.py --dev
````

  * **Console Access:** Keeps the terminal window open (hidden by default in production).
  * **Debug Endpoints:** Enables access to protected `/dev` API routes.
  * **Smoke Tests:** Validate system integrity using `scripts/smoke.ps1`.

## Architecture

See [docs/SOT.md](https://www.google.com/search?q=docs/SOT.md) for the Source of Truth and architecture details.

```
