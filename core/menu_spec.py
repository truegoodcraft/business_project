"""Normalized CLI menu specification."""

MENU_SPEC = [
    (
        "Core",
        [
            ("0", "System Check — Validate credentials and status"),
            ("U", "Update from repository — Fetch and merge latest code"),
            ("1", "Discover & Audit — Read-only adapter audit"),
        ],
    ),
    (
        "Build",
        [
            ("12", "Build Master Index — Notion, Drive, (Sheets) → Markdown"),
            ("14", "Build Sheets Index — Enumerate spreadsheets & tabs"),
        ],
    ),
    (
        "Imports & Sync",
        [
            ("2", "Import from Gmail — Stage vendor quotes/orders"),
            ("3", "Import CSV → Inventory — Map CSV columns"),
            ("4", "Sync metrics → Google Sheets — Preview/push"),
        ],
    ),
    (
        "Linking & Data",
        [
            ("5", "Link Drive PDFs to Notion — Match and attach"),
            ("6", "Contacts/Vendors — Normalize & dedupe"),
        ],
    ),
    (
        "Config & Reports",
        [
            ("7", "Settings & IDs — View environment and saved queries"),
            ("8", "Logs & Reports — List recent run directories"),
        ],
    ),
    (
        "Optional",
        [
            ("9", "Wave — Discover Wave data and plan exports"),
        ],
    ),
    (
        "Exit",
        [
            ("q", "Quit"),
        ],
    ),
]
