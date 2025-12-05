# SPDX-License-Identifier: AGPL-3.0-or-later
# scripts/launch.ps1
param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8765,
  [string]$DbPath = $null,
  [switch]$Reload,
  [switch]$Quiet,
  [switch]$Smoke
)

# WinPS 5.1-safe color echo
function Say([string]$Text, [string]$Color = "White") {
  if (-not $Quiet) { Write-Host $Text -ForegroundColor $Color }
}

# Repo root (parent of /scripts)
$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")
Push-Location $repoRoot

# Default BUS_DEV to 0 unless explicitly set
if (-not $env:BUS_DEV) { $env:BUS_DEV = "0" }

try {
  # Ensure venv
  $venvPy = Join-Path ".\.venv\Scripts" "python.exe"
  if (-not (Test-Path $venvPy)) {
    Say "[launch] Creating venv..." "Cyan"
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed." }
  }

  # Conditional pip install by hashing requirements
  $req = "requirements.txt"
  if (-not (Test-Path $req)) { throw "Missing requirements.txt at repo root." }

  $hashPath = ".\.venv\.req.hash"
  $reqHash  = (Get-FileHash -Algorithm SHA256 $req).Hash
  $oldHash  = ""
  if (Test-Path $hashPath) { $oldHash = (Get-Content $hashPath -ErrorAction SilentlyContinue) }

  if ($reqHash -ne $oldHash) {
    Say "[launch] Installing/updating dependencies..." "Cyan"
    & $venvPy -m pip install -U -r $req
    if ($LASTEXITCODE -ne 0) { throw "pip install failed." }
    $reqHash | Out-File -Encoding ascii $hashPath
  }

  # Resolve DB path and ensure folder (default: AppData via platformdirs)
  $targetDb = $null
  $dbSource = "APPDATA"

  if ($env:BUS_DB) {
    $targetDb = $env:BUS_DB
    $dbSource = "ENV"
  } elseif ($PSBoundParameters.ContainsKey('DbPath') -and $DbPath) {
    $targetDb = $DbPath
    $dbSource = "PARAM"
  } else {
    $targetDb = (& $venvPy - <<'PY'
from platformdirs import user_data_dir
from pathlib import Path
print(Path(user_data_dir("TGC-BUS-Core", "TrueGoodCraft")) / "app.db")
PY
    ).Trim()

    # One-time migrate repo db -> AppData if AppData missing
    try {
      $appDataDb = $targetDb
      $repoDb = Join-Path (Join-Path $scriptDir "..") "data\app.db"
      if ((Test-Path $repoDb) -and -not (Test-Path $appDataDb)) {
        Say "[db] Migrating existing repo DB to AppData..." "Yellow"
        $appDataDir = Split-Path -Parent $appDataDb
        if (-not (Test-Path $appDataDir)) { New-Item -ItemType Directory -Force -Path $appDataDir | Out-Null }
        Copy-Item -Path $repoDb -Destination $appDataDb -Force
        Say "[db] Migrated -> $appDataDb" "Yellow"
      }
    } catch {
      Say "[db] Migration skipped (error): $($_.Exception.Message)" "Yellow"
    }
  }

  if (-not (Split-Path -IsAbsolute $targetDb)) {
    $targetDb = Join-Path $PWD.Path $targetDb
  }

  $dbDir = Split-Path -Parent $targetDb
  if (-not (Test-Path $dbDir)) { New-Item -Type Directory -Path $dbDir | Out-Null }

  $env:BUS_DB     = $targetDb
  $env:PYTHONUTF8 = "1"
  Say ("[db] BUS_DB ({0}) -> {1}" -f $dbSource, $env:BUS_DB) "DarkGray"
  Say ("[db] Using SQLite at: {0}" -f $env:BUS_DB) "DarkGray"

  # SPDX header warning (non-fatal)
  try {
    $missing = (git grep -L "SPDX-License-Identifier" -- "*.py" "*.ps1" "*.js" "*.ts" "*.css" "*.html" 2>$null | measure-object -line).Lines
    if ($missing -gt 0) {
      Write-Warning "[license] $missing files missing SPDX headers. Run: python scripts/tools/add_license_headers.py"
    }
  } catch {
    Write-Verbose "[license] git not available for SPDX check"
  }

  # Build uvicorn args
  $uvArgs = @("tgc.http:app","--host",$BindHost,"--port",$Port)
  if ($Reload) { $uvArgs += "--reload" }

  Say ("[launch] Starting BUS Core at http://{0}:{1}" -f $BindHost,$Port) "Green"
  & $venvPy -m uvicorn @uvArgs

  if ($Smoke) {
    Start-Sleep -Seconds 2
    Say "[launch] Running smoke.ps1..." "Cyan"
    # Build URL safely with -f formatting to avoid $var: parsing errors
    $baseUrl = "http://{0}:{1}" -f $BindHost, $Port
    pwsh -NoProfile -File "$scriptDir\smoke.ps1" -BaseUrl $baseUrl
  }
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}
