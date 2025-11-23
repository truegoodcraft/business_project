# SPDX-License-Identifier: AGPL-3.0-or-later
# Consolidated smoke harness covering UI CRUD + DB persistence

$ErrorActionPreference = "Stop"
try { chcp 65001 > $null } catch {}
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

function Write-Stage {
    param([string]$Stage)
    Write-Host ("[smoke] === {0} ===" -f $Stage) -ForegroundColor Cyan
}

function Write-Info { param([string]$Msg) Write-Host ("[smoke] {0}" -f $Msg) -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host ("[smoke] {0}" -f $Msg) -ForegroundColor Yellow }
function Write-Err { param([string]$Msg) Write-Host ("[smoke] {0}" -f $Msg) -ForegroundColor Red }

function Emit-Failure {
    param(
        [string]$Stage,
        [string]$Reason,
        [string]$ArtifactsDir
    )
    $summary = @{ Status = "FAIL"; Stage = $Stage; Reason = $Reason }
    $line = ($summary | ConvertTo-Json -Depth 5 -Compress)
    Write-Err $line
    if ($ArtifactsDir) {
        try {
            $summary | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -Path (Join-Path $ArtifactsDir "failure.json")
        } catch {}
    }
    exit 1
}

function Ensure-Dir { param([string]$Path) if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null } }

# --- Paths and configuration
$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$artifacts = Join-Path $repoRoot "artifacts/smoke"
Ensure-Dir $artifacts

$baseUrl = $env:BUSCORE_URL
if (-not $baseUrl) { $baseUrl = "http://127.0.0.1:8765/ui/shell.html" }
$baseUri = [Uri]$baseUrl
$apiBase = "{0}://{1}:{2}" -f $baseUri.Scheme, $baseUri.Host, $baseUri.Port
$inventoryUrl = $baseUrl

$Local = [Environment]::GetFolderPath('LocalApplicationData')
$appDir = Join-Path (Join-Path $Local 'BUSCore') 'app'
$appDb = Join-Path $appDir 'app.db'
Write-Info ("App DB path: {0}" -f $appDb)

Ensure-Dir $appDir

# --- SQLite helpers
$script:SqliteProvider = $null
function Import-SqliteAssembly {
    if ($script:SqliteProvider) { return }
    foreach ($candidate in 'Microsoft.Data.Sqlite','System.Data.SQLite') {
        try {
            Add-Type -AssemblyName $candidate -ErrorAction Stop
            $script:SqliteProvider = $candidate
            return
        } catch {}
    }
    $dotnet = (Get-Command dotnet -ErrorAction SilentlyContinue)?.Path
    if ($dotnet) {
        $dnRoot = Split-Path (Split-Path $dotnet)
        $dll = Get-ChildItem -Path $dnRoot -Filter "Microsoft.Data.Sqlite.dll" -Recurse -ErrorAction SilentlyContinue -Depth 4 | Select-Object -First 1
        if ($dll) {
            Add-Type -Path $dll.FullName -ErrorAction Stop
            $script:SqliteProvider = 'Microsoft.Data.Sqlite'
            return
        }
    }
    throw "SQLite provider not available; install Microsoft.Data.Sqlite or System.Data.SQLite"
}

function Invoke-SqliteQuery {
    param(
        [string]$DbPath,
        [string]$Sql,
        [hashtable]$Parameters = @{}
    )
    Import-SqliteAssembly
    if ($script:SqliteProvider -eq 'Microsoft.Data.Sqlite') {
        $conn = [Microsoft.Data.Sqlite.SqliteConnection]::new("Data Source=$DbPath")
        $cmdType = [Microsoft.Data.Sqlite.SqliteCommand]
        $paramCtor = { param($k,$v) [Microsoft.Data.Sqlite.SqliteParameter]::new($k,$v) }
    } else {
        $conn = [System.Data.SQLite.SQLiteConnection]::new("Data Source=$DbPath")
        $cmdType = [System.Data.SQLite.SQLiteCommand]
        $paramCtor = { param($k,$v) [System.Data.SQLite.SQLiteParameter]::new($k,$v) }
    }
    $conn.Open()
    try {
        $cmd = $cmdType::new($Sql,$conn)
        foreach ($k in $Parameters.Keys) { $cmd.Parameters.Add((& $paramCtor $k $Parameters[$k])) | Out-Null }
        $reader = $cmd.ExecuteReader()
        $rows = @()
        while ($reader.Read()) {
            $obj = @{}
            for ($i=0; $i -lt $reader.FieldCount; $i++) { $obj[$reader.GetName($i)] = $reader.GetValue($i) }
            $rows += [pscustomobject]$obj
        }
        return $rows
    } finally { $conn.Dispose() }
}

function Invoke-SqliteNonQuery {
    param(
        [string]$DbPath,
        [string]$Sql,
        [hashtable]$Parameters = @{}
    )
    Import-SqliteAssembly
    if ($script:SqliteProvider -eq 'Microsoft.Data.Sqlite') {
        $conn = [Microsoft.Data.Sqlite.SqliteConnection]::new("Data Source=$DbPath")
        $cmdType = [Microsoft.Data.Sqlite.SqliteCommand]
        $paramCtor = { param($k,$v) [Microsoft.Data.Sqlite.SqliteParameter]::new($k,$v) }
    } else {
        $conn = [System.Data.SQLite.SQLiteConnection]::new("Data Source=$DbPath")
        $cmdType = [System.Data.SQLite.SQLiteCommand]
        $paramCtor = { param($k,$v) [System.Data.SQLite.SQLiteParameter]::new($k,$v) }
    }
    $conn.Open()
    try {
        $cmd = $cmdType::new($Sql,$conn)
        foreach ($k in $Parameters.Keys) { $cmd.Parameters.Add((& $paramCtor $k $Parameters[$k])) | Out-Null }
        return $cmd.ExecuteNonQuery()
    } finally { $conn.Dispose() }
}

# --- HTTP helpers
function Invoke-SmokeRequest {
    param(
        [Parameter(Mandatory)][ValidateSet('GET','POST','PUT','DELETE')] [string]$Method,
        [Parameter(Mandatory)][string]$Path,
        [object]$Body = $null,
        [hashtable]$Headers = @{}
    )
    $uri = "$apiBase$Path"
    $json = $null
    $ct = $null
    if ($null -ne $Body) {
        $json = [System.Text.Encoding]::UTF8.GetBytes(($Body | ConvertTo-Json -Depth 8))
        $ct = 'application/json'
    }
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Method $Method -Uri $uri -Headers $Headers -Body $json -ContentType $ct -TimeoutSec 30
        return [pscustomobject]@{ Status = $resp.StatusCode; Body = $resp.Content }
    } catch [System.Net.WebException] {
        $res = $_.Exception.Response
        if ($res) {
            $reader = New-Object System.IO.StreamReader($res.GetResponseStream())
            $content = $reader.ReadToEnd()
            $reader.Close()
            return [pscustomobject]@{ Status = [int]$res.StatusCode; Body = $content }
        }
        return [pscustomobject]@{ Status = 0; Body = $_.Exception.Message }
    }
}

function Get-SessionToken {
    $resp = Invoke-SmokeRequest -Method GET -Path '/session/token'
    if ($resp.Status -ne 200) { throw "token request failed HTTP $($resp.Status)" }
    return (ConvertFrom-Json $resp.Body).token
}

function Wait-ForServer {
    param([int]$TimeoutSec = 60)
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($stopwatch.Elapsed.TotalSeconds -lt $TimeoutSec) {
        try {
            $resp = Invoke-WebRequest -Uri $inventoryUrl -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -eq 200 -and $resp.Content -match 'Inventory') { return $true }
        } catch {}
        Start-Sleep -Seconds 2
    }
    return $false
}

# --- Stage A: readiness
Write-Stage "Stage A: server readiness"
$serverStartedBySmoke = $false
if (-not (Wait-ForServer -TimeoutSec 5)) {
    Write-Info "Server not detected; starting dev server"
    $python = (Get-Command python -ErrorAction SilentlyContinue)?.Path
    if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue)?.Path }
    if (-not $python) { Emit-Failure -Stage 'Stage A' -Reason 'Python not found' -ArtifactsDir $artifacts }

    $proc = Start-Process $python -ArgumentList @('-m','uvicorn','core.api.http:create_app','--factory','--host',$baseUri.Host,'--port',$baseUri.Port) -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden
    $serverStartedBySmoke = $true
    if (-not (Wait-ForServer -TimeoutSec 60)) {
        Emit-Failure -Stage 'Stage A' -Reason 'Server did not become ready' -ArtifactsDir $artifacts
    }
} else {
    Write-Info "Server already running"
}

# --- Stage B: DB hygiene & backup
Write-Stage "Stage B: DB hygiene"
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupPath = Join-Path $appDir ("app.smokebackup.$timestamp.db")
if (Test-Path $appDb) {
    Copy-Item $appDb $backupPath -Force
    Write-Info ("Backup created: {0}" -f $backupPath)
} else {
    Write-Warn "DB missing; server will create on demand"
}

$removedVendors = 0
$removedItems = 0
if (Test-Path $appDb) {
    $removedVendors = Invoke-SqliteNonQuery -DbPath $appDb -Sql "DELETE FROM vendors WHERE name LIKE 'SMK_%'" -Parameters @{}
    $removedItems = Invoke-SqliteNonQuery -DbPath $appDb -Sql "DELETE FROM items WHERE name LIKE 'SMK_%' OR sku LIKE 'SMK_%'" -Parameters @{}
}
Write-Info ("Purged vendors: {0}, items: {1}" -f $removedVendors, $removedItems)

$dbTimeBefore = $null
if (Test-Path $appDb) { $dbTimeBefore = (Get-Item $appDb).LastWriteTime; Write-Info ("DB last write (before CRUD): {0}" -f $dbTimeBefore) }

# rotate backups (keep 3)
$backups = Get-ChildItem -Path $appDir -Filter 'app.smokebackup.*.db' | Sort-Object LastWriteTime -Descending
$excess = $backups | Select-Object -Skip 3
foreach ($b in $excess) { Remove-Item $b.FullName -Force }

# --- Stage C: ensure vendor
Write-Stage "Stage C: vendor precondition"
$token = Get-SessionToken
$headers = @{ 'X-Session-Token' = $token }
try { Invoke-SmokeRequest -Method POST -Path '/dev/writes' -Headers $headers -Body @{ enabled = $true } | Out-Null } catch {}

$vendorResp = Invoke-SmokeRequest -Method GET -Path '/app/vendors' -Headers $headers
if ($vendorResp.Status -ne 200) { Emit-Failure -Stage 'Stage C' -Reason "Vendor list failed HTTP $($vendorResp.Status)" -ArtifactsDir $artifacts }
$vendorList = @()
try { $vendorList = ConvertFrom-Json $vendorResp.Body } catch {}
if (-not ($vendorList -is [System.Collections.IEnumerable])) { $vendorList = @() }
$vendor = $vendorList | Select-Object -First 1
if (-not $vendor) {
    $name = "SMK_Vendor_$(Get-Random)"
    $create = Invoke-SmokeRequest -Method POST -Path '/app/vendors' -Headers $headers -Body @{ name = $name }
    if ($create.Status -ne 200) { Emit-Failure -Stage 'Stage C' -Reason "Vendor create failed HTTP $($create.Status)" -ArtifactsDir $artifacts }
    $vendor = ConvertFrom-Json $create.Body
}
$vendorId = $vendor.id
$vendorName = $vendor.name
Write-Info ("Using vendor: {0} ({1})" -f $vendorName, $vendorId)

# --- Stage D: UI create/edit/filter via Playwright
Write-Stage "Stage D: UI CRUD"
$itemName = "SMK_Item_$(Get-Random)"
$itemSku = "SMK_SKU_$(Get-Random)"
$itemNotes = "SMK notes $(Get-Random)"
$itemLocation = "SMK_LOC_$(Get-Random)"
$itemLocationEdited = 'SMK_LOC_EDIT'
$playwrightInput = @{ baseUrl = $inventoryUrl; vendorId = $vendorId; vendorName = $vendorName; name = $itemName; sku = $itemSku; qty = 2.5; unitSystem = 'ea'; unit = 'ea'; price = 12.34; itemType = 'material'; notes = $itemNotes; location = $itemLocation; editedQty = 3; editedPrice = 2; editedLocation = $itemLocationEdited; artifacts = $artifacts; timeoutMs = 60000 }
$inputPath = Join-Path $artifacts 'playwright-input.json'
$playwrightInput | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -Path $inputPath

$pwScript = @"
import fs from 'fs';
import { chromium } from 'playwright';

const cfg = JSON.parse(fs.readFileSync(process.env.SMOKE_INPUT, 'utf-8'));
const artifacts = cfg.artifacts;
const ensureDir = (p) => { if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true }); };
ensureDir(artifacts);

const fail = async (stage, reason, page) => {
  const stamp = Date.now();
  if (page) {
    try { await page.screenshot({ path: `${artifacts}/fail-${stamp}.png`, fullPage: true }); } catch {}
    try { const html = await page.content(); fs.writeFileSync(`${artifacts}/fail-${stamp}.html`, html); } catch {}
  }
  console.log(JSON.stringify({ stage, status: 'fail', reason }));
  process.exit(1);
};

const waitForRow = async (page, text) => {
  await page.waitForSelector(`tbody tr:has(td:text-is("${text}"))`, { timeout: cfg.timeoutMs });
  const rows = page.locator('tbody tr').filter({ has: page.getByText(text, { exact: true }) });
  return rows.nth(0);
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  try {
    await page.goto(cfg.baseUrl, { waitUntil: 'networkidle', timeout: cfg.timeoutMs });
    await page.waitForSelector('#add-item-btn', { timeout: cfg.timeoutMs });

    await page.click('#add-item-btn');
    await page.waitForSelector('#item-modal', { state: 'visible', timeout: cfg.timeoutMs });
    await page.fill('input[name="name"]', cfg.name);
    await page.fill('input[name="sku"]', cfg.sku);
    await page.selectOption('#item-type', cfg.itemType);
    await page.fill('input[name="qty"]', String(cfg.qty));
    await page.selectOption('#unit-system', cfg.unitSystem);
    await page.fill('input[name="unit"]', cfg.unit);
    await page.waitForTimeout(500);
    await page.fill('input[name="price"]', String(cfg.price));
    await page.fill('input[name="notes"], textarea[name="notes"]', cfg.notes).catch(() => {});
    await page.fill('input[name="location"]', cfg.location);
    const vendorSel = page.locator('#vendor-select');
    if (await vendorSel.count()) {
      await vendorSel.selectOption(String(cfg.vendorId)).catch(() => {});
    }
    await page.click('#save-btn');

    const row = await waitForRow(page, cfg.name);
    const cells = row.locator('td');
    const rowData = {
      name: await cells.nth(0).innerText(),
      sku: await cells.nth(1).innerText(),
      qty: await cells.nth(2).innerText(),
      vendor: await cells.nth(3).innerText(),
      price: await cells.nth(4).innerText(),
      location: await cells.nth(5).innerText()
    };
    if (!rowData.qty.includes('EA')) await fail('verify-create', `Qty unit missing (got ${rowData.qty})`, page);
    if (!rowData.price.includes('12.34')) await fail('verify-create', `Price mismatch (got ${rowData.price})`, page);
    if (cfg.vendorName && !rowData.vendor.includes(cfg.vendorName) && !rowData.vendor.includes(String(cfg.vendorId))) {
      await fail('verify-create', `Vendor mismatch (got ${rowData.vendor})`, page);
    }
    if (rowData.location.trim() !== cfg.location) await fail('verify-create', `Location mismatch (got ${rowData.location})`, page);

    await row.locator('button.edit-btn').click();
    await page.waitForSelector('#item-modal', { state: 'visible', timeout: cfg.timeoutMs });
    await page.fill('input[name="qty"]', String(cfg.editedQty));
    await page.fill('input[name="price"]', String(cfg.editedPrice));
    await page.fill('input[name="location"]', cfg.editedLocation);
    const notesField = page.locator('input[name="notes"], textarea[name="notes"]');
    if (await notesField.count()) {
      const existing = await notesField.inputValue();
      await notesField.fill(existing + ' + edited');
    }
    await page.click('#save-btn');

    const editedRow = await waitForRow(page, cfg.name);
    const editedCells = editedRow.locator('td');
    const edited = {
      qty: await editedCells.nth(2).innerText(),
      price: await editedCells.nth(4).innerText(),
      location: await editedCells.nth(5).innerText()
    };
    if (!edited.qty.startsWith(String(cfg.editedQty))) await fail('verify-edit', `Qty not updated (${edited.qty})`, page);
    if (!edited.price.includes(String(cfg.editedPrice))) await fail('verify-edit', `Price not updated (${edited.price})`, page);
    if (edited.location.trim() !== cfg.editedLocation) await fail('verify-edit', `Location not updated (${edited.location})`, page);

    const locFilter = page.locator('#location-filter');
    await locFilter.selectOption(cfg.editedLocation).catch(() => {});
    await page.waitForTimeout(500);
    const filteredRows = await page.locator('tbody tr').count();
    if (filteredRows < 1) await fail('filter', 'Edited item missing after filtering', page);
    const mismatched = await page.locator('tbody tr').evaluateAll((rows, expected) => rows.filter(r => (r.cells?.[5]?.textContent?.trim() || '') !== expected).length, cfg.editedLocation);
    if (mismatched > 0) await fail('filter', 'Non-matching locations visible after filter', page);
    await locFilter.selectOption('');
    await page.waitForTimeout(300);

    console.log(JSON.stringify({ status: 'ok', name: cfg.name }));
    await browser.close();
  } catch (err) {
    await fail('playwright', err.message, page);
  }
})();
"@
$pwPath = Join-Path $artifacts 'smoke-playwright.mjs'
Set-Content -Path $pwPath -Value $pwScript -Encoding UTF8

$env:SMOKE_INPUT = $inputPath
try {
    npx --yes playwright install chromium > $null 2>&1
    $node = Get-Command node -ErrorAction Stop
    $pwResult = & $node.Path $pwPath 2>&1
} catch {
    Emit-Failure -Stage 'Stage D' -Reason $_.Exception.Message -ArtifactsDir $artifacts
}

if ($LASTEXITCODE -ne 0) {
    Emit-Failure -Stage 'Stage D' -Reason ($pwResult | Out-String) -ArtifactsDir $artifacts
}

try { $pwJson = $pwResult | ConvertFrom-Json } catch { Emit-Failure -Stage 'Stage D' -Reason 'Playwright did not return JSON' -ArtifactsDir $artifacts }
if ($pwJson.status -ne 'ok') { Emit-Failure -Stage 'Stage D' -Reason ($pwResult | Out-String) -ArtifactsDir $artifacts }

# --- Stage E: DB persistence
Write-Stage "Stage E: DB persistence"
$beforeDelete = Invoke-SqliteQuery -DbPath $appDb -Sql "SELECT id, sku, qty, unit, price, notes, type, vendor_id, location FROM items WHERE name=@n" -Parameters @{ '@n' = $itemName }
if ($beforeDelete.Count -lt 1) { Emit-Failure -Stage 'Stage E' -Reason 'Item missing in DB after UI create/edit' -ArtifactsDir $artifacts }
$itemRow = $beforeDelete[0]
Write-Info ("DB row captured: id={0}, location={1}" -f $itemRow.id, $itemRow.location)

if ($itemRow.sku -ne $itemSku -or [double]$itemRow.qty -ne 3 -or [double]$itemRow.price -ne 2) {
    Emit-Failure -Stage 'Stage E' -Reason 'DB values do not match edited state' -ArtifactsDir $artifacts
}
if ($itemRow.location -ne $itemLocationEdited) { Emit-Failure -Stage 'Stage E' -Reason 'DB location mismatch' -ArtifactsDir $artifacts }
if ($itemRow.unit -ne 'ea') { Emit-Failure -Stage 'Stage E' -Reason 'DB unit mismatch' -ArtifactsDir $artifacts }
if ($itemRow.vendor_id -ne $vendorId) { Emit-Failure -Stage 'Stage E' -Reason 'DB vendor mismatch' -ArtifactsDir $artifacts }
if ($itemRow.type -ne $playwrightInput.itemType) { Emit-Failure -Stage 'Stage E' -Reason 'DB type mismatch' -ArtifactsDir $artifacts }
if (-not ($itemRow.notes -like "*$itemNotes*edited*")) { Emit-Failure -Stage 'Stage E' -Reason 'DB notes mismatch' -ArtifactsDir $artifacts }

# delete via UI to validate removal
$deleteScript = @"
import fs from 'fs';
import { chromium } from 'playwright';

const cfg = JSON.parse(fs.readFileSync(process.env.SMOKE_INPUT, 'utf-8'));
const artifacts = cfg.artifacts;
const fail = async (stage, reason, page) => {
  const stamp = Date.now();
  if (page) {
    try { await page.screenshot({ path: `${artifacts}/fail-${stamp}.png`, fullPage: true }); } catch {}
    try { const html = await page.content(); fs.writeFileSync(`${artifacts}/fail-${stamp}.html`, html); } catch {}
  }
  console.log(JSON.stringify({ stage, status: 'fail', reason }));
  process.exit(1);
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  try {
    await page.goto(cfg.baseUrl, { waitUntil: 'networkidle', timeout: cfg.timeoutMs });
    const row = page.locator('tbody tr').filter({ has: page.getByText(cfg.name, { exact: true }) }).first();
    await row.waitFor({ state: 'visible', timeout: cfg.timeoutMs });
    await row.locator('button.delete-btn').click();
    await page.waitForTimeout(500);
    const stillThere = await page.locator('tbody tr').filter({ has: page.getByText(cfg.name, { exact: true }) }).count();
    if (stillThere > 0) await fail('delete', 'Row not removed after delete', page);
    console.log(JSON.stringify({ status: 'deleted' }));
    await browser.close();
  } catch (err) {
    await fail('delete', err.message, page);
  }
})();
"@
$deletePath = Join-Path $artifacts 'smoke-delete.mjs'
Set-Content -Path $deletePath -Value $deleteScript -Encoding UTF8
$pwDeleteResult = & $node.Path $deletePath 2>&1
if ($LASTEXITCODE -ne 0) { Emit-Failure -Stage 'Stage D' -Reason ($pwDeleteResult | Out-String) -ArtifactsDir $artifacts }
try { $delJson = $pwDeleteResult | ConvertFrom-Json } catch { Emit-Failure -Stage 'Stage D' -Reason 'Delete step missing JSON' -ArtifactsDir $artifacts }
if ($delJson.status -ne 'deleted') { Emit-Failure -Stage 'Stage D' -Reason ($pwDeleteResult | Out-String) -ArtifactsDir $artifacts }

$deleted = Invoke-SqliteQuery -DbPath $appDb -Sql "SELECT id FROM items WHERE name=@n" -Parameters @{ '@n' = $itemName }
if ($deleted.Count -gt 0) { Emit-Failure -Stage 'Stage E' -Reason 'Item still present in DB after delete' -ArtifactsDir $artifacts }

$dbAfter = Get-Item $appDb
Write-Info ("DB last write (after CRUD): {0}" -f $dbAfter.LastWriteTime)

# --- Stage F: optional restart if smoke started server
if ($serverStartedBySmoke) {
    Write-Stage "Stage F: server restart"
    try {
        $procList = Get-Process -Name 'uvicorn' -ErrorAction SilentlyContinue
        foreach ($p in $procList) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    } catch {}
    if (-not (Wait-ForServer -TimeoutSec 5)) {
        $python = (Get-Command python -ErrorAction SilentlyContinue)?.Path
        if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue)?.Path }
        if ($python) {
            Start-Process $python -ArgumentList @('-m','uvicorn','core.api.http:create_app','--factory','--host',$baseUri.Host,'--port',$baseUri.Port) -WorkingDirectory $repoRoot -WindowStyle Hidden | Out-Null
            if (-not (Wait-ForServer -TimeoutSec 30)) { Emit-Failure -Stage 'Stage F' -Reason 'Server failed to restart' -ArtifactsDir $artifacts }
        }
    }
    if (-not (Wait-ForServer -TimeoutSec 30)) { Emit-Failure -Stage 'Stage F' -Reason 'Server not ready after restart' -ArtifactsDir $artifacts }
    $itemsAfterRestart = Invoke-SmokeRequest -Method GET -Path '/app/items' -Headers $headers
    if ($itemsAfterRestart.Status -ne 200) { Emit-Failure -Stage 'Stage F' -Reason 'Items fetch failed after restart' -ArtifactsDir $artifacts }
    try {
        $afterList = ConvertFrom-Json $itemsAfterRestart.Body
        $found = $afterList | Where-Object { $_.name -eq $itemName }
        if ($found) { Emit-Failure -Stage 'Stage F' -Reason 'Deleted item reappeared after restart' -ArtifactsDir $artifacts }
    } catch { Emit-Failure -Stage 'Stage F' -Reason 'Items parse failed after restart' -ArtifactsDir $artifacts }
}

# --- Stage G: cleanup
Write-Stage "Stage G: cleanup"
if (Test-Path $appDb) {
    Invoke-SqliteNonQuery -DbPath $appDb -Sql "DELETE FROM items WHERE name LIKE 'SMK_%' OR sku LIKE 'SMK_%'" | Out-Null
    Invoke-SqliteNonQuery -DbPath $appDb -Sql "DELETE FROM vendors WHERE name LIKE 'SMK_%'" | Out-Null
} else {
    Write-Warn "Cleanup skipped; DB not found"
}

if ($serverStartedBySmoke) {
    try {
        $procList = Get-Process -Name 'uvicorn' -ErrorAction SilentlyContinue
        foreach ($p in $procList) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    } catch {}
}

Write-Stage "Stage H: reporting"
Write-Output "SMOKE PASS"
exit 0
