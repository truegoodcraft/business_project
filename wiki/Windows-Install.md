# Windows Install

The packaged Windows app is the primary local install path.

## Install and Open

1. Download the current `BUS-Core-<version>.zip` from the project's official release page.
2. Read the matching release notes.
3. Extract the ZIP to a normal local folder. Do not run the executable from inside the ZIP.
4. Run the included versioned BUS Core executable.
5. BUS Core starts its local service and opens the browser UI at the local address, normally `http://127.0.0.1:8765`.

The release ZIP contains the versioned executable, README, and license material. The packaged app does not require a separate Python installation.

## First Launch

Choose demo mode to explore sample data or **Start Fresh** for a real-shop database. Demo and production databases are separate. Follow [Getting Started](Getting-Started.md) before entering a full catalog.

## Local Files

BUS Core stores the production database, demo database, configuration, journals, logs, exports, and update state beneath `%LOCALAPPDATA%\BUSCore`. The production database is `%LOCALAPPDATA%\BUSCore\app\app.db`; encrypted exports are under `%LOCALAPPDATA%\BUSCore\exports`.

Do not move or edit the live database by hand. Use **Settings > Administration > Backup Export** and the preview/commit restore workflow.

## Startup Problems

- Confirm the ZIP was fully extracted.
- Avoid launching a second copy while one is already running.
- Check whether `http://127.0.0.1:8765` opens locally.
- Keep the app local; do not publish this port to a LAN or the internet as a troubleshooting shortcut.
- Report the version, Windows version, exact message, and install folder through [Bug Reports](Bug-Reports.md).

Next: [First Shop Workflow](First-Shop-Workflow.md).
