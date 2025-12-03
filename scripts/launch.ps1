# scripts/launch.ps1
param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8765,
  [string]$DbPath = "data/app.db",
  [switch]$Reload,
  [switch]$Quiet
)

# WinPS 5.1-safe color echo
function Say([string]$Text, [string]$Color = "White") {
  if (-not $Quiet) { Write-Host $Text -ForegroundColor $Color }
}

# Repo root (parent of /scripts)
$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")
Push-Location $repoRoot

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

  # Resolve DB path and ensure folder
  if (-not (Split-Path -IsAbsolute $DbPath)) {
    $DbPath = Join-Path $PWD.Path $DbPath
  }
  $dbDir = Split-Path -Parent $DbPath
  if (-not (Test-Path $dbDir)) { New-Item -Type Directory -Path $dbDir | Out-Null }

  $env:BUS_DB     = $DbPath
  $env:PYTHONUTF8 = "1"
  Say ("[db] BUS_DB -> {0}" -f $env:BUS_DB) "DarkGray"
  Say ("[db] Using SQLite at: {0}" -f $env:BUS_DB) "DarkGray"

  # Build uvicorn args
  $uvArgs = @("tgc.http:app","--host",$BindHost,"--port",$Port)
  if ($Reload) { $uvArgs += "--reload" }

  Say ("[launch] Starting BUS Core at http://{0}:{1}" -f $BindHost,$Port) "Green"
  & $venvPy -m uvicorn @uvArgs
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}
