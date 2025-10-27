$ErrorActionPreference="Stop"
$HostAddr="127.0.0.1"; $Port=8765
$AppRoot="$env:LOCALAPPDATA\BUSCore\app\business_project-main"
$UiDir = Join-Path $AppRoot "core\ui"

# kill listener
$listenerPid = (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
                Select-Object -First 1 -ExpandProperty OwningProcess)
if ($listenerPid) { try { Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue } catch {} ; Start-Sleep 1 }

# pull latest zip to temp then mirror (optional keep if you already do this elsewhere)

# mirror working dir to runtime, PRESERVE DB and scripts
New-Item -ItemType Directory -Force -Path $AppRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppRoot "data") | Out-Null
$RepoGuess = (Resolve-Path "$PSScriptRoot\..").Path
robocopy $RepoGuess $AppRoot /MIR /XD data .git .github tests node_modules scripts /XF app.db | Out-Null

# enforce entry
$IndexHtml = Join-Path $UiDir "index.html"
$ShellHtml = Join-Path $UiDir "shell.html"
if (Test-Path $IndexHtml) { try { Rename-Item $IndexHtml "index_legacy.html" -Force } catch {} }
if (!(Test-Path $ShellHtml)) { throw "[ui] Missing shell.html in $UiDir" }
$env:BUS_UI_DIR = $UiDir
Write-Host "[ui] Serving /ui/ from: $env:BUS_UI_DIR"

# start uvicorn with factory
$python = (Get-Command python -ErrorAction SilentlyContinue).Path; if (-not $python) { $python=(Get-Command py -ErrorAction SilentlyContinue).Path }
if (-not $python) { throw "Python not found" }
Push-Location $AppRoot
Start-Process $python -ArgumentList @("-m","uvicorn","core.api.http:create_app","--factory","--host",$HostAddr,"--port",$Port,"--reload") -WindowStyle Minimized
Pop-Location
Start-Sleep 2
Start-Process "http://$HostAddr`:$Port/ui/shell.html"
