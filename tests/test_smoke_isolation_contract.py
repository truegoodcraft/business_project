# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path


def test_smoke_isolation_wrapper_contract() -> None:
    path = Path("scripts/smoke_isolated.ps1")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "BUS_DB" in text
    assert "LOCALAPPDATA" in text
    assert "ALLOW_WRITES" in text
    assert "READ_ONLY" in text
    assert "BUS_DEV" in text
    assert "BUSCORE_HOME" in text
    assert "BUS_MODE" in text
    assert "PYTHONPATH" in text
    assert '$env:BUS_DEV = "0"' in text
    assert '$env:BUSCORE_HOME = Join-Path $tempDir "BUSCore"' in text
    assert '$env:BUS_MODE = "prod"' in text
    assert '$env:PYTHONPATH = [string]$repoRoot' in text
    assert "$hadOriginalBusDev" in text
    assert "$originalBusDev" in text
    assert "$hadOriginalBusCoreHome" in text
    assert "$originalBusCoreHome" in text
    assert "[smoke] BUS_DB ->" in text
    assert "Get-FreeTcpPort" in text
    assert "Test-TcpPortInUse" in text
    assert "Port {0} busy; using isolated port {1}" in text
    assert '"-File", (\'"{0}"\' -f $launchScript)' in text
    assert '[string]$PythonPath = ""' in text
    assert "core.api.http:create_app" in text
    assert "Smoke Python not found:" in text


def test_smoke_honors_localappdata_override() -> None:
    text = Path("scripts/smoke.ps1").read_text(encoding="utf-8")

    assert "function Get-LocalAppDataPath" in text
    assert "$env:LOCALAPPDATA" in text
    assert "$localAppData = Get-LocalAppDataPath" in text
    assert "$localAppData = [Environment]::GetFolderPath('LocalApplicationData')" not in text
    assert "$env:BUS_DB" in text
    assert "Split-Path -Parent $env:BUS_DB" in text
    assert "$journalDir = Get-JournalDir" in text


def test_smoke_cleanup_uses_display_quantity_contract() -> None:
    text = Path("scripts/smoke.ps1").read_text(encoding="utf-8")
    cleanup = text.split('Step "10. Cleanup"', maxsplit=1)[1]

    assert "stock_on_hand_display" in cleanup
    assert "cleanup:item:{0}.stock_on_hand_display.value" in cleanup
    assert "uom = $onHandUom" in cleanup
    assert 'Invoke-Json GET ($BaseUrl + "/app/items/$id")' in cleanup
    assert "Archived Item {0} (history preserved)" in cleanup
    assert "[decimal]$current.qty_stored" not in cleanup
    assert 'uom = "ea"' not in cleanup
    assert "Dev Mode: ON" not in text
