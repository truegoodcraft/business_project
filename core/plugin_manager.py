import importlib
import json
import pathlib
import sys
import types
import tomllib

from core.capabilities import declare, register
from core.plugins_state import is_enabled as _plugin_enabled
from core.signing import PUBLIC_KEY_HEX, SIGNING_AVAILABLE, verify_plugin_signature
from core.unilog import write as uni_write

CORE_VERSION = "0.1.0"
SECURITY_LOG = pathlib.Path("reports/security.log")
DENYLIST_PATH = pathlib.Path("registry/denylist.json")

_SIGNING_STATUS_LOGGED = False


def discover_plugins(root: str = "plugins"):
    for p in pathlib.Path(root).glob("*-plugin"):
        m = p / "plugin.toml"
        if m.exists():
            data = tomllib.loads(m.read_text())
            yield p, data


def _ensure_namespace(name: str, path: pathlib.Path):
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module
    else:
        pkg_path = list(getattr(module, "__path__", []))  # type: ignore[attr-defined]
        str_path = str(path)
        if str_path not in pkg_path:
            pkg_path.append(str_path)
            module.__path__ = pkg_path  # type: ignore[attr-defined]
    return module


def _prepare_packages(module_name: str, root_path: pathlib.Path, plugin_path: pathlib.Path):
    parts = module_name.split(".")[:-1]
    if not parts:
        return
    for index, _ in enumerate(parts):
        package_name = ".".join(parts[: index + 1])
        if index == 0:
            package_path = root_path
        elif index == 1:
            package_path = plugin_path
        else:
            relative = parts[2 : index + 1]
            package_path = plugin_path.joinpath(*relative)
        _ensure_namespace(package_name, package_path)


def load_plugins(root: str = "plugins"):
    root_path = pathlib.Path(root)
    if not root_path.exists():
        return
    _ensure_namespace("plugins", root_path)
    if not SIGNING_AVAILABLE:
        _log_signing_disabled_once()
    denylist = _load_denylist()
    for path, man in discover_plugins(root):
        api = str(man.get("plugin_api", ""))
        if not api.startswith("1."):
            _log_security_event(
                f"[compat] Skipped {man.get('name', path.name)}: incompatible plugin_api '{api}'"
            )
            continue
        declare(man.get("name", path.name), man.get("version", ""), man.get("capabilities", []))
        plugin_name = man.get("name", path.name)
        if not _plugin_enabled(plugin_name):
            message = f"[disabled] Skipped {plugin_name}: disabled via plugins_state"
            _log_security_event(message)
            uni_write("plugin.skipped_disabled", None, plugin=plugin_name)
            continue
        if not _is_compatible(man):
            _log_security_event(
                f"[compat] Skipped {man.get('name', path.name)}: incompatible with core {CORE_VERSION}"
            )
            continue
        if SIGNING_AVAILABLE and not verify_plugin_signature(path, PUBLIC_KEY_HEX):
            _log_security_event(
                f"[signature] Skipped {man.get('name', path.name)}: signature verification failed"
            )
            continue
        if _is_blocked(man, denylist):
            _log_security_event(
                f"[denylist] Skipped {man.get('name', path.name)}: blocked by registry"
            )
            continue
        module_name = man["entrypoint"]["module"]
        _prepare_packages(module_name, root_path, path)
        mod = importlib.import_module(module_name)
        for cap in man["capabilities"]:
            func = getattr(mod, cap["callable"])
            register(
                cap["name"],
                man["name"],
                man["version"],
                cap.get("scopes", []),
                func,
                cap.get("network", False),
            )


def _log_security_event(message: str) -> None:
    SECURITY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SECURITY_LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"{message}\n")
    uni_write("security.note", None, message=message)


def _log_signing_disabled_once() -> None:
    global _SIGNING_STATUS_LOGGED
    if _SIGNING_STATUS_LOGGED:
        return
    _SIGNING_STATUS_LOGGED = True
    message = "[signature] Plugin signing disabled: PyNaCl not installed"
    _log_security_event(message)
    uni_write("plugin.signing.disabled", None)


def _load_denylist() -> set[tuple[str, str]]:
    try:
        data = json.loads(DENYLIST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError:
        _log_security_event("[denylist] Failed to parse denylist file")
        return set()
    blocked = set()
    for entry in data.get("blocked", []):
        name = entry.get("name")
        version = entry.get("version")
        if isinstance(name, str) and isinstance(version, str):
            blocked.add((name, version))
    return blocked


def _is_blocked(manifest: dict, denylist: set[tuple[str, str]]) -> bool:
    name = manifest.get("name")
    version = manifest.get("version")
    if not isinstance(name, str) or not isinstance(version, str):
        return False
    return (name, version) in denylist


def _is_compatible(manifest: dict) -> bool:
    compat = manifest.get("compat") or {}
    min_core = compat.get("min_core")
    max_core = compat.get("max_core")

    try:
        if min_core and _version_tuple(CORE_VERSION) < _version_tuple(min_core):
            return False
        if max_core and _version_tuple(CORE_VERSION) > _version_tuple(max_core):
            return False
    except ValueError:
        return False
    return True


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = value.split(".")
    if not parts:
        raise ValueError("empty version")
    try:
        return tuple(int(part) for part in parts)
    except ValueError as exc:  # pragma: no cover - invalid manifest data
        raise ValueError("invalid version component") from exc
