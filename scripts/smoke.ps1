# SPDX-License-Identifier: AGPL-3.0-or-later
<#
.SYNOPSIS
  BUS Core smoke tests (SOT-compliant). Keep all smoke here (no pytest).
  Verifies items (definition-only), adjustments (+/- FIFO), recipes (PUT full doc),
  and manufacturing runs (validation, no oversold).
#>

param(
  [string]$BaseUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step($msg){ Write-Host "[SMOKE] $msg" -ForegroundColor Cyan }
function Write-Ok($msg){ Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Fail($msg){ Write-Host "  ✗ $msg" -ForegroundColor Red }

function Invoke-JsonPost($Url, $BodyObj) {
  $json = $BodyObj | ConvertTo-Json -Depth 10
  return Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json" -Body $json
}
function Invoke-JsonPut($Url, $BodyObj) {
  $json = $BodyObj | ConvertTo-Json -Depth 10
  return Invoke-RestMethod -Method Put -Uri $Url -ContentType "application/json" -Body $json
}
function TryInvoke { param([scriptblock]$Block)
  try { & $Block; return @{ ok=$true } } catch { return @{ ok=$false; err=$_ } }
}

# Session token (if required)
TryInvoke { Invoke-RestMethod -Method Get -Uri "$BaseUrl/session/token" } | Out-Null

$Failures = @()
function Assert-True($cond, $msg) {
  if ($cond) { Write-Ok $msg } else { Write-Fail $msg; $script:Failures += $msg }
}

# 1) Items: create (definition-only)
Write-Step "Items: create definition-only"
$itemA = Invoke-JsonPost "$BaseUrl/app/items" @{ name = "SMK-A" }
$itemB = Invoke-JsonPost "$BaseUrl/app/items" @{ name = "SMK-B" }
$itemC = Invoke-JsonPost "$BaseUrl/app/items" @{ name = "SMK-C" }
Assert-True ($itemA.id -gt 0 -and $itemB.id -gt 0 -and $itemC.id -gt 0) "Created items A/B/C"

# 2) Adjustments: + then - (no partials, no oversold)
Write-Step "Adjustments: + then - (FIFO, no oversold)"
$adj1 = Invoke-JsonPost "$BaseUrl/app/ledger/adjust" @{ item_id = $itemA.id; qty_change = 15 }
Assert-True ($adj1.ok -or $adj1 -eq $null) "+15 adjust OK"
$adj2 = Invoke-JsonPost "$BaseUrl/app/ledger/adjust" @{ item_id = $itemA.id; qty_change = -4 }
Assert-True ($adj2.ok -or $adj2 -eq $null) "-4 adjust OK"
$negTry = TryInvoke { Invoke-JsonPost "$BaseUrl/app/ledger/adjust" @{ item_id = $itemB.id; qty_change = -999 } }
Assert-True (-not $negTry.ok) "Negative adjust > on-hand returns 400"

# 3) Recipes: create + full PUT (single output, qty_required)
Write-Step "Recipes: create + PUT full document"
$recCreate = Invoke-JsonPost "$BaseUrl/app/recipes" @{
  name = "SMK Recipe B-from-A"
  output_item_id = $itemB.id
  output_qty = 1
  items = @(@{ item_id = $itemA.id; qty_required = 3; is_optional = $false })
}
Assert-True ($recCreate.id -gt 0) "Recipe created"

$recPut = Invoke-JsonPut "$BaseUrl/app/recipes/$($recCreate.id)" @{
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
Assert-True ($recPut.ok -eq $true) "Recipe PUT OK"

# 4) Manufacturing: success + shortage 400 + ad-hoc 400
Write-Step "Manufacturing: run success + shortage checks"
$runOk = Invoke-JsonPost "$BaseUrl/app/manufacturing/run" @{
  recipe_id = $recCreate.id
  output_qty = 2  # needs 6 of A (15-4 left => 11 available) → should pass
  notes = "smoke run ok"
}
Assert-True ($runOk.status -eq "completed") "Run completed"

$runBadTry = TryInvoke { Invoke-JsonPost "$BaseUrl/app/manufacturing/run" @{ recipe_id = $recCreate.id; output_qty = 999 } }
Assert-True (-not $runBadTry.ok) "Run with insufficient stock returns 400"
if (-not $runBadTry.ok) {
  $msg = $runBadTry.err.ErrorDetails.Message
  Assert-True ($msg -match "failed_insufficient_stock" -or $msg -match "shortages") "Shortage payload contains shortages"
}

$adhocBadTry = TryInvoke {
  Invoke-JsonPost "$BaseUrl/app/manufacturing/run" @{
    output_item_id = $itemC.id
    output_qty = 1
    components = @(@{ item_id = $itemB.id; qty_required = 999 })
  }
}
Assert-True (-not $adhocBadTry.ok) "Ad-hoc run without stock fails 400"

Write-Step "Smoke complete"
if ($Failures.Count -gt 0) {
  Write-Host "`nFailures:" -ForegroundColor Red
  $Failures | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
  exit 1
} else {
  Write-Host "`nAll smoke checks passed." -ForegroundColor Green
  exit 0
}
