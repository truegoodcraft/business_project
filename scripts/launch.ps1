<#  BUS Core – Dev Launcher (Windows PowerShell 5.1 compatible)
    - Creates venv if missing
    - Installs/updates deps ONLY if requirements.txt changed (hash)
    - Ensures data folder exists and exports BUS_DB
    - Starts uvicorn
    Usage:
      powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch.ps1 -Host 127.0.0.1 -Port 8765 -Reload:$false -DbPath data\app.db
#>
param(
  [string]$Host = "127.0.0.1",
  [int]$Port    = 8765,
  [bool]$Reload = $false,
  [string]$DbPath = "data\app.db"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Say([string]$msg, [ConsoleColor]$c = [ConsoleColor]::Gray) { Write-Host $msg -ForegroundColor $c }

$venvPath = ".venv"
$reqFile  = "requirements.txt"
$hashFile = Join-Path $venvPath ".req.hash"

# 1) Venv
if (-not (Test-Path $venvPath)) {
  Say "[launch] Creating venv..." Cyan
  python -m venv $venvPath
}

$python = Join-Path $venvPath "Scripts\python.exe"

# 2) Pip install (only if requirements changed)
if (Test-Path $reqFile) {
  $newHash = (Get-FileHash $reqFile -Algorithm SHA256).Hash
  $oldHash = ""
  if (Test-Path $hashFile) { $oldHash = Get-Content $hashFile -Raw }
  if ($newHash -ne $oldHash) {
    Say "[launch] Installing requirements..." Cyan
    & $python -m pip install --upgrade pip --disable-pip-version-check | Out-Null
    & $python -m pip install -r $reqFile --no-input | Out-Null
    $newHash | Out-File $hashFile -Encoding ascii
  } else {
    Say "[launch] Requirements unchanged (skip install)" DarkGray
  }
} else {
  Say "[launch] No requirements.txt found – skipping install" DarkGray
}

# 3) Ensure data folder & expand DB path (file may not exist yet)
$dp = Split-Path -Parent $DbPath
$leaf = Split-Path -Leaf $DbPath
if ($dp -and -not (Test-Path $dp)) { New-Item -ItemType Directory -Force -Path $dp | Out-Null }
if (-not $dp) { $dp = (Get-Location).Path }
$fullDp = (Resolve-Path $dp).Path
$resolvedDbPath = Join-Path $fullDp $leaf

# 4) Env
$env:PYTHONUTF8 = "1"
$env:BUS_DB     = $resolvedDbPath
Say "[db] BUS_DB -> $env:BUS_DB" DarkGray

# 5) Run API
Say "[launch] Starting BUS Core at http://$Host`:$Port" Green
if ($Reload) {
  & $python -m uvicorn tgc.http:app --host $Host --port $Port --reload
} else {
  & $python -m uvicorn tgc.http:app --host $Host --port $Port
}
