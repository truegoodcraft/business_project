from core.brand import NAME, VENDOR
from core.menu_spec import ROOT_MENU, SUBMENUS


def render_root(quiet: bool = False):
    if not quiet:
        print(f"{NAME} — Controller Menu")
        print(f"made by: {VENDOR}")
        print()
    for key, label in ROOT_MENU:
        print(f" {key:>1}) {label}")
    print()
    print("Select an option (1–4, or q to quit): ", end="")


def render_submenu(root_key: str):
    print()
    section_name = next((lbl for k,lbl in ROOT_MENU if k == root_key), "Menu")
    print(section_name)
    items = SUBMENUS.get(root_key, [])
    for key, label, _handler in items:
        print(f"  {key}) {label}")
    print("  0) Back")
    print()
    print("Select an option (1–9, or 0 to go back): ", end="")
