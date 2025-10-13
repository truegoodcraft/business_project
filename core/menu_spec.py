"""Normalized CLI menu specification."""

MENU_SPEC = [
    (
        "Core",
        [
            ("0", "System Check — Validate credentials and status"),
            ("1", "Discover & Audit — Read-only adapter audit"),
            ("U", "Update from repository — Fetch and merge latest code"),
        ],
    ),
    (
        "Build",
        [
            ("12", "Build Master Index — Notion, Drive, (Sheets) → Markdown"),
            ("13", "Master Index Snapshot (debug) — Print JSON for inspection"),
            ("14", "Build Sheets Index — Enumerate spreadsheets & tabs"),
        ],
    ),
    (
        "Imports & Sync",
        [
            ("2", "Import from Gmail — Stage vendor quotes/orders (optional)"),
            ("3", "Import CSV → Inventory — Map CSV columns"),
            ("4", "Sync metrics → Google Sheets — Preview/push"),
        ],
    ),
    (
        "Linking & Data",
        [
            ("5", "Link Drive PDFs to Notion — Match and attach"),
            ("6", "Contacts & Vendors — Normalize & dedupe"),
        ],
    ),
    (
        "Config & Reports",
        [
            ("7", "Settings & IDs — View environment and saved queries"),
            ("8", "Logs & Reports — List recent run directories"),
            ("10", "Google Drive Module — Configure sharing & validation"),
            ("11", "Notion Module — Review access & troubleshooting"),
            ("15", "Plugin Consents — Grant or revoke scopes"),
            ("17", "Retention Cleanup — Preview or prune historical runs"),
        ],
    ),
    (
        "Optional",
        [
            ("9", "Wave — Discover Wave data and plan exports"),
        ],
    ),
    ("Exit", [("q", "Quit")]),
]
