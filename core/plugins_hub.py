# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

"""Interactive Plugins Hub for discovery and diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from core.plugins_state import is_enabled, set_enabled
from core.runtime_state import gather_plugin_health, plugin_descriptors, probe_plugin_health
from core.unilog import write as uni_write


def run_plugins_hub() -> None:
    """Launch the Plugins Hub interactive loop."""

    while True:
        print("\n=== PLUGINS HUB ===")
        print("H1) Discover plugins")
        print("H2) Auto-connect available plugins")
        print("H3) Test a plugin")
        print("H4) Configure a plugin (view schema & paths)")
        print("H5) Enable/Disable a plugin")
        print("H6) Debug broken connections (batch health)")
        print("Q) Back to main menu")
        choice = input("Select an option: ").strip().upper()
        if choice in {"Q", "", "QUIT", "BACK"}:
            break
        if choice == "H1":
            _handle_discover()
            continue
        if choice == "H2":
            _handle_autoconnect()
            continue
        if choice == "H3":
            _handle_test()
            continue
        if choice == "H4":
            _handle_configure()
            continue
        if choice == "H5":
            _handle_toggle()
            continue
        if choice == "H6":
            _handle_debug()
            continue
        print("Unknown selection. Use H1-H6 or Q to return.")


def _handle_discover() -> None:
    status = gather_plugin_health()
    items = status.get("items", [])
    summary = status.get("summary", {})
    print("\n--- Installed Plugins ---")
    for item in items:
        name = item.get("name")
        version = item.get("version") or "?"
        enabled = "enabled" if item.get("enabled") else "disabled"
        manifest_ok = "ok" if item.get("manifest_ok") else f"error ({item.get('manifest_error')})"
        missing_env = item.get("config", {}).get("missing_env") or []
        health = item.get("health", {})
        health_status = health.get("status") or "unknown"
        notes = "; ".join(health.get("notes") or [])
        print(f"- {name} @ {version}: {enabled}; manifest={manifest_ok}; health={health_status}")
        if missing_env:
            print(f"  missing env: {', '.join(missing_env)}")
        if notes:
            print(f"  notes: {notes}")
    print(
        "Summary: total={total}, enabled={enabled}, ok={ok}".format(
            total=summary.get("total", 0),
            enabled=summary.get("enabled", 0),
            ok=summary.get("ok", 0),
        )
    )
    uni_write("plugins_hub.discover", None, total=summary.get("total", 0))


def _handle_autoconnect() -> None:
    status = gather_plugin_health()
    items = status.get("items", [])
    connected = 0
    needs_help = 0
    print("\n--- Auto-connect guidance ---")
    for item in items:
        name = item.get("name")
        missing_env = item.get("config", {}).get("missing_env") or []
        env_keys = item.get("config", {}).get("env_keys") or []
        plugin_root = item.get("paths", {}).get("root")
        secrets_path = Path(plugin_root or ".") / "plugin.secrets.local.env"
        if not missing_env and item.get("enabled") and item.get("manifest_ok"):
            print(f"- {name}: connected (env keys: {', '.join(env_keys) or 'none'})")
            connected += 1
            continue
        needs_help += 1
        print(f"- {name}: configuration required")
        if missing_env:
            print(f"  missing env: {', '.join(missing_env)}")
        if env_keys:
            print("  set values in .env or:")
            print(f"    {secrets_path}")
        if name == "google-plugin":
            print(f"  hint: { _google_share_hint() }")
    print(
        f"Summary: connected={connected}, attention={needs_help}, total={len(items)}"
    )
    uni_write(
        "plugins_hub.autoconnect",
        None,
        total=len(items),
        connected=connected,
        needs_attention=needs_help,
    )


def _handle_test() -> None:
    descriptors = plugin_descriptors()
    if not descriptors:
        print("No plugins discovered.")
        return
    print("\nSelect plugin to test:")
    for idx, descriptor in enumerate(descriptors, start=1):
        status = "enabled" if descriptor.enabled else "disabled"
        print(f"  {idx}) {descriptor.name} ({status})")
    answer = input("Enter number or name (blank to cancel): ").strip()
    if not answer:
        return
    chosen: Optional[str]
    if answer.isdigit():
        idx = int(answer) - 1
        if idx < 0 or idx >= len(descriptors):
            print("Invalid selection.")
            return
        chosen = descriptors[idx].name
    else:
        names = {descriptor.name: descriptor for descriptor in descriptors}
        if answer not in names:
            print(f"Unknown plugin '{answer}'.")
            return
        chosen = answer
    if chosen is None:
        return
    print(f"\n--- Health probe: {chosen} ---")
    result = probe_plugin_health(chosen)
    if result is None:
        print("Plugin not found.")
        return
    status = result.get("status", "unknown")
    capability = result.get("capability") or "(none)"
    notes = result.get("notes") or []
    print(f"status: {status}")
    print(f"capability: {capability}")
    for note in notes:
        print(f"  note: {note}")
    uni_write(
        "plugins_hub.test",
        None,
        plugin=chosen,
        status=status,
    )


def _handle_configure() -> None:
    status = gather_plugin_health()
    items = status.get("items", [])
    if not items:
        print("No plugins discovered.")
        return
    names = [item.get("name") for item in items]
    print("\nAvailable plugins:")
    for idx, name in enumerate(names, start=1):
        print(f"  {idx}) {name}")
    answer = input("Enter number or name (blank to cancel): ").strip()
    if not answer:
        return
    target_name: Optional[str] = None
    if answer.isdigit():
        idx = int(answer) - 1
        if 0 <= idx < len(names):
            target_name = names[idx]
    elif answer in names:
        target_name = answer
    if not target_name:
        print("Invalid selection.")
        return
    item = next((it for it in items if it.get("name") == target_name), None)
    if not item:
        print("Plugin not found.")
        return
    env_keys = item.get("config", {}).get("env_keys") or []
    missing = item.get("config", {}).get("missing_env") or []
    plugin_root = Path(item.get("paths", {}).get("root") or ".")
    secrets_path = (plugin_root / "plugin.secrets.local.env").resolve()
    print(f"\n--- Configuration: {target_name} ---")
    for key in env_keys:
        present = "✅" if key not in missing else "❌"
        print(f"  {present} {key}")
    print("  set globally via .env at:")
    print(f"    {Path('.env').resolve()}")
    print("  or locally via:")
    print(f"    {secrets_path}")
    uni_write(
        "plugins_hub.configure.view",
        None,
        plugin=target_name,
        missing_env=len(missing),
    )


def _handle_toggle() -> None:
    descriptors = plugin_descriptors()
    if not descriptors:
        print("No plugins discovered.")
        return
    print("\nCurrent plugin state:")
    for idx, descriptor in enumerate(descriptors, start=1):
        flag = "enabled" if descriptor.enabled else "disabled"
        print(f"  {idx}) {descriptor.name} — {flag}")
    answer = input("Enter number or name to toggle (blank to cancel): ").strip()
    if not answer:
        return
    target: Optional[str]
    if answer.isdigit():
        idx = int(answer) - 1
        if idx < 0 or idx >= len(descriptors):
            print("Invalid selection.")
            return
        target = descriptors[idx].name
    else:
        names = {d.name for d in descriptors}
        if answer not in names:
            print(f"Unknown plugin '{answer}'.")
            return
        target = answer
    if target is None:
        return
    new_state = not is_enabled(target)
    set_enabled(target, new_state)
    event = "plugins_hub.enable" if new_state else "plugins_hub.disable"
    uni_write(event, None, plugin=target)
    print(
        f"Set {target} to {'enabled' if new_state else 'disabled'}. Restart CLI to reload plugins."
    )


def _handle_debug() -> None:
    status = gather_plugin_health()
    items = status.get("items", [])
    issues = [item for item in items if item.get("health", {}).get("status") != "ok"]
    if not issues:
        print("All plugins report ok status.")
        uni_write("plugins_hub.debug", None, issues=0)
        return
    print("\n--- Debug: plugins needing attention ---")
    for item in issues:
        name = item.get("name")
        health = item.get("health", {})
        notes = health.get("notes") or []
        missing_env = item.get("config", {}).get("missing_env") or []
        print(f"- {name}: status={health.get('status', 'unknown')}")
        if missing_env:
            print(f"  missing env: {', '.join(missing_env)}")
        for note in notes:
            print(f"  note: {note}")
    uni_write("plugins_hub.debug", None, issues=len(issues))


def _google_share_hint() -> str:
    try:
        from tgc.integration_support import sheets_share_hint
    except Exception:  # pragma: no cover - optional dependency guard
        return "Share Drive folders and Sheets with the service account email."
    try:
        from tgc.modules.google_drive import GoogleDriveModule
    except Exception:  # pragma: no cover - optional dependency guard
        return sheets_share_hint(None)
    try:
        module = GoogleDriveModule.load()
        email = module.config.credentials.get("client_email") if module else None
    except Exception:  # pragma: no cover - optional dependency guard
        email = None
    return sheets_share_hint(email)
