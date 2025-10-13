from core.config_validate import validate_plugin_config
from core.unilog import write as uni_write


def system_check() -> None:
    plugins = ["notion-plugin", "google-plugin"]
    issues: list[str] = []
    for pl in plugins:
        issues.extend(validate_plugin_config(pl))
    if issues:
        print("\nSystem Check — MISSING\n" + "\n".join(f" - {x}" for x in issues))
    else:
        print("\nSystem Check — READY ✅")
    uni_write("system_check", None, status=("READY" if not issues else "MISSING"), issues=issues)
