# SPDX-License-Identifier: AGPL-3.0-or-later
# scripts/smoke.ps1
# Quick, reproducible smoke that proves inventory FIFO works end-to-end.
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke.ps1 -BindHost 127.0.0.1 -Port 8765 -DbPath data\app.db -Clean

param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8765,
  [string]$DbPath = "data/app.db",
  [switch]$Clean,
  [switch]$Quiet
)

function Say([string]$Text, [string]$Color = "White") {
  if (-not $Quiet) { Write-Host $Text -ForegroundColor $Color }
}
function Tick([string]$Text) { Say ("  [√] " + $Text) "Green" }
function Boom([string]$Text) { Say ("  [x] " + $Text) "Red" }

$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")
Push-Location $repoRoot

# Helpers ----------------------------------------------------------
function Invoke-Json {
  param([string]$Method,[string]$Url,[object]$Body = $null,[Microsoft.PowerShell.Commands.WebRequestSession]$Session = $null)
  $params = @{
    Uri = $Url
    Method = $Method
    UseBasicParsing = $true
  }
  if ($Session) { $params.WebSession = $Session }
  if ($Body -ne $null) {
    $params.ContentType = "application/json"
    $params.Body = ($Body | ConvertTo-Json -Compress)
  }
  return Invoke-WebRequest @params
}
function Parse-Json([string]$s) {
  if ([string]::IsNullOrWhiteSpace($s)) { return $null }
  return $s | ConvertFrom-Json
}
# -----------------------------------------------------------------

# Enable dev context for smoke validation; server must be started with matching env to expose dev-only routes
$env:BUS_DEV = "1"

try {
  # Resolve DB path for info & optional cleanup
  if (-not (Split-Path -IsAbsolute $DbPath)) {
    $DbPath = Join-Path $PWD.Path $DbPath
  }
  if ($Clean -and (Test-Path $DbPath)) {
    Remove-Item -Force $DbPath
    Say ("[smoke] Removed existing DB: {0}" -f $DbPath) "DarkGray"
  }

  $base = "http://{0}:{1}" -f $BindHost,$Port
  Say ("[smoke] Target: {0}" -f $base) "Cyan"

  # Start cookie session like the UI
  $resp = Invoke-WebRequest -UseBasicParsing -Uri "$base/session/token" -SessionVariable sess
  if ($resp.StatusCode -ne 200) { throw "Failed to start session; status $($resp.StatusCode)" }
  Tick "Session: OK (cookie)"

  # Create a unique item
  $sku  = "SMOKE-" + [Guid]::NewGuid().ToString("N").Substring(0,8)
  $item = @{
    name="Widget A"
    sku=$sku
    uom="ea"
    qty_stored=0
    price=0
    item_type="Material"
    location="rack-1"
  }
  $r = Invoke-Json -Method POST -Url "$base/app/items" -Body $item -Session $sess
  if ($r.StatusCode -ne 200 -and $r.StatusCode -ne 201) { throw "Create item failed ($($r.StatusCode))" }
  $newItem = Parse-Json $r.Content
  $itemId = $newItem.id
  if (-not $itemId) {
    # fallback: list and find by sku
    $li = Invoke-WebRequest -UseBasicParsing -Uri "$base/app/items" -WebSession $sess
    $arr = Parse-Json $li.Content
    $itemId = ($arr | Where-Object { $_.sku -eq $sku } | Select-Object -First 1).id
  }
  if (-not $itemId) { throw "Unable to determine item id" }
  Tick ("Item created: id={0}, sku={1}" -f $itemId,$sku)

  # Stock in two cost layers (FIFO test setup)
  $r1 = Invoke-Json -Method POST -Url "$base/app/ledger/purchase" -Body @{ item_id=$itemId; qty=10; unit_cost_cents=300; source_kind="purchase"; source_id="po-1001" } -Session $sess
  if ($r1.StatusCode -ne 200) { throw "Purchase #1 failed ($($r1.StatusCode)) -> $($r1.Content)" }
  $r2 = Invoke-Json -Method POST -Url "$base/app/ledger/purchase" -Body @{ item_id=$itemId; qty=5;  unit_cost_cents=500; source_kind="purchase"; source_id="po-1002" } -Session $sess
  if ($r2.StatusCode -ne 200) { throw "Purchase #2 failed ($($r2.StatusCode)) -> $($r2.Content)" }
  Tick "Purchases: 10@300 + 5@500"

  # Consume 12 -> expect remaining 3@500 => valuation 1500
  $rc = Invoke-Json -Method POST -Url "$base/app/ledger/consume" -Body @{ item_id=$itemId; qty=12; source_kind="sale"; source_id="so-2001" } -Session $sess
  if ($rc.StatusCode -ne 200) { throw "Consume failed ($($rc.StatusCode)) -> $($rc.Content)" }
  Tick "Consumed: 12 (FIFO)"

  # Verify valuation == 1500 cents
  $rv = Invoke-WebRequest -UseBasicParsing -Uri "$base/app/ledger/valuation?item_id=$itemId" -WebSession $sess
  if ($rv.StatusCode -ne 200) { throw "Valuation failed ($($rv.StatusCode))" }
  $val = (Parse-Json $rv.Content).total_value_cents
  if ($val -ne 1500) {
    Boom ("Valuation unexpected: got {0}, expected 1500" -f $val)
    throw "Valuation mismatch"
  }
  Tick "Valuation: OK (1500¢)"

  # Dev/detail gating checks (pass if 200 in dev mode or clean 404/403 when gated)
  function Test-GatedEndpoint {
    param(
      [string]$Url,
      [string]$Label
    )
    $resp = $null
    try {
      $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -WebSession $sess -ErrorAction Stop
    } catch {
      $resp = $_.Exception.Response
    }
    $status = if ($resp) { $resp.StatusCode } else { $null }
    if ($status -eq 200) {
      Tick ("{0}: available (dev mode)" -f $Label)
      return
    }
    if (-not $status) { $status = "(no response)" }
    if ($status -eq 404 -or $status -eq 403) {
      Tick ("{0}: gated ({1})" -f $Label,$status)
      return
    }
    Boom ("{0}: unexpected status {1}" -f $Label,$status)
    throw "Gating check failed"
  }

  Test-GatedEndpoint "$base/health/detailed" "Health detail"
  Test-GatedEndpoint "$base/dev/db-info" "Dev DB info"

  # Movements sanity
  $rm = Invoke-WebRequest -UseBasicParsing -Uri "$base/app/ledger/movements?item_id=$itemId&limit=50" -WebSession $sess
  if ($rm.StatusCode -ne 200) { throw "Movements failed ($($rm.StatusCode))" }
  $movs = (Parse-Json $rm.Content).movements
  $count = ($movs | Measure-Object).Count
  if ($count -lt 4) {
    Boom ("Movements too few: {0}" -f $count)
    throw "Movement history incomplete"
  }
  Tick ("Movements: OK ({0} rows)" -f $count)

  # Pretty finale
  Say "" "White"
  Say "All smoke checks passed." "Green"
  Say ("DB: {0}" -f $DbPath) "DarkGray"
  Say ("Item: id={0}, sku={1}" -f $itemId,$sku) "DarkGray"

} catch {
  Say ""
  Boom ("Smoke FAILED: {0}" -f $_)
  exit 1
} finally {
  if ($Clean) {
    # Optional reset: remove DB so the run is ephemeral when desired
    if (Test-Path $DbPath) {
      Remove-Item -Force $DbPath
      Say ("[smoke] Cleaned DB: {0}" -f $DbPath) "DarkGray"
    }
  }
  Pop-Location
}
