from core.config_validate import validate_plugin_config


def system_check() -> None:
    plugins = ["notion-plugin", "google-plugin"]
    issues: list[str] = []
    for pl in plugins:
        issues.extend(validate_plugin_config(pl))
    if issues:
        print("\nSystem Check — MISSING\n" + "\n".join(f" - {x}" for x in issues))
    else:
        print("\nSystem Check — READY ✅")
