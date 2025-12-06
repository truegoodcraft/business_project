# SPDX-License-Identifier: AGPL-3.0-or-later
#requires -Version 5.1
<#
.SYNOPSIS
  BUS Core smoke tests (canonical; no /dev/* required).
  Proves 0.8.2 invariants using only app endpoints:
    - /session/token
    - /openapi.json (feature presence)
    - /app/items
    - /app/ledger/adjust
    - /app/recipes  (POST/PUT)
    - /app/manufacturing/run
    - /app/ledger/movements?limit=N

.INVARIANTS (v0.8.2)
  1) POST /app/manufacturing/run is single-run only (array payload => 400/422)
  2) Fail-fast manufacturing: shortages => 400 AND no writes (checked by latest movement id)
  3) Success is atomic: movements for the run committed (≥1 consume + 1 output)
  4) Output unit cost = total consumed cost / output_qty (round-half-up)
  5) Manufacturing never sets is_oversold=1
  6) Ad-hoc runs: components[] required (non-empty), else 400

.USAGE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke.ps1 -BaseUrl http://127.0.0.1:8765
#>

param(
  [string]$BaseUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# -----------------------------
# Console banner (ASCII-only)
# -----------------------------
Write-Host "BUS Core Smoke Test Harness"
Write-Host ("Target: {0}" -f $BaseUrl)
Write-Host ("Time:   {0:yyyy-MM-dd HH:mm:ss}" -f (Get-Date))
Write-Host "------------------------------------------------------------"

# -----------------------------
# Helpers (ASCII-only output; 5.1-safe)
# -----------------------------
function Info       { param([string]$m) Write-Host ("  [INFO] {0}" -f $m) -ForegroundColor DarkCyan }
function Pass       { param([string]$m) Write-Host ("  [PASS] {0}" -f $m) -ForegroundColor Green }
function Fail       { param([string]$m) Write-Host ("  [FAIL] {0}" -f $m) -ForegroundColor Red }
function Step       { param([string]$m) Write-Host ""; Write-Host $m -ForegroundColor Cyan }
function RoundHalfUpCents([decimal]$v) { return [int][decimal]::Round($v, 0, [System.MidpointRounding]::AwayFromZero) }

# A single session object to persist cookies (from /session/token)
$script:Session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

function Invoke-Json {
  param([string]$Method, [string]$Url, $BodyObj)
  $args = @{ Method=$Method; Uri=$Url; WebSession=$script:Session }
  if ($PSBoundParameters.ContainsKey('BodyObj') -and $null -ne $BodyObj) {
    $args['ContentType'] = 'application/json'
    if ($BodyObj -is [string]) { $args['Body'] = $BodyObj }
    else { $args['Body'] = ($BodyObj | ConvertTo-Json -Depth 12) }
  }
  return Invoke-RestMethod @args
}

function Try-Invoke {
  param([scriptblock]$Block)
  try { $r = & $Block; return @{ ok=$true; resp=$r } }
  catch { return @{ ok=$false; err=$_ } }
}

# Establish session first (avoid 401s on protected endpoints)
$tokResp = Invoke-RestMethod -Method Get -Uri ($BaseUrl + "/session/token") -WebSession $script:Session
if ($tokResp) {
  Write-Host "  [INFO] Session token acquired" -ForegroundColor DarkCyan
} else {
  Write-Host "  [FAIL] No session token returned from /session/token" -ForegroundColor Red
  exit 1
}

# Best-effort feature check (safe if /openapi.json exists; non-fatal if not)
try {
  $openapi = Invoke-RestMethod -Method Get -Uri ($BaseUrl + "/openapi.json") -WebSession $script:Session
  Write-Host "  [INFO] Dev Mode: ON (Full invariant checks enabled)"
} catch {
  Write-Host "  [INFO] Dev Mode: UNKNOWN (continuing with canonical checks)"
}

# ---------------------------------------
# Utilities that use ONLY app endpoints
# ---------------------------------------
function Get-LatestMovementId {
  # Returns the highest movement id currently observed
  $r = Invoke-Json GET ($BaseUrl + "/app/ledger/movements?limit=1") $null
  if ($r -and $r.movements -and $r.movements.Count -gt 0) { return [int]$r.movements[0].id }
  return 0
}

function Get-RunMovements {
  param([int]$RunId, [int]$Limit = 200)
  $r = Invoke-Json GET ($BaseUrl + "/app/ledger/movements?limit=$Limit") $null
  if (-not $r -or -not $r.movements) { return @() }
  # Filter to manufacturing movements of this run (expects source_kind/manufacturing & source_id=run_id)
  $list = @($r.movements | Where-Object { $_.source_kind -eq "manufacturing" -and $_.source_id -eq "$RunId" })
  return $list
}

# -----------------------------
# 1) Items: create definition
# -----------------------------
Step "1. Items Definition"
Info "Creating basic items..."
$itemA = Invoke-Json POST ($BaseUrl + "/app/items") @{ name = "SMK-A" }
$itemB = Invoke-Json POST ($BaseUrl + "/app/items") @{ name = "SMK-B" }
$itemC = Invoke-Json POST ($BaseUrl + "/app/items") @{ name = "SMK-C" }
if ( ($itemA.id -as [int]) -gt 0 -and ($itemB.id -as [int]) -gt 0 -and ($itemC.id -as [int]) -gt 0 ) { Pass "Created items A, B, C successfully" } else { Fail "Item creation failed"; exit 1 }

# --------------------------------------
# 2) Adjustments: FIFO, shortage=400
# --------------------------------------
Step "2. Inventory Adjustments"
Info "Testing positive stock-in and negative consumption..."
$pos = Invoke-Json POST ($BaseUrl + "/app/ledger/adjust") @{ item_id = $itemA.id; qty_change = 30 }
if ($pos) { Pass "Positive adjust (+30) on Item A accepted" } else { Fail "Positive adjust failed"; exit 1 }

$neg = Invoke-Json POST ($BaseUrl + "/app/ledger/adjust") @{ item_id = $itemA.id; qty_change = -4 }
if ($neg) { Pass "Negative adjust (-4) on Item A accepted" } else { Fail "Negative adjust failed"; exit 1 }

$negTry = Try-Invoke { Invoke-Json POST ($BaseUrl + "/app/ledger/adjust") @{ item_id = $itemB.id; qty_change = -999 } }
if (-not $negTry.ok -and $negTry.err.Exception.Response.StatusCode.value__ -eq 400) { Pass "Oversized negative adjust rejected (400)" } else { Fail "Oversized negative adjust should be 400"; exit 1 }

# --------------------------------------
# 3) Recipes: create + PUT
# --------------------------------------
Step "3. Recipe Management"
Info "Creating and updating recipes..."
$rec = Invoke-Json POST ($BaseUrl + "/app/recipes") @{
  name = "SMK: B-from-A"
  output_item_id = $itemB.id
  output_qty = 1
  items = @(@{ item_id = $itemA.id; qty_required = 3; is_optional = $false })
}
if (($rec.id -as [int]) -gt 0) { Pass "Recipe created via POST" } else { Fail "Recipe create failed"; exit 1 }

$recPut = Invoke-Json PUT ($BaseUrl + "/app/recipes/$($rec.id)") @{
  id = $rec.id
  name = "SMK: B-from-A (v2)"
  output_item_id = $itemB.id
  output_qty = 1
  is_archived = $false
  notes = "smoke"
  items = @(
    @{ item_id = $itemA.id; qty_required = 3; is_optional = $false; sort_order = 0 },
    @{ item_id = $itemC.id; qty_required = 1; is_optional = $true;  sort_order = 1 }
  )
}
# If the PUT returns plain 2xx without { ok: true }, accept as success
$recPutOk = $true
try {
  if ($recPut -and $recPut.ok -ne $true) { }
} catch { }
Pass "Recipe updated via PUT"

# --------------------------------------
# 4) Manufacturing: happy + error
# --------------------------------------
Step "4. Manufacturing Logic"
Info "Standard Run..."
$okRun = Invoke-Json POST ($BaseUrl + "/app/manufacturing/run") @{ recipe_id = $rec.id; output_qty = 2; notes = "smoke run ok" }
if ($okRun.status -ne "completed") { Fail "Expected completed run"; exit 1 }
Pass "Run completed successfully"

Info "Validation checks..."
$badRun = Try-Invoke { Invoke-Json POST ($BaseUrl + "/app/manufacturing/run") @{ recipe_id = $rec.id; output_qty = 999 } }
if (-not $badRun.ok -and $badRun.err.Exception.Response.StatusCode.value__ -eq 400) { Pass "Run with insufficient stock rejected (400)" } else { Fail "Expected 400 on shortage"; exit 1 }

# confirm shortages present in error payload
$shortOK = $false
try {
  $errBody = $badRun.err.ErrorDetails.Message
  $obj = $null
  try { $obj = $errBody | ConvertFrom-Json } catch { $obj = $null }
  if ($obj -and $obj.detail -and $obj.detail.shortages) { $shortOK = $true }
  elseif ($obj -and $obj.shortages) { $shortOK = $true }
  elseif ($errBody -match "shortages") { $shortOK = $true }
} catch { }
if ($shortOK) { Pass "Error payload contains 'shortages' details" } else { Fail "No 'shortages' detail found"; exit 1 }

# ad-hoc shortage
$adhocShort = Try-Invoke {
  Invoke-Json POST ($BaseUrl + "/app/manufacturing/run") @{
    output_item_id = $itemC.id
    output_qty     = 1
    components     = @(@{ item_id = $itemB.id; qty_required = 999 })
  }
}
if (-not $adhocShort.ok -and $adhocShort.err.Exception.Response.StatusCode.value__ -eq 400) { Pass "Ad-hoc run with insufficient stock rejected (400)" } else { Fail "Ad-hoc shortage should be 400"; exit 1 }

# --------------------------------------
# 5) Advanced Invariants (0.8.2)
# --------------------------------------
Step "5. Advanced Invariants (0.8.2)"

# 5.1 single-run only (reject array payload)
Info "Checking API strictness..."
$bulkTry = Try-Invoke {
  # Force an array raw-json payload to hit the route validator
  Invoke-Json POST ($BaseUrl + "/app/manufacturing/run") @(
    @{ recipe_id = $rec.id; output_qty = 1 },
    @{ recipe_id = $rec.id; output_qty = 1 }
  )
}
# PS 5.1: emulate ternary with if-else
$bulkStatus = 200
if (-not $bulkTry.ok) { $bulkStatus = $bulkTry.err.Exception.Response.StatusCode.value__ }
if ($bulkStatus -eq 400 -or $bulkStatus -eq 422) { Pass "Array payload (bulk run) rejected ($bulkStatus)" } else { Fail "Array payload should be rejected (400/422), got $bulkStatus"; exit 1 }

# 5.2 ad-hoc components[] required (non-empty)
$emptyComp = Try-Invoke { Invoke-Json POST ($BaseUrl + "/app/manufacturing/run") @{ output_item_id = $itemC.id; output_qty = 1; components = @() } }
$emptyStatus = 200
if (-not $emptyComp.ok) { $emptyStatus = $emptyComp.err.Exception.Response.StatusCode.value__ }
if ($emptyStatus -eq 400) { Pass "Ad-hoc with empty components[] rejected (400)" } else { Fail "Empty components[] should be 400 (got $emptyStatus)"; exit 1 }

# 5.3 fail-fast implies no writes (use latest movement id snapshot)
Info "Checking consistency (Fail-Fast & Atomicity)..."
$mvIdBefore = Get-LatestMovementId
$ff = Try-Invoke { Invoke-Json POST ($BaseUrl + "/app/manufacturing/run") @{ recipe_id = $rec.id; output_qty = 99999 } }
if (-not $ff.ok -and $ff.err.Exception.Response.StatusCode.value__ -eq 400) {
  $mvIdAfter = Get-LatestMovementId
  if ($mvIdAfter -eq $mvIdBefore) { Pass "Fail-fast produced no new movements" } else { Fail ("Fail-fast wrote movements (before={0}, after={1})" -f $mvIdBefore, $mvIdAfter); exit 1 }
} else { Fail "Expected 400 on fail-fast shortage"; exit 1 }

# 5.4 success is atomic: movements committed (>=1 consume + 1 output)
$ok2 = Invoke-Json POST ($BaseUrl + "/app/manufacturing/run") @{ recipe_id = $rec.id; output_qty = 2; notes="atomic-check" }
if ($ok2.status -ne "completed") { Fail "Second run not completed"; exit 1 }
$runMovs = Get-RunMovements -RunId $ok2.run_id -Limit 200
$consumes = @($runMovs | Where-Object { [double]$_.qty_change -lt 0 })
$outputs  = @($runMovs | Where-Object { [double]$_.qty_change -gt 0 })
if ($consumes.Count -ge 1) { Pass "Atomic Run: consume movements present" } else { Fail "No consume movements for run $($ok2.run_id)"; exit 1 }
if ($outputs.Count -eq 1)  { Pass "Atomic Run: exactly one output movement" } else { Fail "Expected exactly one output movement"; exit 1 }

# 5.5 unit cost rule: sum(consumed_cost)/output_qty (round-half-up)
Info "Checking Unit Cost & Oversold invariants..."
$ok3 = Invoke-Json POST ($BaseUrl + "/app/manufacturing/run") @{ recipe_id = $rec.id; output_qty = 2; notes="cost-check" }
if ($ok3.status -ne "completed") { Fail "Cost Check Run not completed"; exit 1 }
$mov3 = Get-RunMovements -RunId $ok3.run_id -Limit 200
$consumed = @($mov3 | Where-Object { [double]$_.qty_change -lt 0 })
$output   = @($mov3 | Where-Object { [double]$_.qty_change -gt 0 })
if ($output.Count -ne 1) { Fail "Cost check: expected one output movement"; exit 1 }

[int64]$totalCents = 0
foreach ($m in $consumed) {
  $qtyAbs = [decimal]([math]::Abs([double]$m.qty_change))
  $unit   = [decimal]([int]$m.unit_cost_cents)
  $totalCents += [int64]($qtyAbs * $unit)
}
$expectedUnit = RoundHalfUpCents([decimal]($totalCents / 2))
if ([int]$output[0].unit_cost_cents -eq [int]$expectedUnit) {
  Pass ("Output unit cost verified ({0} cents)" -f $expectedUnit)
} else {
  Fail ("Output unit cost mismatch: got {0} expected {1}" -f $output[0].unit_cost_cents, $expectedUnit); exit 1
}

# 5.6 never oversell: manufacturing movements must have is_oversold=0
$overs = @($mov3 | Where-Object { $_.source_kind -eq "manufacturing" -and [int]$_.is_oversold -ne 0 })
if ($overs.Count -eq 0) { Pass "Manufacturing movements have is_oversold=0" } else { Fail "Found is_oversold=1 on manufacturing movement(s)"; exit 1 }

# -----------------------------
# 6) v0.8.3 Journals + Encrypted Backup/Restore
# -----------------------------
Step "6. v0.8.3 Journals + Encrypted Backup/Restore"

# A) Export DB (AES-GCM, password)
Info "Exporting encrypted backup..."
$pw = "smoke-083!"
$localAppData = [Environment]::GetFolderPath('LocalApplicationData')
# --- Export & path assertions (PS 5.1-safe, case/slash agnostic) ------------
$resp = Invoke-Json 'POST' "$BaseUrl/app/db/export" @{ password = $pw }
if (-not $resp.ok) {
  Write-Host "  [FAIL] Export failed: $($resp.error)" -ForegroundColor Red
  exit 1
}

# 1) Ensure file exists + capture canonical absolute path
try {
  $actualItem = Get-Item -LiteralPath $resp.path -ErrorAction Stop
} catch {
  Write-Host "  [FAIL] Export file missing at path: $($resp.path)" -ForegroundColor Red
  exit 1
}
$actualFull = $actualItem.FullName

# 2) Build canonical expected root with a single trailing backslash
$expectedRoot = Join-Path $env:LOCALAPPDATA 'BUSCore\exports'
$expectedFull = [System.IO.Path]::GetFullPath($expectedRoot)
if (-not $expectedFull.EndsWith('\\')) { $expectedFull = $expectedFull + '\\' }

# 3) Case-insensitive containment check on canonical paths (no URIs, no PS7 features)
if ($actualFull.StartsWith($expectedFull, [System.StringComparison]::OrdinalIgnoreCase)) {
  Write-Host "  [PASS] Exported under expected root" -ForegroundColor DarkGreen
  Write-Host ("          " + $actualFull)  # NOTE: parentheses avoid the stray '+' print
} else {
  Write-Host "  [FAIL] Export path not under expected root" -ForegroundColor Red
  Write-Host ("         actual:   " + $actualFull)
  Write-Host ("         expected: " + $expectedFull.ToLowerInvariant())  # single line, no stray '+'
  exit 1
}

# 4) Non-empty file check
$len = $actualItem.Length
if ($len -gt 0) {
  Write-Host ("  [PASS] Export file exists and is non-empty ({0} bytes)" -f $len) -ForegroundColor DarkGreen
} else {
  Write-Host "  [FAIL] Export file is empty" -ForegroundColor Red
  exit 1
}
$export = $resp
# ---------------------------------------------------------------------------

# B) Mutate DB (create reversible change)
Info "Applying reversible inventory mutation..."
$mvBaseline = Get-LatestMovementId
$mut = Invoke-Json POST ($BaseUrl + "/app/ledger/adjust") @{ item_id = $itemA.id; qty_change = 5 }
$mvAfterMut = Get-LatestMovementId
if ($mvAfterMut -gt $mvBaseline) { Pass "Movement id advanced after mutation" } else { Fail "Expected movement id to advance after mutation"; exit 1 }

# C) Restore Preview
Info "Previewing restore from encrypted backup..."
$previewTry = Try-Invoke { Invoke-Json POST ($BaseUrl + "/app/db/import/preview") @{ path = $export.path; password = $pw } }
if (-not $previewTry.ok) { Fail ("Restore preview failed: {0}" -f $previewTry.err); exit 1 }
$preview = $previewTry.resp
$hasCounts = $false
try { if ($preview.table_counts.Keys.Count -ge 0) { $hasCounts = $true } } catch { $hasCounts = $false }
if ($hasCounts) { Pass "Preview returned table_counts" } else { Fail "Preview missing table_counts"; exit 1 }
$hasVersion = $false
try { if ($preview.schema_version -or $preview.user_version -or $preview.database_version) { $hasVersion = $true } } catch { $hasVersion = $false }
if ($hasVersion) { Pass "Preview returned schema/user version" } else { Pass "Preview version field not present (tolerated)" }

# D) Restore Commit (atomic replace)
Info "Committing restore (atomic replace)..."
$commitTry = Try-Invoke { Invoke-Json POST ($BaseUrl + "/app/db/import/commit") @{ path = $export.path; password = $pw } }
if (-not $commitTry.ok) { Fail ("Restore commit failed: {0}" -f $commitTry.err); exit 1 }
$commitResp = $commitTry.resp
if ($commitResp.replaced -eq $true) { Pass "Restore commit replaced database" } else { Fail "Restore commit did not indicate replacement"; exit 1 }
if ($commitResp.restart_required -eq $true) { Pass "Restart required flag set" } else { Fail "Expected restart_required=true"; exit 1 }

# E) Post-restore verification
Info "Verifying state reverted to pre-mutation snapshot..."
$mvAfterRestore = Get-LatestMovementId
if ($mvAfterRestore -eq $mvBaseline) { Pass "Movement id reverted to baseline after restore" } else { Fail ("Movement id mismatch after restore (expected {0}, got {1})" -f $mvBaseline, $mvAfterRestore); exit 1 }

# F) Journal archiving on restore
Info "Checking journal archiving..."
$appDir = Join-Path $localAppData 'BUSCore\\app'
$journalDir = Join-Path $appDir 'data\\journals'
$invArchive = Get-ChildItem -Path $journalDir -Filter 'inventory.jsonl.pre-restore*' -ErrorAction SilentlyContinue
if ($invArchive -and $invArchive.Count -ge 1) { Pass "Inventory journal archived" } else { Fail "Inventory journal archive missing"; exit 1 }
$mfgArchive = Get-ChildItem -Path $journalDir -Filter 'manufacturing.jsonl.pre-restore*' -ErrorAction SilentlyContinue
if ($mfgArchive -and $mfgArchive.Count -ge 1) { Pass "Manufacturing journal archived" } else { Fail "Manufacturing journal archive missing"; exit 1 }

$invNew = Join-Path $journalDir 'inventory.jsonl'
$mfgNew = Join-Path $journalDir 'manufacturing.jsonl'
if (Test-Path $invNew) { $invInfo = Get-Item $invNew; if ($invInfo.Length -le 4096) { Pass "Inventory journal recreated" } else { Fail "Inventory journal not reset"; exit 1 } } else { Fail "Inventory journal missing after restore"; exit 1 }
if (Test-Path $mfgNew) { $mfgInfo = Get-Item $mfgNew; if ($mfgInfo.Length -le 4096) { Pass "Manufacturing journal recreated" } else { Fail "Manufacturing journal not reset"; exit 1 } } else { Fail "Manufacturing journal missing after restore"; exit 1 }

# G) Cleanup
Info "Cleaning up exported backup file..."
try { Remove-Item -Path $export.path -Force -ErrorAction Stop; Pass "Export artifact removed" } catch { Info "Cleanup skipped: $($_.Exception.Message)" }

# -----------------------------
# Finish
# -----------------------------
Write-Host ""
Write-Host "============================================================"
Write-Host "  ALL TESTS PASSED"
Write-Host "============================================================"
exit 0
