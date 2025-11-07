# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

"""Menu layout specification for the controller CLI."""

MAIN_MENU = [
  ("1", "Status & Plugins — Read-only overview (no actions)"),
  ("2", "Data Operations — Run indexing/import/sync/link workflows"),
  ("3", "Plugins Hub — Discover / Auto-connect / Debug / Configure plugins"),
  ("4", "Controller Config & Tools — Base controller settings, logs, retention, update"),
  ("q", "Quit"),
]

SUBMENU_DATA_OPS = [
  ("12", "Build Master Index — Notion, Drive, (Sheets) → Markdown"),
  ("15", "Build Sheets Index — Enumerate spreadsheets & tabs"),
  ("2",  "Import from Gmail — Stage vendor quotes/orders"),
  ("3",  "Import CSV → Inventory — Map CSV columns"),
  ("4",  "Sync metrics → Google Sheets — Preview/push"),
  ("5",  "Link Drive PDFs to Notion — Match and attach"),
  ("6",  "Contacts/Vendors — Normalize & dedupe"),
  ("b",  "Back"),
]

CONTROLLER_CONFIG_MENU = [
  ("1", "System Check — Validate credentials and status"),
  ("2", "Logs & Reports — List recent run directories"),
  ("3", "Retention — Prune old runs"),
  ("4", "Update from repository — Fetch and merge latest code"),
  ("5", "Consent management — Grant/revoke plugin scopes"),
  ("6", "About / Versions — Core build & plugin summary"),
  ("b", "Back"),
]

# Read-only “Status & Plugins” sections pulled from runtime_state & registry
STATUS_PLUGINS_SECTIONS = [
  "Core Status",          # Ready flags, SafeMode/Subprocess flags
  "APIs (Notion/Drive/Sheets)",   # READY/MISSING
  "Installed Plugins",    # name@version, enabled, config ok/missing, health
  "Indexing Capabilities" # list of capabilities that match *.index* (NOT running)
]

LEGACY_ACTIONS = {
  "0": "action_system_check",
  "1": "action_discover_audit",
  "12": "action_build_master_index",
  "15": "action_build_sheets_index",
  "2": "action_import_gmail",
  "3": "action_import_csv",
  "4": "action_sync_metrics",
  "5": "action_link_drive_pdfs",
  "6": "action_contacts_vendors",
  "7": "action_settings_ids",
  "8": "action_logs_reports",
  "9": "action_wave",
  "20": "action_plugins_hub",
  "0U": "action_update_repo",
}
