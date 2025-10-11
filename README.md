# Universal Business Controller

This repository implements the controller architecture described in the True Good Craft master project brief and makes it available for any organization to adopt. It provides a single startup command that loads configuration, assembles modular adapters, and exposes a menu-driven workflow for core business operations. (Created by True Good Craft, generalized for wider use.)

## Features

- **Single core controller** with modular adapters for Notion, Google Drive, Google Sheets, Gmail, and optional Wave.
- **Menu-driven actions** that follow the required plan → dry-run/apply → report flow.
- **ID-first, traceable runs** that create timestamped folders in `reports/` containing `plan.md`, `changes.md`, and `errors.md`.
- **Beginner-safe defaults** with configuration masking, preview-friendly dry runs, and clear notes on missing credentials.
- **ChatGPT-first interface** via the included startup prompt file, with a CLI fallback for local execution.
- **Organization reference tracking** so business name, short codes, and contact details are captured once and reused across the workflow. Placeholder values ship with the project so new operators can quickly rebrand it.
- **Connector status report** available via `python app.py --status` to quickly audit which adapters are implemented and configured.
- **In-session auto-update** command so you can pull new repository changes without restarting the conversation.

## Project Structure

```
app.py                 # CLI entrypoint (python app.py)
tgc/                   # Controller, adapters, and actions
  adapters/            # Modular integrations (Notion live read + safe stubs for others)
  actions/             # Menu commands with plan/dry-run/apply flow
  bootstrap.py         # Builds controller and registers actions
  config.py            # Loads .env and masks secrets
  controller.py        # Core orchestration engine
  menu.py              # CLI menu loop
  organization.py      # Organization profile helpers and setup prompts
  reporting.py         # Run context and report helpers
requirements.txt       # Python dependency list
docs/chatgpt_startup_prompt.md  # Prompt to operate the system via ChatGPT
docs/organization_reference.md  # Generated organization quick reference
```

Adapters are designed to run safely without credentials. The Notion adapter now supports live read-only access to the inventory vault, while the remaining adapters currently expose capability summaries and placeholder methods that can be upgraded to full API integrations.

## Getting Started

1. Create and populate a `.env` file following the template below. Missing values are allowed; unavailable adapters will be skipped automatically.

   ```env
   NOTION_TOKEN=
   NOTION_DB_INVENTORY_ID=
   SHEET_INVENTORY_ID=
   DRIVE_ROOT_FOLDER_ID=
   GMAIL_QUERY=from:(order OR invoice OR quote) newer_than:1y

   # Optional Wave support
   WAVE_GRAPHQL_TOKEN=
   WAVE_BUSINESS_ID=
   WAVE_SHEET_ID=
   ```

2. Configure your organization profile. This step removes placeholder branding and sets up SKU prefixes that follow the `[xxx]-001` format until a custom short code is provided.

   ```bash
   python app.py --init-org
   ```

   The command asks for the business name, contact information, and preferred short code (for example, `ABC` to produce IDs like `ABC-001`). Your answers populate `organization_profile.json` and refresh `docs/organization_reference.md` for quick reference during audits.

3. Install dependencies and launch the controller:

   ```bash
   pip install -r requirements.txt
   python app.py
   ```

4. Follow the prompts to select an action. Each action displays a plan, allows you to choose a dry run or apply mode, and writes reports under `reports/run_<ACTION>_<TIMESTAMP>/`.

5. (Optional) Print a connector functionality report without entering the menu:

   ```bash
   python app.py --status
   ```

   This command highlights whether each adapter is implemented, whether it is configured with credentials, and includes the current organization summary so you can confirm the environment before testing.

6. (Optional) Pull the latest repository changes from within the same session. Run a dry-run first to confirm the command, then apply it when ready:

   ```bash
   python app.py --update          # Preview the git pull command
   python app.py --update --apply  # Execute git pull --ff-only
   ```

   Update reports record stdout/stderr so you can review what changed without leaving the workflow. Configure at least one Git
   remote (e.g., `origin`) before running the update command; otherwise the controller will report that no remotes are available
   and skip the pull.

## Organization Reference

- `organization_profile.json` — machine-readable profile used by the controller.
- `docs/organization_reference.md` — human-friendly view regenerated whenever you run `python app.py --init-org`.

Keep these files version-controlled so new environments inherit the same branding, SKU structure, and contact information. If you onboard another business, run the init command again to update the values safely.

## ChatGPT Startup Prompt

The file [`docs/chatgpt_startup_prompt.md`](docs/chatgpt_startup_prompt.md) contains the startup instructions to load this controller inside ChatGPT. Paste its contents into a new ChatGPT conversation to operate the workflow conversationally. The CLI remains available as a fallback.

## Optional Distribution Notes

- Licensed under the MIT License (see `LICENSE`).
- Add a PayPal donation badge or additional documentation as needed before publishing publicly.

---

Crafted by True Good Craft — released for community use.
