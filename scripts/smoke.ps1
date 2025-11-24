<# 
  scripts/smoke.ps1 — consolidated smoke (PowerShell 5.1+ safe)
  No third-party downloads. Uses HTTP API CRUD (not UI automation).
  Starts server in its own window if absent and KEEPS that window.
  Can trigger an in-place restart without closing the window (uvicorn reloader).
#>

$ErrorActionPreference = 'Stop'
$host.UI.RawUI.WindowTitle = "BUS Core — smoke.ps1"

function New-Rand      { [guid]::NewGuid().ToString('N').Substring(0,8) }
function Json          { param($o) return ($o | ConvertTo-Json -Depth 8 -Compress) }
function Join-Url      { param([string]$base,[string]$path) return ($base.TrimEnd('/') + '/' + $path.TrimStart('/')) }

# ------------------------ Config ------------------------
$BaseUrl = $env:BUSCORE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) { $BaseUrl = 'http://127.0.0.1:8765' }  # API root
$ShellUrl = Join-Url $BaseUrl '/ui/shell.html'
$HealthUrl = Join-Url $BaseUrl '/health'
$ItemsUrl  = Join-Url $BaseUrl '/app/items'
$TokenUrl  = Join-Url $BaseUrl '/session/token'
$DbPath    = Join-Path $env:LOCALAPPDATA 'BUSCore\app\app.db'

Write-Host "[smoke] App DB path: $DbPath"

# ------------------------ Stage A: server readiness ------------------------
Write-Host "[smoke] === Stage A: server readiness ==="

# Start server in its OWN WINDOW if not running; KEEP that window
$serverProc = Get-Process -Name 'BUSCore' -ErrorAction SilentlyContinue
$startedBySmoke = $false
if (-not $serverProc) {
  $devBootstrap = Join-Path $PSScriptRoot 'dev_bootstrap.ps1'
  $devScript    = (Test-Path $devBootstrap) ? $devBootstrap : (Join-Path $PSScriptRoot 'dev.ps1')
  if (-not (Test-Path $devScript)) { throw "Dev script not found: $devScript" }
  Write-Host "[smoke] Starting server in its own window..." -ForegroundColor Yellow
  # /k keeps window; -NoExit keeps PowerShell window open
  Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -NoExit -File `"$devScript`"" -WindowStyle Normal -Verb Open
  $startedBySmoke = $true
} else {
  Write-Host "[smoke] Server already running" -ForegroundColor Green
}

# Wait for health (max 60s)
$ready = $false
foreach ($i in 1..60) {
  try {
    $r = Invoke-WebRequest $HealthUrl -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { $ready = $true; break }
  } catch { Start-Sleep -Milliseconds 500 }
}
if (-not $ready) { throw "Server not ready at $HealthUrl" }
Write-Host "[smoke] Server healthy" -ForegroundColor Green

# ------------------------ Stage B: DB hygiene & baseline ------------------------
Write-Host "[smoke] === Stage B: DB hygiene (no sqlite provider needed) ==="
if (-not (Test-Path $DbPath)) { throw "DB missing: $DbPath" }
$beforeSize = (Get-Item $DbPath).Length
$beforeTime = (Get-Item $DbPath).LastWriteTimeUtc
if ($beforeSize -lt 1024) { throw "DB suspiciously small ($beforeSize bytes)" }

$ts     = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path (Split-Path $DbPath) ("app.smokebackup.$ts.db")
Copy-Item $DbPath $backup -Force
Write-Host "[smoke] Backup created: $backup" -ForegroundColor Green

# ------------------------ Helpers: API ------------------------
function Get-ApiToken {
  $r = Invoke-RestMethod -Method GET -Uri $TokenUrl -TimeoutSec 10
  if (-not $r.token) { throw "Token endpoint returned no token" }
  return $r.token
}
function Api-Get  { param($url,$tok) Invoke-RestMethod -Method GET  -Uri $url -Headers @{Authorization="Bearer $tok"} -TimeoutSec 15 }
function Api-Post { param($url,$tok,$body) Invoke-RestMethod -Method POST -Uri $url -Headers @{Authorization="Bearer $tok"; 'Content-Type'='application/json'} -Body (Json $body) -TimeoutSec 15 }
function Api-Put  { param($url,$tok,$body) Invoke-RestMethod -Method PUT  -Uri $url -Headers @{Authorization="Bearer $tok"; 'Content-Type'='application/json'} -Body (Json $body) -TimeoutSec 15 }
function Api-Del  { param($url,$tok)       Invoke-RestMethod -Method DELETE -Uri $url -Headers @{Authorization="Bearer $tok"} -TimeoutSec 15 }

# Optional: in-place server restart that PRESERVES the console window (touches a file to bump uvicorn reloader)
function Invoke-ServerReload {
  $touch = Join-Path $PSScriptRoot "__smoke_reload__.$([guid]::NewGuid().ToString('N')).tmp"
  Set-Content -Path $touch -Value (Get-Date).ToString('o')
  Start-Sleep -Milliseconds 200
  Remove-Item -Force $touch -ErrorAction SilentlyContinue
  # Wait for health again (quick)
  foreach ($i in 1..20) {
    try {
      $r = Invoke-WebRequest $HealthUrl -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { return }
    } catch { Start-Sleep -Milliseconds 250 }
  }
  throw "Server reload did not complete"
}

# ------------------------ Stage C: API CRUD for Items ------------------------
Write-Host "[smoke] === Stage C: API CRUD — Items ==="
$tok = Get-ApiToken

# Create
$rand = New-Rand
$name = "SMK_Item_$rand"
$sku  = "SMK_SKU_$rand"
$loc  = "SMK_LOC_$rand"
$create = @{
  name      = $name
  sku       = $sku
  item_type = "material"
  qty       = 2.5
  unit      = "EA"
  price     = 12.34
  notes     = "smoke notes"
  location  = $loc
}
$created = Api-Post $ItemsUrl $tok $create
if (-not $created.id) { throw "Create returned no id" }
Write-Host "[smoke] Created item id=$($created.id)"

# Read/verify appears in list
$items = Api-Get $ItemsUrl $tok
$got   = @($items | Where-Object { $_.id -eq $created.id })
if ($got.Count -ne 1) { throw "Created item not in list" }
if ($got[0].location -ne $loc) { throw "Location mismatch after create" }

# Update
$upd = @{
  name      = $name
  sku       = $sku
  item_type = "material"
  qty       = 3
  unit      = "EA"
  price     = 2
  notes     = "smoke notes + edited"
  location  = "${loc}_EDIT"
}
$null = Api-Put (Join-Url $ItemsUrl "/$($created.id)") $tok $upd

# Verify update
$items2 = Api-Get $ItemsUrl $tok
$got2   = @($items2 | Where-Object { $_.id -eq $created.id })
if ($got2.Count -ne 1) { throw "Updated item missing" }
if ($got2[0].qty -ne 3) { throw "Qty not updated" }
if ($got2[0].price -ne 2) { throw "Price not updated" }
if ($got2[0].location -ne "${loc}_EDIT") { throw "Location not updated" }

# Optional: prove in-place restart works while KEEPING the dev window
if ($env:SMOKE_RELOAD -eq '1') {
  Write-Host "[smoke] Triggering in-place server reload..." -ForegroundColor Yellow
  Invoke-ServerReload
  # quick re-check
  $items3 = Api-Get $ItemsUrl $tok
  $got3   = @($items3 | Where-Object { $_.id -eq $created.id })
  if ($got3.Count -ne 1) { throw "Item missing after reload" }
}

# Delete
$null = Api-Del (Join-Url $ItemsUrl "/$($created.id)") $tok
$items4 = Api-Get $ItemsUrl $tok
$gone   = @($items4 | Where-Object { $_.id -eq $created.id })
if ($gone.Count -ne 0) { throw "Delete failed — item still present" }
Write-Host "[smoke] CRUD ok" -ForegroundColor Green

# ------------------------ Stage D: DB persistence observed ------------------------
Start-Sleep -Milliseconds 300
$afterTime = (Get-Item $DbPath).LastWriteTimeUtc
if ($afterTime -le $beforeTime) { throw "DB LastWriteTime did not advance after CRUD" }
Write-Host "[smoke] DB persistence observed (mtime advanced)" -ForegroundColor Green

Write-Host "`n[smoke] SMOKE PASS" -ForegroundColor Cyan
exit 0
