REGISTRY: dict[str, dict] = {}  # name -> {plugin, version, scopes, func}


def register(name: str, plugin: str, version: str, scopes: list[str], func):
    REGISTRY[name] = {"plugin": plugin, "version": version, "scopes": scopes, "func": func}


def resolve(name: str):
    return REGISTRY[name]["func"]


def meta(name: str):
    return REGISTRY[name]
