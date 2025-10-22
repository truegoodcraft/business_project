Param(
  [string]$Owner = ${env:BUS_GH_OWNER}  ? ${env:BUS_GH_OWNER}  : "truegoodcraft",
  [string]$Repo  = ${env:BUS_GH_REPO}   ? ${env:BUS_GH_REPO}   : "buisness_project",
  [string]$Branch= ${env:BUS_GH_BRANCH} ? ${env:BUS_GH_BRANCH} : "main",
  [int]$Port = ${env:BUS_PORT} ? [int]${env:BUS_PORT} : 8765
)
$ErrorActionPreference = "Stop"

function Need-Python {
  try { $v = python -c "import sys; print(sys.version)" } catch { return $false }
  return $true
}

function Get-Token {
  if ($env:GITHUB_TOKEN) { return $env:GITHUB_TOKEN }
  Write-Host "Private repo? Paste a GitHub token with read access (or press Enter to skip):"
  $tok = Read-Host
  return $tok
}

if (-not (Need-Python)) { throw "Python 3.11+ not found on PATH. Install Python and reopen PowerShell." }

$root = Join-Path $env:LOCALAPPDATA "BUSCore"
$app  = Join-Path $root "app"
$tmp  = Join-Path $root "tmp"
$zip  = Join-Path $tmp  "repo.zip"
$venv = Join-Path $root "env"
New-Item -ItemType Directory -Force -Path $root,$tmp | Out-Null

# Download ZIP (public or private)
$apiZip = "https://api.github.com/repos/$Owner/$Repo/zipball/$Branch"
$pubZip = "https://github.com/$Owner/$Repo/archive/refs/heads/$Branch.zip"
$tok = Get-Token
$hdr = @{ "User-Agent"="BUSCore-Launcher" }
if ($tok) { $hdr["Authorization"] = "Bearer $tok" }

try {
  Write-Host "Downloading $Owner/$Repo ($Branch)..."
  Invoke-WebRequest ($tok ? $apiZip : $pubZip) -Headers $hdr -OutFile $zip
} catch {
  throw "Download failed. If the repo is private, set GITHUB_TOKEN or paste a token when prompted."
}

# Unpack to app/
if (Test-Path $app) { Remove-Item $app -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $tmp -Force
# Find the single extracted directory
$unpacked = Get-ChildItem $tmp | Where-Object { $_.PSIsContainer -and $_.Name -notmatch "repo\.zip" } | Select-Object -First 1
if (-not $unpacked) { throw "Unpack failed." }
Move-Item $unpacked.FullName $app -Force
Remove-Item $zip -Force

# Ensure venv
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
  Write-Host "Creating venv..."
  python -m venv $venv
}
$py = Join-Path $venv "Scripts\python.exe"

# Install deps (requirements + Windows deps we rely on)
Write-Host "Installing dependencies..."
& $py -m pip install --upgrade pip
if (Test-Path (Join-Path $app "requirements.txt")) {
  & $py -m pip install -r (Join-Path $app "requirements.txt")
}
& $py -m pip install "pywin32>=306" "Send2Trash==1.8.2"

# Optional pywin32 postinstall (best-effort)
try { & $py -m pywin32_postinstall -install | Out-Null } catch { }

# Run
Push-Location $app
Write-Host "Starting BUS Core on http://127.0.0.1:$Port/ui"
Start-Process "http://127.0.0.1:$Port/ui"
& $py app.py serve --port $Port
Pop-Location
