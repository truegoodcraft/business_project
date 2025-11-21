# scripts/dev_bootstrap.ps1
# SPDX-License-Identifier: AGPL-3.0-or-later
$ErrorActionPreference = "Stop"

# Resolve repo root
$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $RepoRoot

# Ensure venv
$VenvDir = Join-Path $RepoRoot ".venv"
if (!(Test-Path $VenvDir)) {
  Write-Host "[dev] Creating venv at $VenvDir"

  # Find a Python interpreter: prefer py.exe if present, else python/python3
  $Launcher = $null
  foreach ($c in @("py","python","python3")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { $Launcher = $cmd.Path; break }
  }
  if (-not $Launcher) {
    throw "Python 3.x not found on PATH. Install Python and re-run."
  }

  if ($Launcher -like "*\py.exe") {
    & $Launcher -3 -m venv "$VenvDir"
  } else {
    & $Launcher -m venv "$VenvDir"
  }
}

# Venv python
$Py = Join-Path $VenvDir "Scripts\python.exe"
if (!(Test-Path $Py)) { throw "Missing venv python at $Py" }

# Upgrade pip + install deps
& $Py -m pip install --upgrade pip
& $Py -m pip install -r "$RepoRoot\requirements.txt"

# Env for in-place dev
$env:PYTHONPATH = $RepoRoot
$env:BUS_UI_DIR = Join-Path $RepoRoot "core\ui"

# Ensure BUSCore dirs + community license
$BcRoot = Join-Path $env:LOCALAPPDATA 'BUSCore'
$null = New-Item -ItemType Directory -Force -Path $BcRoot
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BcRoot 'secrets')
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BcRoot 'state')
$LicPath = Join-Path $BcRoot 'license.json'
if (!(Test-Path $LicPath)) {
  '{"tier":"community","features":{},"plugins":{}}' | Set-Content -Encoding UTF8 -Path $LicPath
  Write-Host "[dev] Wrote default community license at $LicPath"
} else {
  Write-Host "[dev] Found existing license at $LicPath"
}

# Start server (reload) minimized and open UI
$Args = @("-m","uvicorn","core.api.http:create_app","--host","127.0.0.1","--port","8765","--reload")
Start-Process -WindowStyle Minimized -FilePath $Py -ArgumentList $Args
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:8765/ui/shell.html"

Write-Host "[dev] BUS Core starting at http://127.0.0.1:8765"
