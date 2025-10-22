Param(
  [string]$Owner  = $env:BUS_GH_OWNER,
  [string]$Repo   = $env:BUS_GH_REPO,
  [string]$Branch = $env:BUS_GH_BRANCH,
  [int]$Port      = $(if ($env:BUS_PORT) { [int]$env:BUS_PORT } else { 8765 })
)
$ErrorActionPreference = "Stop"

if (-not $Owner  -or $Owner  -eq "") { $Owner  = "truegoodcraft" }
if (-not $Repo   -or $Repo   -eq "") { $Repo   = "buisness_project" }
if (-not $Branch -or $Branch -eq "") { $Branch = "main" }

function Resolve-VenvPython([string]$venvRoot) {
  $exe = Join-Path $venvRoot "Scripts\python.exe"
  if (Test-Path $exe) { return $exe }

  # Windows Store Python may redirect under Packages\...\LocalCache\Local\BUSCore\env
  $pkgRoot = Join-Path $env:LOCALAPPDATA "Packages"
  if (Test-Path $pkgRoot) {
    $pkgs = Get-ChildItem $pkgRoot -Directory -Filter "PythonSoftwareFoundation.Python.*" -ErrorAction SilentlyContinue
    foreach ($p in $pkgs) {
      $alt = Join-Path $p.FullName "LocalCache\Local\BUSCore\env\Scripts\python.exe"
      if (Test-Path $alt) { return $alt }
    }
  }

  # Fallback: search under venvRoot
  $found = Get-ChildItem -Path $venvRoot -Recurse -Filter "python.exe" -ErrorAction SilentlyContinue `
           | Where-Object { $_.FullName -match "\\env\\Scripts\\python\.exe$" } `
           | Select-Object -First 1
  if ($found) { return $found.FullName }

  throw "Venv python.exe not found under $venvRoot"
}

function Need-Python {
  try { $null = python -c "import sys; assert sys.version_info[:2] >= (3,11)"; return $true }
  catch { return $false }
}

function Get-Token {
  if ($env:GITHUB_TOKEN) { return $env:GITHUB_TOKEN }
  Write-Host "If the repo is PRIVATE, paste a GitHub token (read access). Press Enter to skip for public repos:"
  $tok = Read-Host
  return $tok
}

if (-not (Need-Python)) { throw "Python 3.11+ not found on PATH. Install it, reopen PowerShell, then re-run." }

$root = Join-Path $env:LOCALAPPDATA "BUSCore"
$app  = Join-Path $root "app"
$tmp  = Join-Path $root "tmp"
$zip  = Join-Path $tmp  "repo.zip"
$venv = Join-Path $root "env"

New-Item -ItemType Directory -Force -Path $root,$tmp | Out-Null

# Build URLs
$apiZip = "https://api.github.com/repos/$Owner/$Repo/zipball/$Branch"
$pubZip = "https://github.com/$Owner/$Repo/archive/refs/heads/$Branch.zip"
$tok = Get-Token
$hdr = @{ "User-Agent"="BUSCore-Launcher" }
if ($tok) { $hdr["Authorization"] = "Bearer $tok" }

# Download ZIP
Write-Host "Downloading $Owner/$Repo ($Branch)..."
$downloadUrl = $pubZip
if ($tok) { $downloadUrl = $apiZip }
try {
  Invoke-WebRequest -Uri $downloadUrl -Headers $hdr -OutFile $zip
} catch {
  throw "Download failed. If the repo is private, set GITHUB_TOKEN or paste a token when prompted. $_"
}

# Unpack to app/
if (Test-Path $app) { Remove-Item $app -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $tmp -Force
# Find unpacked dir
$unpacked = Get-ChildItem $tmp | Where-Object { $_.PSIsContainer -and $_.Name -ne "app" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $unpacked) { throw "Unpack failed." }
Move-Item $unpacked.FullName $app -Force
Remove-Item $zip -Force

# Ensure venv
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
  Write-Host "Creating venv..."
  python -m venv $venv
}
$py = Resolve-VenvPython $venv
Write-Host "Using venv python: $py"

# Install deps
Write-Host "Installing dependencies..."
& "$py" -m pip install --upgrade pip
if (Test-Path (Join-Path $app "requirements.txt")) {
  & "$py" -m pip install -r (Join-Path $app "requirements.txt")
}
& "$py" -m pip install "pywin32>=306" "Send2Trash==1.8.2"
try { & "$py" -m pywin32_postinstall -install | Out-Null } catch { }

# Run
Push-Location $app
Write-Host "Starting BUS Core on http://127.0.0.1:$Port/ui"
Start-Process "http://127.0.0.1:$Port/ui"
& "$py" app.py serve --port $Port
Pop-Location
