# SPDX-License-Identifier: AGPL-3.0-or-later
#requires -Version 5.1
<#
.SYNOPSIS
  BUS Core smoke tests (SOT-compliant, ASCII-only to avoid parsing issues).
  Verifies: items (definition-only), adjustments (+/- FIFO), recipes (PUT full doc),
  and manufacturing runs (validation and no-oversold).

.USAGE
  pwsh -NoProfile -File scripts/smoke.ps1 -BaseUrl http://127.0.0.1:8765
#>

param(
  [string]$BaseUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# -----------------------------
# Helpers (ASCII-only output)
# -----------------------------
function Write-Step { param([string]$Msg) Write-Host "[SMOKE] $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg) Write-Host "  OK  $Msg" -ForegroundColor Green }
function Write-Fail { param([string]$Msg) Write-Host "  ERR $Msg" -ForegroundColor Red }

# A single session object to persist cookies (Set-Cookie from /session/token)
$script:Session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

function Invoke-JsonPost {
  param([string]$Url, [hashtable]$BodyObj)
  $json = $BodyObj | ConvertTo-Json -Depth 10
  return Invoke-RestMethod -Method Post -Uri $Url -WebSession $script:Session -ContentType "application/json" -Body $json
}
function Invoke-JsonPut {
  param([string]$Url, [hashtable]$BodyObj)
  $json = $BodyObj | ConvertTo-Json -Depth 10
  return Invoke-RestMethod -Method Put -Uri $Url -WebSession $script:Session -ContentType "application/json" -Body $json
}
function TryInvoke {
  param([scriptblock]$Block)
  try { & $Block; return @{ ok = $true } }
  catch { return @{ ok = $false; err = $_ } }
}

# Establish session: call /session/token to receive auth cookie for this session
# Note: We reuse the same $script:Session in all subsequent calls so cookies are sent.
TryInvoke { Invoke-RestMethod -Method Get -Uri ($BaseUrl + "/session/token") -WebSession $script:Session } | Out-Null

# Precheck: ensure /app/ledger/adjust exists before running deeper smoke steps
try {
  $openapi = Invoke-RestMethod -Method Get -Uri "$BaseUrl/openapi.json"
  $hasAdjust = $false
  foreach ($k in $openapi.paths.PSObject.Properties.Name) {
    if ($k -eq "/app/ledger/adjust") { $hasAdjust = $true; break }
  }
  if (-not $hasAdjust) {
    Write-Host "[SMOKE] FATAL: /app/ledger/adjust not found in OpenAPI. Present /app/ledger paths:" -ForegroundColor Red
    foreach ($k in $openapi.paths.PSObject.Properties.Name) {
      if ($k -like "/app/ledger/*") { Write-Host "  - $k" -ForegroundColor Red }
    }
    throw "ledger.adjust route missing"
  }
} catch {
  throw
}

$Failures = @()
function Assert-True {
  param([bool]$Cond, [string]$Msg)
  if ($Cond) { Write-Ok $Msg } else { Write-Fail $Msg; $script:Failures += $Msg }
}

# -----------------------------
# 1) Items: create (definition-only)
# -----------------------------
Write-Step "Items: create definition-only"
$itemA = Invoke-JsonPost ($BaseUrl + "/app/items") @{ name = "SMK-A" }
$itemB = Invoke-JsonPost ($BaseUrl + "/app/items") @{ name = "SMK-B" }
$itemC = Invoke-JsonPost ($BaseUrl + "/app/items") @{ name = "SMK-C" }
Assert-True ((($itemA.id -as [int]) -gt 0) -and (($itemB.id -as [int]) -gt 0) -and (($itemC.id -as [int]) -gt 0)) "Created items A/B/C"

# -----------------------------
# 2) Adjustments: positive and negative (FIFO, no oversold)
# -----------------------------
Write-Step "Adjustments: positive and negative (FIFO, no oversold)"
$adj1 = Invoke-JsonPost ($BaseUrl + "/app/ledger/adjust") @{ item_id = $itemA.id; qty_change = 15 }
Assert-True ($null -ne $adj1) "Positive adjust +15 on A accepted"

$adj2 = Invoke-JsonPost ($BaseUrl + "/app/ledger/adjust") @{ item_id = $itemA.id; qty_change = -4 }
Assert-True ($null -ne $adj2) "Negative adjust -4 on A accepted"

$negTry = TryInvoke { Invoke-JsonPost ($BaseUrl + "/app/ledger/adjust") @{ item_id = $itemB.id; qty_change = -999 } }
Assert-True (-not $negTry.ok) "Negative adjust larger than on-hand returns 400"

# -----------------------------
# 3) Recipes: create + PUT full document
# -----------------------------
Write-Step "Recipes: create and PUT full document"
$recCreate = Invoke-JsonPost ($BaseUrl + "/app/recipes") @{
  name = "SMK Recipe B-from-A"
  output_item_id = $itemB.id
  output_qty = 1
  items = @(@{ item_id = $itemA.id; qty_required = 3; is_optional = $false })
}
Assert-True ((($recCreate.id -as [int]) -gt 0)) "Recipe created"

$recPut = Invoke-JsonPut ($BaseUrl + "/app/recipes/$($recCreate.id)") @{
  id = $recCreate.id
  name = "SMK Recipe B-from-A (v2)"
  output_item_id = $itemB.id
  output_qty = 1
  is_archived = $false
  notes = "smoke"
  items = @(
    @{ item_id = $itemA.id; qty_required = 3; is_optional = $false; sort_order = 0 },
    @{ item_id = $itemC.id; qty_required = 1; is_optional = $true;  sort_order = 1 }
  )
}
Assert-True (($recPut.ok -eq $true)) "Recipe PUT OK"

# -----------------------------
# 4) Manufacturing: success and shortage 400; ad-hoc 400
# -----------------------------
Write-Step "Manufacturing: run success and shortage checks"

$runOk = Invoke-JsonPost ($BaseUrl + "/app/manufacturing/run") @{
  recipe_id = $recCreate.id
  output_qty = 2
  notes = "smoke run ok"
}
Assert-True (($runOk.status -eq "completed")) "Run completed"

$runBadTry = TryInvoke { Invoke-JsonPost ($BaseUrl + "/app/manufacturing/run") @{ recipe_id = $recCreate.id; output_qty = 999 } }
Assert-True (-not $runBadTry.ok) "Run with insufficient stock returns 400"
if (-not $runBadTry.ok) {
  $msg = ""
  if ($runBadTry.err -and $runBadTry.err.ErrorDetails -and $runBadTry.err.ErrorDetails.Message) {
    $msg = $runBadTry.err.ErrorDetails.Message
  }
  $hasShortage = ($msg -match "failed_insufficient_stock") -or ($msg -match "shortages")
  Assert-True $hasShortage "Shortage payload contains shortages"
}

$adhocBadTry = TryInvoke {
  Invoke-JsonPost ($BaseUrl + "/app/manufacturing/run") @{
    output_item_id = $itemC.id
    output_qty = 1
    components = @(@{ item_id = $itemB.id; qty_required = 999 })
  }
}
Assert-True (-not $adhocBadTry.ok) "Ad-hoc run without stock fails 400"

# -----------------------------
# Finish
# -----------------------------
Write-Step "Smoke complete"
if ($Failures.Count -gt 0) {
  Write-Host ""
  Write-Host "Failures:" -ForegroundColor Red
  foreach ($f in $Failures) { Write-Host (" - " + $f) -ForegroundColor Red }
  exit 1
} else {
  Write-Host ""
  Write-Host "All smoke checks passed." -ForegroundColor Green
  exit 0
}
