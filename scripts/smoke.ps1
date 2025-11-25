<# 
  scripts/smoke.ps1 — isolated smoke:
    - Starts its OWN server on a FREE port in a TEMP app data root (separate DB).
    - Exercises API CRUD for Items (no extra downloads).
    - Verifies DB persistence (mtime advances).
    - Shuts its server down and deletes the temp app data on success/failure.

  Requirements: PowerShell 5.1+ (works in pwsh too). No Node/.NET SQLite/sqlite3.exe needed.
#>

$ErrorActionPreference = 'Stop'

function New-Rand { [guid]::NewGuid().ToString('N').Substring(0,8) }
function Json { param($o) $o | ConvertTo-Json -Depth 8 -Compress }
function Join-Url { param([string]$base,[string]$path) $base.TrimEnd('/') + '/' + $path.TrimStart('/') }
function Get-FreeTcpPort {
  $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback,0)
  $l.Start(); $p = $l.LocalEndpoint.Port; $l.Stop(); return $p
}

# ---------- Prepare isolated environment (temp LOCALAPPDATA + free port) ----------
$Port = Get-FreeTcpPort
$IsoRoot = Join-Path $env:TEMP ("BUSCore_Smoke_" + (New-Rand))
$null = New-Item -ItemType Directory -Force -Path (Join-Path $IsoRoot 'BUSCore\app') | Out-Null

# Child server environment (only for the server window)
$ChildEnvCmd = @"
`$env:LOCALAPPDATA = '$IsoRoot'
`$env:BUSCORE_PORT = '$Port'
`$env:BUSCORE_SMOKE = '1'
"@.Trim()

# URLs & DB path for THIS smoke run
$BaseUrl  = "http://127.0.0.1:$Port"
$HealthUrl= Join-Url $BaseUrl '/health'
$ItemsUrl = Join-Url $BaseUrl '/app/items'
$TokenUrl = Join-Url $BaseUrl '/session/token'
$DbPath   = Join-Path $IsoRoot 'BUSCore\app\app.db'

Write-Host "[smoke] Isolated app data root: $IsoRoot"
Write-Host "[smoke] Smoke server port: $Port"
Write-Host "[smoke] Smoke app DB path: $DbPath"

# ---------- Start our OWN server in its own window (kept while smoke runs) ----------
$devBootstrap = Join-Path $PSScriptRoot 'dev_bootstrap.ps1'
$devScript    = (Test-Path $devBootstrap) ? $devBootstrap : (Join-Path $PSScriptRoot 'dev.ps1')
if (-not (Test-Path $devScript)) { throw "Dev script not found: $devScript" }

Write-Host "[smoke] Launching dedicated server window..." -ForegroundColor Yellow
# Use -Command to inject env vars in the child session, then invoke the dev script; -NoExit keeps the window open
$devScriptFull = (Resolve-Path $devScript).Path
$cmd = "$ChildEnvCmd; & `"$devScriptFull`""
$ServerProc = Start-Process powershell.exe -PassThru -WindowStyle Normal `
  -ArgumentList "-NoProfile -ExecutionPolicy Bypass -NoExit -Command $cmd"

# ---------- Wait for health of OUR server (max 60s) ----------
$ready = $false
foreach ($i in 1..60) {
  try { $r = Invoke-WebRequest $HealthUrl -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { $ready = $true; break } }
  catch { Start-Sleep -Milliseconds 500 }
}
if (-not $ready) { throw "Smoke server not ready on $HealthUrl" }
Write-Host "[smoke] Smoke server healthy" -ForegroundColor Green

# ---------- Stage A: DB baseline & backup ----------
$ts     = Get-Date -Format "yyyyMMdd_HHmmss"
$beforeTime = (Test-Path $DbPath) ? (Get-Item $DbPath).LastWriteTimeUtc : (Get-Date).AddSeconds(-1)
$backup = Join-Path (Join-Path $IsoRoot 'BUSCore\app') ("app.smokebackup.$ts.db")
if (Test-Path $DbPath) { Copy-Item $DbPath $backup -Force; Write-Host "[smoke] Backup created: $backup" -ForegroundColor Green }

# ---------- Helpers: API ----------
function Get-ApiToken {
  $r = Invoke-RestMethod -Method GET -Uri $TokenUrl -TimeoutSec 10
  if (-not $r.token) { throw "Token endpoint returned no token" }
  return $r.token
}
function Api-Get  { param($url,$tok) Invoke-RestMethod -Method GET    -Uri $url -Headers @{Authorization="Bearer $tok"} -TimeoutSec 15 }
function Api-Post { param($url,$tok,$body) Invoke-RestMethod -Method POST   -Uri $url -Headers @{Authorization="Bearer $tok"; 'Content-Type'='application/json'} -Body (Json $body) -TimeoutSec 15 }
function Api-Put  { param($url,$tok,$body) Invoke-RestMethod -Method PUT    -Uri $url -Headers @{Authorization="Bearer $tok"; 'Content-Type'='application/json'} -Body (Json $body) -TimeoutSec 15 }
function Api-Del  { param($url,$tok)       Invoke-RestMethod -Method DELETE -Uri $url -Headers @{Authorization="Bearer $tok"} -TimeoutSec 15 }

# ---------- Stage B: API CRUD against OUR server ----------
Write-Host "[smoke] === Stage B: API CRUD — Items (isolated) ==="
$tok  = Get-ApiToken
$rand = New-Rand
$name = "SMK_Item_$rand"
$sku  = "SMK_SKU_$rand"
$loc  = "SMK_LOC_$rand"

# Create
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

# List & verify
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
$null = Api-Put ($ItemsUrl + "/$($created.id)") $tok $upd

# Verify update
$items2 = Api-Get $ItemsUrl $tok
$got2   = @($items2 | Where-Object { $_.id -eq $created.id })
if ($got2.Count -ne 1) { throw "Updated item missing" }
if ($got2[0].qty -ne 3) { throw "Qty not updated" }
if ($got2[0].price -ne 2) { throw "Price not updated" }
if ($got2[0].location -ne "${loc}_EDIT") { throw "Location not updated" }

# Delete
$null = Api-Del ($ItemsUrl + "/$($created.id)") $tok
$items4 = Api-Get $ItemsUrl $tok
$gone   = @($items4 | Where-Object { $_.id -eq $created.id })
if ($gone.Count -ne 0) { throw "Delete failed — item still present" }
Write-Host "[smoke] CRUD ok" -ForegroundColor Green

# ---------- Stage C: DB persistence (mtime must advance) ----------
Start-Sleep -Milliseconds 300
if (-not (Test-Path $DbPath)) { throw "DB missing after CRUD: $DbPath" }
$afterTime = (Get-Item $DbPath).LastWriteTimeUtc
if ($afterTime -le $beforeTime) { throw "DB LastWriteTime did not advance after CRUD" }
Write-Host "[smoke] DB persistence observed (mtime advanced)" -ForegroundColor Green

# ---------- Teardown: stop OUR server and clean isolated data ----------
function Stop-ByPort($p){
  try {
    $owning = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($owning) { Stop-Process -Id $owning -Force -ErrorAction SilentlyContinue }
  } catch {}
}
if ($ServerProc -and -not $ServerProc.HasExited) { try { Stop-Process -Id $ServerProc.Id -Force -ErrorAction SilentlyContinue } catch {} }
Stop-ByPort -p $Port

# Leave backup but remove working DB (optional). Comment out next line if you want to keep it.
try { Remove-Item -Recurse -Force $IsoRoot -ErrorAction SilentlyContinue } catch {}

Write-Host "`n[smoke] SMOKE PASS (isolated)" -ForegroundColor Cyan
exit 0
