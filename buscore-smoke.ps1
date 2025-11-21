# SPDX-License-Identifier: AGPL-3.0-or-later
# Canonical SoT smoke harness — must pass 100% on every change
# Last updated to SoT: 2025-11-18
# buscore-smoke.ps1 — SoT-aligned smoke (PowerShell, assumes server is already running)
$ErrorActionPreference = "Stop"
try { chcp 65001 > $null } catch {}
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$BASE = "http://127.0.0.1:8765"

function Note($m){ Write-Host "[smoke] $m" -ForegroundColor Cyan }
function Snip([string]$s){ if(!$s){return ""}; if($s.Length -gt 200){ $s.Substring(0,200) } else { $s } }

function Invoke-Api {
  param(
    [Parameter(Mandatory)][ValidateSet('GET','POST','PUT','DELETE')] [string]$Method,
    [Parameter(Mandatory)][string]$Url,
    [hashtable]$Headers = @{},
    [object]$JsonBody = $null
  )
  $body = $null
  $ct = $null
  if ($null -ne $JsonBody) {
    $body = [System.Text.Encoding]::UTF8.GetBytes(($JsonBody | ConvertTo-Json -Depth 8))
    $ct = "application/json"
  }
  try {
    $resp = Invoke-WebRequest -UseBasicParsing -Method $Method -Uri $Url -Headers $Headers -Body $body -ContentType $ct -TimeoutSec 15
    return [pscustomobject]@{ Status = $resp.StatusCode; Body = $resp.Content }
  } catch [System.Net.WebException] {
    $resp = $_.Exception.Response
    if ($resp -ne $null) {
      $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
      $content = $reader.ReadToEnd()
      $reader.Close()
      return [pscustomobject]@{ Status = [int]$resp.StatusCode; Body = $content }
    } else {
      return [pscustomobject]@{ Status = 0; Body = $_.Exception.Message }
    }
  }
}

function PrintResult($label, $resp, [bool]$expect200){
  if ($expect200) {
    if ($resp.Status -eq 200) {
      Write-Host ("{0}: status 200" -f $label)
    } else {
      Write-Host ("{0}: status {1} body={2}" -f $label, $resp.Status, (Snip $resp.Body))
    }
  } else {
    if ($resp.Status -eq 200) {
      Write-Host ("{0}: status 200 (unexpected OK)" -f $label)
    } else {
      Write-Host ("{0}: status {1} (rejected as expected) body={2}" -f $label, $resp.Status, (Snip $resp.Body))
    }
  }
}

# --- Public health
$hp = Invoke-Api -Method GET -Url "$BASE/health"
Write-Host ("health(public): status {0}, body {{""ok"": true}} seen: {1}" -f $hp.Status, [bool]($hp.Body -match '"ok"\s*:\s*true'))

# --- Token
$tokResp = Invoke-Api -Method GET -Url "$BASE/session/token"
if ($tokResp.Status -ne 200) {
  Write-Host ("token: status {0}, body={1}" -f $tokResp.Status, (Snip $tokResp.Body))
  exit 1
}
$token = (ConvertFrom-Json $tokResp.Body).token
$AUTH = @{ "X-Session-Token" = $token; "Accept" = "application/json" }

# Hard cutover assertions (Windows-only, SoT)
$legacyRoot = Join-Path $env:LOCALAPPDATA 'TGC'
if (Test-Path $legacyRoot) {
  $hit = Get-ChildItem -Force -Recurse $legacyRoot -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $hit) {
    $hit = Get-Item -LiteralPath $legacyRoot -ErrorAction SilentlyContinue
  }
  if ($hit) {
    throw "Legacy TGC path found: $($hit.FullName)"
  }
}

$bcRoot = Join-Path $env:LOCALAPPDATA 'BUSCore'
$null = New-Item -ItemType Directory -Force -Path $bcRoot -ErrorAction SilentlyContinue
$null = New-Item -ItemType Directory -Force -Path (Join-Path $bcRoot 'secrets') -ErrorAction SilentlyContinue
$null = New-Item -ItemType Directory -Force -Path (Join-Path $bcRoot 'state') -ErrorAction SilentlyContinue
Write-Host "paths: hard cutover validated"

# --- Protected health (token-aware)
$hpProt = Invoke-Api -Method GET -Url "$BASE/health" -Headers $AUTH
if ($hpProt.Status -ne 200) {
  Write-Host ("❌ health(protected): HTTP {0}" -f $hpProt.Status)
  exit 1
}
try {
  $hjson = ConvertFrom-Json $hpProt.Body
} catch {
  Write-Host ("❌ health(protected): invalid JSON body={0}" -f ($hpProt.Body.Substring(0, [Math]::Min(256, $hpProt.Body.Length))))
  exit 1
}

$expected = @("version","policy","license","run-id")
$missing = $expected | Where-Object { -not ($hjson.PSObject.Properties.Name -contains $_) }
if ($missing.Count -gt 0) {
  Write-Host ("❌ health(protected): missing keys => {0}" -f ($missing -join ", "))
  exit 1
}
Write-Host "✅ health(protected): version, policy, license, run-id present"

# --- UI presence
$ui = Invoke-Api -Method GET -Url "$BASE/ui/shell.html"
Write-Host ("ui(shell): status {0}, length>0: {1}" -f $ui.Status, ([bool]($ui.Body) -and $ui.Body.Length -gt 0))

# --- Enable writes (if supported)
$writes = Invoke-Api -Method POST -Url "$BASE/dev/writes" -Headers $AUTH -JsonBody @{ enabled = $true }
Write-Host ("writes.enable: status {0}, body={1}" -f $writes.Status, (Snip $writes.Body))
$WritesOn = ($writes.Status -eq 200)

# --- Vendors CRUD
$vnCreate = Invoke-Api -Method POST -Url "$BASE/app/vendors" -Headers $AUTH -JsonBody @{ name = "smoke-vendor-$(Get-Random)" }
PrintResult "vendors.create" $vnCreate $true
$vid = $null; try { $vid = (ConvertFrom-Json $vnCreate.Body).id } catch {}
$vnList = Invoke-Api -Method GET -Url "$BASE/app/vendors" -Headers $AUTH
PrintResult "vendors.list" $vnList $true
if ($vid -ne $null) {
  $vnUpdate = Invoke-Api -Method PUT -Url "$BASE/app/vendors/$vid" -Headers $AUTH -JsonBody @{ name = "smoke-vendor-upd" }
  PrintResult "vendors.update" $vnUpdate $true
  $vnDelete = Invoke-Api -Method DELETE -Url "$BASE/app/vendors/$vid" -Headers $AUTH
  PrintResult "vendors.delete" $vnDelete $true
} else {
  Write-Host "vendors.update/delete: skipped (id not available)"
}

# --- Items CRUD + one-off qty
$itemCreate = Invoke-Api -Method POST -Url "$BASE/app/items" -Headers $AUTH -JsonBody @{ name = "smoke-item-$(Get-Random)"; sku = "SMK-$(Get-Random)"; qty = 0 }
PrintResult "items.create" $itemCreate $true
$iid = $null; try { $iid = (ConvertFrom-Json $itemCreate.Body).id } catch {}
$itemList = Invoke-Api -Method GET -Url "$BASE/app/items" -Headers $AUTH
PrintResult "items.list" $itemList $true
if ($iid -ne $null) {
  $itemUpdate = Invoke-Api -Method PUT -Url "$BASE/app/items/$iid" -Headers $AUTH -JsonBody @{ qty = 1 }
  PrintResult "items.PUT(one-off)" $itemUpdate $true
  $itemDelete = Invoke-Api -Method DELETE -Url "$BASE/app/items/$iid" -Headers $AUTH
  PrintResult "items.delete" $itemDelete $true
} else {
  Write-Host "items.PUT/delete: skipped (id not available)"
}

# --- Import preview (free endpoint, schema not specified in SoT)
$impPrev = Invoke-Api -Method POST -Url "$BASE/app/import/preview" -Headers $AUTH -JsonBody @{ note = "SoT schema pending" }
if ($impPrev.Status -eq 200) {
  Write-Host "import.preview (writes on): status 200"
} elseif ($impPrev.Status -eq 422) {
  Write-Host "import.preview (writes on): status 422 (expected until request schema defined in SoT)"
} else {
  Write-Host ("import.preview (writes on): status {0} (unexpected) body={1}" -f $impPrev.Status, (Snip $impPrev.Body))
}

# --- Gated endpoints (must be rejected under community license)
$rfq = Invoke-Api -Method POST -Url "$BASE/app/rfq/generate" -Headers $AUTH -JsonBody @{ }
PrintResult "rfq.generate" $rfq $false
$mfg = Invoke-Api -Method POST -Url "$BASE/app/manufacturing/run" -Headers $AUTH -JsonBody @{ }
PrintResult "manufacturing.run" $mfg $false
$inv = Invoke-Api -Method POST -Url "$BASE/app/inventory/run" -Headers $AUTH -JsonBody @{ }
PrintResult "inventory.run (alias)" $inv $false
$impCommit = Invoke-Api -Method POST -Url "$BASE/app/import/commit" -Headers $AUTH -JsonBody @{ }
PrintResult "import.commit" $impCommit $false
