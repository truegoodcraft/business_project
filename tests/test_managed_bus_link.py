from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "core" / "ui" / "js" / "cards" / "settings.js"


def test_settings_has_literal_managed_bus_inquiry_link():
    source = SETTINGS.read_text(encoding="utf-8")
    assert "Have TGC manage BUS for you" in source
    assert "host, update, back up, monitor, and support BUS Core" in source
    assert "The free self-managed application remains complete" in source
    assert "https://buscore.ca/managed-bus-inquiry?" in source
    assert "src=buscore-settings" in source
    assert "utm_source=bus-core" in source
    assert "utm_campaign=managed-bus" in source


def test_settings_link_has_safe_external_navigation_and_no_upgrade_gates():
    source = SETTINGS.read_text(encoding="utf-8")
    assert 'target="_blank" rel="noopener noreferrer">Discuss TGC Managed BUS</a>' in source
    for prohibited in ("BUS Pro", "entitlement", "subscription required", "upgrade to unlock", "premium feature"):
        assert prohibited not in source


def test_telemetry_explanation_uses_canonical_route():
    source = SETTINGS.read_text(encoding="utf-8")
    assert "https://buscore.ca/telemetry" in source
    assert "https://buscore.ca/privacy.html" not in source
