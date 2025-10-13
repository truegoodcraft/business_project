# Root categories: 1–4 only
ROOT_MENU = [
  ("1", "Status & Health"),
  ("2", "Build & Indexing"),
  ("3", "Data Operations"),
  ("4", "Config & Tools"),
  ("q", "Quit"),
]

# Submenus: items numbered 1–9 only. Use existing actions/labels.
SUBMENUS = {
  "1": [  # Status & Health
    ("1", "System Check — Validate credentials and status", "action_system_check"),
    ("2", "Discover & Audit — Read-only adapter audit", "action_discover_audit"),
    ("3", "Plugins Hub — Discover / Auto-connect / Debug / Configure", "action_plugins_hub"),
  ],
  "2": [  # Build & Indexing
    ("1", "Build Master Index — Notion, Drive, (Sheets) → Markdown", "action_build_master_index"),
    ("2", "Build Sheets Index — Enumerate spreadsheets & tabs", "action_build_sheets_index"),
  ],
  "3": [  # Data Operations
    ("1", "Import from Gmail — Stage vendor quotes/orders", "action_import_gmail"),
    ("2", "Import CSV → Inventory — Map CSV columns", "action_import_csv"),
    ("3", "Sync metrics → Google Sheets — Preview/push", "action_sync_metrics"),
    ("4", "Link Drive PDFs to Notion — Match and attach", "action_link_drive_pdfs"),
    ("5", "Contacts/Vendors — Normalize & dedupe", "action_contacts_vendors"),
    ("6", "Wave — Discover Wave data and plan exports", "action_wave"),
  ],
  "4": [  # Config & Tools
    ("1", "Settings & IDs — View environment and saved queries", "action_settings_ids"),
    ("2", "Logs & Reports — List recent run directories", "action_logs_reports"),
    ("3", "Update from repository — Fetch and merge latest code", "action_update_repo"),
  ],
}

# Legacy shim: map old flat hotkeys to new (section, item) actions.
# Keys are the user input strings you already supported.
LEGACY_SHIMS = {
  "0":  ("1","1"),  # System Check
  "1":  ("1","2"),  # Discover & Audit
  "12": ("2","1"),  # Build Master Index
  "15": ("2","2"),  # Build Sheets Index
  "2":  ("3","1"),  # Import Gmail
  "3":  ("3","2"),  # Import CSV
  "4":  ("3","3"),  # Sync metrics
  "5":  ("3","4"),  # Link PDFs
  "6":  ("3","5"),  # Contacts/Vendors
  "7":  ("4","1"),  # Settings & IDs
  "8":  ("4","2"),  # Logs & Reports
  "9":  ("3","6"),  # Wave
  "20": ("1","3"),  # Plugins Hub
  "0U": ("4","3"),  # Update repo (if you used that alias)
}
