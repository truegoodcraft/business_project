import json
import pathlib

_STORE = pathlib.Path("consents.json")
_CONSENTS = json.loads(_STORE.read_text()) if _STORE.exists() else {}


def approved(plugin: str, scope: str) -> bool:
    return _CONSENTS.get(f"{plugin}:{scope}", False)


def require(plugin: str, scopes: list[str]):
    missing = [s for s in scopes if not approved(plugin, s)]
    if missing:
        raise PermissionError(f"Missing consent: {plugin} -> {', '.join(missing)}")


def grant(plugin: str, scopes: list[str]):
    for s in scopes:
        _CONSENTS[f"{plugin}:{s}"] = True
    _STORE.write_text(json.dumps(_CONSENTS, indent=2))
