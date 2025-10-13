REGISTRY: dict[str, dict] = {}  # name -> {plugin, version, scopes, func, network}


def register(name: str, plugin: str, version: str, scopes: list[str], func, network: bool = False):
    REGISTRY[name] = {
        "plugin": plugin,
        "version": version,
        "scopes": scopes,
        "func": func,
        "network": bool(network),
    }


def resolve(name: str):
    return REGISTRY[name]["func"]


def meta(name: str):
    return REGISTRY[name]
