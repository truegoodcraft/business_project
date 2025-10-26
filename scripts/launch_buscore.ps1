# Your ops vault—safe boot every time.
param(
    [switch]$Crawl
)

$ErrorActionPreference = 'Stop'

function Test-Python311 {
    try {
        $versionText = (& python --version 2>&1).Trim()
        if (-not $versionText) { return $false }
        $parts = $versionText.Split()[1]
        $ver = [version]$parts
        return ($ver.Major -eq 3 -and $ver.Minor -ge 11)
    } catch {
        return $false
    }
}

try {
    $localRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'BUSCore'
    $deployRoot = Join-Path $localRoot 'app'
    $AppRoot = Join-Path $deployRoot 'business_project-main'
    New-Item -ItemType Directory -Force -Path $localRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $deployRoot | Out-Null

    $ZipPath = Join-Path $env:TEMP 'tgc.zip'
    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

    $ZipExtractRoot = Join-Path $env:TEMP 'tgc_extract'
    if (Test-Path $ZipExtractRoot) { Remove-Item $ZipExtractRoot -Recurse -Force }

    $owner = 'truegoodcraft'
    $repo = 'business_project'
    $zipUrl = "https://github.com/$owner/$repo/archive/refs/heads/main.zip"
    Write-Host "Downloading $zipUrl..."
    Invoke-WebRequest -Uri $zipUrl -OutFile $ZipPath -UseBasicParsing | Out-Null

    Write-Host "Unpacking payload..."
    Expand-Archive -Path $ZipPath -DestinationPath $ZipExtractRoot -Force
    $ZipDir = Join-Path $ZipExtractRoot "$repo-main"
    if (-not (Test-Path $ZipDir)) { throw "Could not locate unpacked repository under $ZipExtractRoot" }

    # Ensure target root exists
    New-Item -ItemType Directory -Path $AppRoot -Force | Out-Null

    # Create data dir if missing, but DO NOT modify its contents
    New-Item -ItemType Directory -Path (Join-Path $AppRoot "data") -Force | Out-Null

    # Mirror payload to app root EXCLUDING data folder and app.db
    # Also exclude VCS and dev-only dirs if present
    $src = $ZipDir
    $dst = $AppRoot
    Write-Host "[sync] Mirroring payload → $dst (preserving \data and app.db)"
    $rc = robocopy $src $dst /MIR /XF app.db /XD data .git .github tests node_modules 2>$null
    if ($LASTEXITCODE -ge 8) {
      throw "robocopy failed with code $LASTEXITCODE"
    }

    # ESM entry enforcement (keep from earlier steps)
    $UiDir     = if ($env:BUS_UI_DIR) { $env:BUS_UI_DIR } else { Join-Path $AppRoot "core\ui" }
    $IndexHtml = Join-Path $UiDir "index.html"
    $ShellHtml = Join-Path $UiDir "shell.html"
    Write-Host "[ui] Serving UI from: $UiDir"
    if (Test-Path $IndexHtml) {
      try { Rename-Item -Path $IndexHtml -NewName "index_legacy.html" -Force; Write-Host "[ui] Archived legacy entry: index.html → index_legacy.html" }
      catch { Write-Host "[ui] Archive skipped: $($_.Exception.Message)" }
    }
    if (-not (Test-Path $ShellHtml)) { throw "[ui] Missing shell.html in $UiDir" }
    $env:BUS_UI_DIR = $UiDir
    $EntryUrl = "http://127.0.0.1:8765/ui/shell.html"
    Write-Host "[ui] Entry enforced: /ui/shell.html"
    Write-Host "[ui] Opening: $EntryUrl"
    Start-Process $EntryUrl

    Remove-Item $ZipPath -Force
    Remove-Item $ZipExtractRoot -Recurse -Force

    $appRoot = $AppRoot
    Write-Host "Repository ready at $appRoot"

    if (-not (Test-Python311)) {
        $response = Read-Host 'Python 3.11+ not detected. Install Python 3.11 now? (Y/N)'
        if ($response -match '^[Yy]') {
            winget install --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
            if (-not (Test-Python311)) { throw 'Python installation did not complete. Reopen PowerShell after install.' }
        } else {
            throw 'Python 3.11+ is required.'
        }
    }

    $venvPath = Join-Path $deployRoot 'venv'
    if (!(Test-Path $venvPath)) {
        Write-Host 'Creating virtual environment...'
        python -m venv $venvPath
    }

    $venvPython = Join-Path $venvPath 'Scripts\python.exe'
    if (!(Test-Path $venvPython)) { throw "Virtual environment python not found at $venvPython" }

    Write-Host 'Installing dependencies...'
    & $venvPython -m pip install --upgrade pip | Out-Null
    $requirements = Join-Path $appRoot 'requirements.txt'
    if (Test-Path $requirements) {
        & $venvPython -m pip install -q -r $requirements
    }

    $uiSource = Join-Path $appRoot 'core\ui'
    $uiTarget = Join-Path $deployRoot 'app\ui'
    if (Test-Path $uiSource) {
        New-Item -ItemType Directory -Force -Path $uiTarget | Out-Null
        robocopy $uiSource $uiTarget /MIR /XO /R:3 /W:5 | Out-Null
        if ($LASTEXITCODE -gt 7) {
            Write-Warning 'UI mirror partial—check paths.'
        }
    }

    $uvicornCmd = "& `"$venvPython`" -m uvicorn app:app --host 127.0.0.1 --port 8765 --reload --log-level info"
    Write-Host 'Launching BUS Core service...'
    Start-Process powershell -ArgumentList '-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-Command',$uvicornCmd -WorkingDirectory $appRoot -WindowStyle Hidden | Out-Null

    $baseUrl = 'http://127.0.0.1:8765'
    $token = $null
    for ($i = 0; $i -lt 20 -and -not $token; $i++) {
        try {
            $token = (Invoke-RestMethod "$baseUrl/session/token").token
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $token) { throw "Unable to acquire session token from $baseUrl" }

    $headers = @{ 'X-Session-Token' = $token; 'Content-Type' = 'application/json' }
    $disableBody = @{ enabled = $false } | ConvertTo-Json -Compress
    Invoke-RestMethod "$baseUrl/dev/writes" -Method POST -Headers $headers -Body $disableBody | Out-Null
    Write-Host 'Writes disabled for this session.'

    Start-Sleep -Seconds 5
    Start-Process $EntryUrl | Out-Null

    if ($Crawl) {
        Write-Host 'Crawl probe starting...'
        $reader = Invoke-RestMethod "$baseUrl/settings/reader" -Headers @{ 'X-Session-Token' = $token }
        $roots = $reader.local_roots
        foreach ($root in $roots) {
            $renamePlan = Invoke-RestMethod "$baseUrl/organizer/rename/plan" -Method POST -Headers $headers -Body (@{ start_path = $root } | ConvertTo-Json -Compress)
            $dupePlan = Invoke-RestMethod "$baseUrl/organizer/duplicates/plan" -Method POST -Headers $headers -Body (@{ start_path = $root } | ConvertTo-Json -Compress)
            Write-Host "Probed $root: $($renamePlan.plan_id) renames, $($dupePlan.plan_id) dupes."
        }
        Write-Host 'Crawl probe complete.'
    }

    Write-Host 'BUS Core v0.2 bootstrap ready.'
} catch {
    Write-Error $_
    exit 1
}
