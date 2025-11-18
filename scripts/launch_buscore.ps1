# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

$ErrorActionPreference="Stop"
$HostAddr="127.0.0.1"; $Port=8765
$AppRoot="$env:LOCALAPPDATA\BUSCore\app\tgc-bus-core"
$UiDir = Join-Path $AppRoot "core\ui"
$BcRoot = Join-Path $env:LOCALAPPDATA 'BUSCore'
$null = New-Item -ItemType Directory -Force -Path $BcRoot
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BcRoot 'secrets')
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BcRoot 'state')

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
