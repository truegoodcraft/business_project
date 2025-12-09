# scripts/build-windows.ps1
[CmdletBinding()]
param(
  [string]$Python = "python"
)

$ErrorActionPreference = 'Stop'

Write-Host "BUS Core Windows Build" -ForegroundColor Cyan

# Resolve repo root (scripts/..)
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

Push-Location $Root
try {
  Write-Host "[INFO] Using Python: $Python"
  & $Python -c "import sys; print(sys.version)" | Out-Null

  Write-Host "[INFO] Upgrading pip/setuptools/wheel..."
  & $Python -m pip install --upgrade pip setuptools wheel

  if (Test-Path "$Root\requirements.txt") {
    Write-Host "[INFO] Installing requirements.txt"
    & $Python -m pip install -r requirements.txt
  } else {
    Write-Host "[WARN] requirements.txt not found (continuing)"
  }

  if (Test-Path "$Root\requirements-extras.txt") {
    Write-Host "[INFO] Installing requirements-extras.txt"
    & $Python -m pip install -r requirements-extras.txt
  } else {
    Write-Host "[INFO] requirements-extras.txt not present (skipping)"
  }

  Write-Host "[INFO] Installing PyInstaller..."
  & $Python -m pip install pyinstaller

  # Prefer an existing .spec; fallback to a simple recipe
  $spec = Get-ChildItem -Path $Root -Filter *.spec -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($null -ne $spec) {
    Write-Host "[INFO] Building via spec: $($spec.Name)"
    & $Python -m PyInstaller $spec.FullName --noconfirm
  } else {
    Write-Host "[WARN] No .spec found; using default PyInstaller recipe"
    # NOTE: On Windows, --add-data uses "SRC;DEST"
    & $Python -m PyInstaller --noconfirm --name "TGC-Controller" --onefile `
      --add-data "core\ui;core\ui" launcher.py
  }

  $dist = Join-Path $Root "dist"
  if (-not (Test-Path $dist)) { throw "dist directory not created" }

  # Heuristics for output dir
  $outDir = if (Test-Path (Join-Path $dist "TGC-Controller")) {
    Join-Path $dist "TGC-Controller"
  } else {
    $dist
  }

  foreach ($f in @("LICENSE","README.md")) {
    $src = Join-Path $Root $f
    if (Test-Path $src) {
      Copy-Item $src -Destination $outDir -Force -ErrorAction SilentlyContinue
    }
  }

  Write-Host "[DONE] Built artifacts at $outDir" -ForegroundColor Green
} finally {
  Pop-Location
}
