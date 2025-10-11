# True Good Craft Controller

This repository implements the controller architecture described in the True Good Craft master project brief. It provides a single startup command that loads configuration, assembles modular adapters, and exposes a menu-driven workflow for the core business operations.

## Features

- **Single core controller** with modular adapters for Notion, Google Drive, Google Sheets, Gmail, and optional Wave.
- **Menu-driven actions** that follow the required plan → dry-run/apply → report flow.
- **ID-first, traceable runs** that create timestamped folders in `reports/` containing `plan.md`, `changes.md`, and `errors.md`.
- **Beginner-safe defaults** with configuration masking, preview-friendly dry runs, and clear notes on missing credentials.
- **ChatGPT-first interface** via the included startup prompt file, with a CLI fallback for local execution.

## Project Structure

```
app.py                 # CLI entrypoint (python app.py)
tgc/                   # Controller, adapters, and actions
  adapters/            # Modular integrations (safe stubs)
  actions/             # Menu commands with plan/dry-run/apply flow
  bootstrap.py         # Builds controller and registers actions
  config.py            # Loads .env and masks secrets
  controller.py        # Core orchestration engine
  menu.py              # CLI menu loop
  reporting.py         # Run context and report helpers
requirements.txt       # Python dependency list (empty by default)
docs/chatgpt_startup_prompt.md  # Prompt to operate the system via ChatGPT
```

Adapters are implemented as safe placeholders so the controller can run without third-party credentials. Each adapter exposes capability summaries and stub methods that can later be expanded to perform real API calls.

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

2. Install dependencies and launch the controller:

   ```bash
   pip install -r requirements.txt
   python app.py
   ```

3. Follow the prompts to select an action. Each action displays a plan, allows you to choose a dry run or apply mode, and writes reports under `reports/run_<ACTION>_<TIMESTAMP>/`.

## ChatGPT Startup Prompt

The file [`docs/chatgpt_startup_prompt.md`](docs/chatgpt_startup_prompt.md) contains the startup instructions to load this controller inside ChatGPT. Paste its contents into a new ChatGPT conversation to operate the workflow conversationally. The CLI remains available as a fallback.

## Optional Distribution Notes

- Licensed under the MIT License (see `LICENSE`).
- Add a PayPal donation badge or additional documentation as needed before publishing publicly.
