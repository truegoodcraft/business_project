<#
  THE PURGE: Removes monolithic adapters & extras to enforce Microkernel.
  Run from repo root:
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\purge_monolith.ps1
#>
$ErrorActionPreference = "Continue"
Write-Host "[purge] Removing adapter folders (if present)..."
Remove-Item -Recurse -Force "core\adapters\drive"   -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "core\adapters\notion"  -ErrorAction SilentlyContinue

Write-Host "[purge] Removing extras requirements (if present)..."
Remove-Item -Force "requirements-extras.txt" -ErrorAction SilentlyContinue

Write-Host "[purge] Done. Apply code patches and reinstall core requirements."
