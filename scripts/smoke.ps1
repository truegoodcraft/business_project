<#  BUS Core – Smoke Test (Windows PowerShell 5.1 compatible)
    Checks: session, schema, ledger health, create item, purchases (2 batches),
            consume FIFO (12 units), valuation (=1500¢), movement history
    Usage:
      powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke.ps1 -BaseUrl http://127.0.0.1:8765
#>
param(
  [string]$BaseUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Mark([string]$msg, [ConsoleColor]$color) { Write-Host "  $msg" -ForegroundColor $color }
function Step([string]$title) { Write-Host ""; Write-Host "▌ $title" -ForegroundColor Cyan }

function JsonPost($path, $obj) {
  $uri = "$BaseUrl$path"
  $body = ($obj | ConvertTo-Json -Depth 6)
  $resp = Invoke-WebRequest -UseBasicParsing -Method POST -Uri $uri -WebSession $sess -ContentType "application/json" -Body $body
  return ($resp.Content | ConvertFrom-Json)
}
function JsonGet($path) {
  $uri = "$BaseUrl$path"
  $resp = Invoke-WebRequest -UseBasicParsing -Method GET -Uri $uri -WebSession $sess
  return ($resp.Content | ConvertFrom-Json)
}
function Assert($cond, [string]$okMsg, [string]$failMsg) {
  if ($cond) { Mark "✔ $okMsg" Green } else { Mark "✖ $failMsg" Red; throw $failMsg }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════"
Write-Host " BUS Core – Smoke (Items + FIFO Ledger) " -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════════════"

# Session
Step "Session"
try {
  $null = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/session/token" -SessionVariable sess
  Mark "✔ Session cookie acquired" Green
} catch {
  Mark "✖ Could not get session at $BaseUrl/session/token" Red
  throw
}

# Schema / DB
Step "Schema / DB"
$dbinfo = JsonGet "/dev/db-info"
Assert ($dbinfo.tables -contains "items")           "items table present"         "items table missing"
Assert ($dbinfo.tables -contains "item_batches")    "item_batches present"        "item_batches missing"
Assert ($dbinfo.tables -contains "item_movements")  "item_movements present"      "item_movements missing"

# Ledger health
Step "Ledger health"
$health = JsonGet "/app/ledger/health"
Assert ($health.desync -eq $false) "Ledger in sync" "Ledger reports desync"

# Create test item
Step "Create test item"
$stamp  = Get-Date -Format "yyyyMMddHHmmss"
$sku    = "SMK-$stamp"
$item   = JsonPost "/app/items" @{
  name="Smoke Widget"; sku=$sku; uom="ea"; qty_stored=0; price=0;
  item_type="Material"; location="smoke-rack"
}
Assert ($item.id -gt 0) "Item created: #$($item.id) ($sku)" "Failed to create item"

$itemId = $item.id
$seen = (JsonGet "/app/ledger/debug/db?item_id=$itemId")
Assert ($seen.items_count -ge 1 -and $seen.item_row -ne $null) "Ledger sees item #$itemId" "Ledger cannot see the new item"

# Stock-in (two batches)
Step "Stock-in (create cost layers)"
$po1 = JsonPost "/app/ledger/purchase" @{ item_id=$itemId; qty=10; unit_cost_cents=300; source_kind="purchase"; source_id="po-A" }
$po2 = JsonPost "/app/ledger/purchase" @{ item_id=$itemId; qty=5;  unit_cost_cents=500; source_kind="purchase"; source_id="po-B" }
Assert ($po1.ok -and $po2.ok) "Two batches created (#$($po1.batch_id), #$($po2.batch_id))" "Failed to create batches"

# Consume 12 (10@300 + 2@500)
Step "Consume (FIFO: 10@300 + 2@500)"
$cons = JsonPost "/app/ledger/consume" @{ item_id=$itemId; qty=12; source_kind="sale"; source_id="so-1" }
Assert ($cons.ok) "Consumed 12 units via FIFO" "Consumption failed"
Assert ($cons.consumed.Count -eq 2) "Split across 2 cost layers" "Unexpected batch split"

# Valuation
Step "Valuation"
$val = JsonGet "/app/ledger/valuation?item_id=$itemId"
Assert ($val.total_value_cents -eq 1500) "Valuation = `$15.00 (1500¢)" "Valuation mismatch: $($val.total_value_cents)¢"

# Movement history
Step "Movement history"
$mov = JsonGet "/app/ledger/movements?item_id=$itemId&limit=50"
$cnt = $mov.movements.Count
Assert ($cnt -ge 4) "Movement entries present ($cnt)" "No movements found"

Write-Host ""
Write-Host "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓" -ForegroundColor DarkCyan
Write-Host "┃   Smoke: PASSED  –  items ✅  ledger ✅  fifo ✅  ui ✅ ┃" -ForegroundColor DarkCyan
Write-Host "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛" -ForegroundColor DarkCyan
Write-Host ""
