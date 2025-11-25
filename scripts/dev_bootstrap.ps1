# scripts/dev_bootstrap.ps1
# SPDX-License-Identifier: AGPL-3.0-or-later
$ErrorActionPreference = "Stop"

# Resolve repo root and ensure CWD regardless of invocation location
$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $RepoRoot

# --- BUSCore: allow custom port from env for parallel runs (smoke) ---
$port = [int]($env:BUSCORE_PORT) 
if (-not $port -or $port -lt 1) { $port = 8765 }

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
if (Test-Path -Path "$RepoRoot\requirements.txt") {
  & $Py -m pip install -r "$RepoRoot\requirements.txt"
} else {
  & $Py -m pip install fastapi "uvicorn[standard]" pydantic pydantic-settings platformdirs
}

# Env for in-place dev
$env:PYTHONPATH = $RepoRoot
$env:BUS_UI_DIR = Join-Path $RepoRoot "core\ui"

# Ensure BUSCore dirs + community license
$BcRoot = Join-Path $env:LOCALAPPDATA 'BUSCore'
$null = New-Item -ItemType Directory -Force -Path $BcRoot
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BcRoot 'secrets')
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BcRoot 'state')
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BcRoot 'app')
$LicPath = Join-Path $BcRoot 'license.json'
if (!(Test-Path $LicPath)) {
  '{"tier":"community","features":{},"plugins":{}}' | Set-Content -Encoding UTF8 -Path $LicPath
  Write-Host "[dev] Wrote default community license at $LicPath"
} else {
  Write-Host "[dev] Found existing license at $LicPath"
}

# Start server minimized and open UI
$Args = @("-c", "import uvicorn; uvicorn.run('tgc.http:app', host='127.0.0.1', port=$port, log_level='info')")
Start-Process -WindowStyle Minimized -FilePath $Py -ArgumentList $Args
Start-Sleep -Seconds 2
$BaseUrl = "http://127.0.0.1:$port"
Start-Process $BaseUrl

Write-Host "BUS Core - Running on $BaseUrl"
