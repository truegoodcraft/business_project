SERVICE_ID = "core.organizer"
VERSION = "0.1.0"


def describe() -> dict:
    return {
        "id": SERVICE_ID,
        "name": "Organizer",
        "version": VERSION,
        "builtin": True,
        "services": [],
        "scopes": [],
        "ui": {
            "tools_pages": [
                {
                    "id": "organizer",
                    "title": "Organizer",
                    "path": "ui/index.html",
                    "order": 100,
                }
            ]
        },
    }
