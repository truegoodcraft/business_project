import importlib
import pathlib
import sys
import types
import tomllib

from core.capabilities import register


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
    for path, man in discover_plugins(root):
        api = str(man.get("plugin_api", ""))
        if not api.startswith("1."):
            continue
        module_name = man["entrypoint"]["module"]
        _prepare_packages(module_name, root_path, path)
        mod = importlib.import_module(module_name)
        for cap in man["capabilities"]:
            func = getattr(mod, cap["callable"])
            register(cap["name"], man["name"], man["version"], cap.get("scopes", []), func)
