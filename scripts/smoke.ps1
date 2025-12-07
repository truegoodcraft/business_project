# SPDX-License-Identifier: AGPL-3.0-or-later
#requires -Version 5.1
<#
.SYNOPSIS
  BUS Core smoke tests (Milestone 0.8.8 Final).
  Verifies full system stability including error UX, journals, and restore.

.USAGE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke.ps1 -BaseUrl http://127.0.0.1:8765
#>

param(
  [string]$BaseUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "BUS Core Smoke Test (Milestone 0.8.8)"
Write-Host ("Target: {0}" -f $BaseUrl)
Write-Host "------------------------------------------------------------"

function Info { param([string]$m) Write-Host ("  [INFO] {0}" -f $m) -ForegroundColor DarkCyan }
function Pass { param([string]$m) Write-Host ("  [PASS] {0}" -f $m) -ForegroundColor Green }
function Fail { param([string]$m) Write-Host ("  [FAIL] {0}" -f $m) -ForegroundColor Red }
function Step { param([string]$m) Write-Host ""; Write-Host $m -ForegroundColor Cyan }

$script:Session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

function Invoke-Json {
  param([string]$Method, [string]$Url, $BodyObj)
  $args = @{ Method=$Method; Uri=$Url; WebSession=$script:Session }
  if ($PSBoundParameters.ContainsKey('BodyObj') -and $null -ne $BodyObj) {
    $args['ContentType'] = 'application/json'
    $args['Body'] = ($BodyObj | ConvertTo-Json -Depth 10)
  }
  return Invoke-RestMethod @args
}

function Try-Invoke {
  param([scriptblock]$Block)
  try { $r = & $Block; return @{ ok=$true; resp=$r } }
  catch { return @{ ok=$false; err=$_ } }
}

# Helper to find item by ID from list if direct GET fails
function Get-ItemState {
    param($id)
    try {
        return Invoke-Json GET "$BaseUrl/app/items/$id" $null
    } catch {
        # Fallback to list
        $list = Invoke-Json GET "$BaseUrl/app/items" $null
        return $list | Where-Object { $_.id -eq $id }
    }
}

# 1. Session/Health
Step "1. Session & Health"
$tok = Invoke-RestMethod -Method Get -Uri "$BaseUrl/session/token" -WebSession $script:Session
if ($tok) { Pass "Session token acquired" } else { Fail "No token"; exit 1 }

$health = Try-Invoke { Invoke-RestMethod -Method Get -Uri "$BaseUrl/health" -WebSession $script:Session }
if ($health.ok) { Pass "Health check OK" } else { Fail "Health check failed: $($health.err)"; exit 1 }


# 2. Inventory CRUD
Step "2. Inventory CRUD"
$itemA = Invoke-Json POST "$BaseUrl/app/items" @{ name = "SMK-A-Raw" }
$itemB = Invoke-Json POST "$BaseUrl/app/items" @{ name = "SMK-B-Raw" }
$itemC = Invoke-Json POST "$BaseUrl/app/items" @{ name = "SMK-C-Prod" }
if ($itemA.id -and $itemB.id -and $itemC.id) { Pass "Created Items A, B, C" } else { Fail "Create failed"; exit 1 }

$updA = Invoke-Json PUT "$BaseUrl/app/items/$($itemA.id)" @{ name = "SMK-A-Raw-Updated"; sku = "SKU-A" }
if ($updA.name -eq "SMK-A-Raw-Updated") { Pass "Updated Item A" } else { Fail "Update failed"; exit 1 }


# 3. Contacts
Step "3. Contacts"
$vendV = Invoke-Json POST "$BaseUrl/app/vendors" @{ name = "SMK-Vendor-V" }
if ($vendV.id) { Pass "Created Vendor V" } else { Fail "Create Vendor failed"; exit 1 }

# Link Item A to Vendor V (PUT item with vendor_id)
$link = Invoke-Json PUT "$BaseUrl/app/items/$($itemA.id)" @{
  name = "SMK-A-Raw-Updated"
  sku = "SKU-A"
  vendor_id = $vendV.id
}
if ($link.vendor_id -eq $vendV.id) { Pass "Linked Item A to Vendor V" } else { Fail "Link Vendor failed"; exit 1 }


# 4. FIFO Stock-In
Step "4. FIFO Stock-In (Ledger)"
# Purchase 10 @ $3.00
$in1 = Invoke-Json POST "$BaseUrl/app/ledger/adjust" @{ item_id = $itemA.id; qty_change = 10; unit_cost_cents = 300; reason = "Batch 1" }
# Purchase 5 @ $5.00
$in2 = Invoke-Json POST "$BaseUrl/app/ledger/adjust" @{ item_id = $itemA.id; qty_change = 5; unit_cost_cents = 500; reason = "Batch 2" }

$stateA = Get-ItemState $itemA.id
if ($stateA.qty_stored -eq 15) { Pass "Qty is 15" } else { Fail "Qty mismatch: $($stateA.qty_stored)"; exit 1 }

$valA = [int]$stateA.value_cents
if ($valA -eq 5500) { Pass "Value is 5500 (10*300 + 5*500)" } else { Fail "Value mismatch: $valA"; exit 1 }


# 5. FIFO Consume
Step "5. FIFO Consume"
# Consume 12 units (10 from Batch 1 @ 300, 2 from Batch 2 @ 500)
$out = Invoke-Json POST "$BaseUrl/app/ledger/adjust" @{ item_id = $itemA.id; qty_change = -12; reason = "Consume" }
# Remaining: 3 units of Batch 2 @ 500 = 1500 cents
$stateA2 = Get-ItemState $itemA.id

if ($stateA2.qty_stored -eq 3) { Pass "Qty is 3" } else { Fail "Qty mismatch: $($stateA2.qty_stored)"; exit 1 }
if ($stateA2.value_cents -eq 1500) { Pass "Value is 1500" } else { Fail "Value mismatch: $($stateA2.value_cents)"; exit 1 }


# 6. Adjustments
Step "6. Adjustments (Item B)"
# Positive +2 B (found stock, cost 0)
$adjPos = Invoke-Json POST "$BaseUrl/app/ledger/adjust" @{ item_id = $itemB.id; qty_change = 2; reason = "Found" }
if ($adjPos) { Pass "Adjust +2 Item B" } else { Fail "Adj +2 failed"; exit 1 }
# Negative -1 B
$adjNeg = Invoke-Json POST "$BaseUrl/app/ledger/adjust" @{ item_id = $itemB.id; qty_change = -1; reason = "Lost" }
if ($adjNeg) { Pass "Adjust -1 Item B" } else { Fail "Adj -1 failed"; exit 1 }


# 7. Manufacturing Success
Step "7. Manufacturing Success"
# Recipe: 1 C <- 2 A
$rec = Invoke-Json POST "$BaseUrl/app/recipes" @{
  name = "Make C"
  output_item_id = $itemC.id
  output_qty = 1
  items = @(@{ item_id = $itemA.id; qty_required = 2 })
}

# Run: Produce 1 C
# Consumes 2 A. A was 3 units @ 500. So consume 2 @ 500 = 1000 cost.
# Output C gets cost 1000 / 1 = 1000.
$run = Invoke-Json POST "$BaseUrl/app/manufacturing/run" @{ recipe_id = $rec.id; output_qty = 1 }
if ($run.status -eq "completed") { Pass "Run completed" } else { Fail "Run failed"; exit 1 }

# Assert A stock (3 - 2 = 1)
$stA = Get-ItemState $itemA.id
if ($stA.qty_stored -eq 1) { Pass "Item A stock decreased by 2 (rem: 1)" } else { Fail "Item A stock mismatch: $($stA.qty_stored)"; exit 1 }

# Assert C stock (0 + 1 = 1)
$stC = Get-ItemState $itemC.id
if ($stC.qty_stored -eq 1) { Pass "Item C stock increased by 1" } else { Fail "Item C stock mismatch: $($stC.qty_stored)"; exit 1 }

# Assert C unit cost (1000)
if ($stC.value_cents -eq 1000) { Pass "Item C cost correct (1000)" } else { Fail "Item C cost mismatch: $($stC.value_cents)"; exit 1 }


# 8. Manufacturing Fail
Step "8. Manufacturing Fail (Fail-Fast)"
# Try produce 100 C (needs 200 A, have 1)
$bad = Try-Invoke { Invoke-Json POST "$BaseUrl/app/manufacturing/run" @{ recipe_id = $rec.id; output_qty = 100 } }
if (-not $bad.ok -and $bad.err.Exception.Response.StatusCode.value__ -eq 400) { Pass "Rejected with 400" } else { Fail "Should be 400"; exit 1 }

# Assert no stock changes
$stA_after = Get-ItemState $itemA.id
if ($stA_after.qty_stored -eq 1) { Pass "Item A stock unchanged" } else { Fail "Item A stock changed"; exit 1 }


# 9. Journal Verification
Step "9. Journal Verification"
$localAppData = [Environment]::GetFolderPath('LocalApplicationData')
$journalDir = Join-Path $localAppData 'BUSCore\app\data\journals'
if (Test-Path (Join-Path $journalDir 'inventory.jsonl')) { Pass "inventory.jsonl exists" } else { Fail "inventory.jsonl missing"; exit 1 }
if (Test-Path (Join-Path $journalDir 'manufacturing.jsonl')) { Pass "manufacturing.jsonl exists" } else { Fail "manufacturing.jsonl missing"; exit 1 }


# 10. Backup & Restore
Step "10. Backup & Restore"
# Export
$exp = Invoke-Json POST "$BaseUrl/app/db/export" @{ password = "smoke" }
if ($exp.path) { Pass "Exported DB" } else { Fail "Export failed"; exit 1 }

# Mutate: Change Item C name
$mut = Invoke-Json PUT "$BaseUrl/app/items/$($itemC.id)" @{ name = "SMK-C-MUTATED"; sku="MUT" }
$chk = Get-ItemState $itemC.id
if ($chk.name -eq "SMK-C-MUTATED") { Pass "DB Mutated" } else { Fail "Mutation failed"; exit 1 }

# Import Commit
$imp = Try-Invoke { Invoke-Json POST "$BaseUrl/app/db/import/commit" @{ path = $exp.path; password = "smoke" } }
if ($imp.ok -and $imp.resp.replaced) { Pass "Restored DB" } else { Fail "Restore failed: $($imp.err)"; exit 1 }

# Assert Reverted
$chk2 = Get-ItemState $itemC.id
if ($chk2.name -eq "SMK-C-Prod") { Pass "Item C name reverted" } else { Fail "Restore verify failed (name=$($chk2.name))"; exit 1 }


# 11. Integrity Checks
Step "11. Integrity Checks"
$allMovs = Invoke-Json GET "$BaseUrl/app/ledger/movements?limit=1000" $null
$oversold = $allMovs.movements | Where-Object { $_.is_oversold -eq 1 -or $_.is_oversold -eq $true }
if ($oversold) { Fail "Found oversold movements"; exit 1 } else { Pass "No oversold movements" }

$allItems = Invoke-Json GET "$BaseUrl/app/items" $null
$negItems = $allItems | Where-Object { $_.qty_stored -lt 0 }
if ($negItems) { Fail "Found negative stock items"; exit 1 } else { Pass "No negative stock items" }


# 12. Cleanup
Step "12. Cleanup"
$toDelete = @($itemA, $itemB, $itemC)
foreach ($i in $toDelete) {
    $fresh = Get-ItemState $i.id
    if ($fresh) {
        if ($fresh.qty_stored -ne 0) {
             $adj = Try-Invoke { Invoke-Json POST "$BaseUrl/app/ledger/adjust" @{ item_id = $fresh.id; qty_change = -($fresh.qty_stored); reason = "Cleanup" } }
        }
        $del = Try-Invoke { Invoke-RestMethod -Method DELETE -Uri "$BaseUrl/app/items/$($fresh.id)" -WebSession $script:Session }
        if ($del.ok) { Pass "Deleted $($fresh.name)" }
    }
}
$delRec = Try-Invoke { Invoke-RestMethod -Method DELETE -Uri "$BaseUrl/app/recipes/$($rec.id)" -WebSession $script:Session }
if ($delRec.ok) { Pass "Deleted Recipe" }

$delVend = Try-Invoke { Invoke-RestMethod -Method DELETE -Uri "$BaseUrl/app/vendors/$($vendV.id)" -WebSession $script:Session }
if ($delVend.ok) { Pass "Deleted Vendor" }

Pass "Cleanup complete"

Write-Host "ALL TESTS PASSED" -ForegroundColor Green
exit 0
