param(
  [string]$Version = "",
  [string]$Name    = "BUS-Core",
  [string]$Company = "True Good Craft",
  [string]$Product = "TGC BUS Core",
  [string]$Desc    = "Local-first Business Utility System Core (AGPL) by True Good Craft",
  [switch]$Sign,
  [switch]$Bundle,
  [switch]$Release,
  [string]$SignerThumbprint = "55474aa9a2d562022a6590d487045e069457f985",
  [string]$TimestampUrl = "http://timestamp.digicert.com",
  [string]$SignToolPath = "signtool"
)

$ErrorActionPreference = "Stop"

if ($Release) {
  $Sign = $true
  $Bundle = $true
}

function Normalize-Thumbprint {
  param([string]$Thumbprint)

  return (($Thumbprint -replace "\s", "").ToUpperInvariant())
}

function Assert-ValidSignature {
  param(
    [string]$Path,
    [string]$ExpectedThumbprint
  )

  $signature = Get-AuthenticodeSignature -FilePath $Path
  if ($signature.Status -ne "Valid") {
    throw "Signature verification failed for '$Path': $($signature.Status) $($signature.StatusMessage)"
  }

  if ($null -eq $signature.SignerCertificate) {
    throw "Signature verification failed for '$Path': missing signer certificate."
  }

  $actualThumbprint = Normalize-Thumbprint $signature.SignerCertificate.Thumbprint
  $expectedNormalized = Normalize-Thumbprint $ExpectedThumbprint
  if ($actualThumbprint -ne $expectedNormalized) {
    throw "Signature verification failed for '$Path': signer thumbprint '$actualThumbprint' did not match expected '$expectedNormalized'."
  }
}

function New-ReleaseBundle {
  param(
    [string]$VersionedExe,
    [string]$ReadmePath,
    [string]$LicensePath,
    [string]$DistPath,
    [string]$BundleName
  )

  if (!(Test-Path $VersionedExe -PathType Leaf)) {
    throw "Cannot bundle: versioned EXE not found: $VersionedExe"
  }
  if (!(Test-Path $ReadmePath -PathType Leaf)) {
    throw "Cannot bundle: README.md not found: $ReadmePath"
  }
  if (!(Test-Path $LicensePath -PathType Container)) {
    throw "Cannot bundle: license folder not found: $LicensePath"
  }

  $bundleRoot = Join-Path $DistPath "_bundle"
  $stagePath = Join-Path $bundleRoot $BundleName
  $zipPath = Join-Path $DistPath "$BundleName.zip"

  Remove-Item -Recurse -Force $stagePath -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Path $stagePath -Force | Out-Null

  Copy-Item $VersionedExe (Join-Path $stagePath (Split-Path -Leaf $VersionedExe)) -Force
  Copy-Item $ReadmePath (Join-Path $stagePath "README.md") -Force
  Copy-Item $LicensePath (Join-Path $stagePath "license") -Recurse -Force

  Remove-Item -Force $zipPath -ErrorAction SilentlyContinue
  Compress-Archive -Path (Join-Path $stagePath "*") -DestinationPath $zipPath -Force

  $archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
  try {
    $rootEntries = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $rootExeCount = 0
    $rootReadmeCount = 0
    $licenseFileCount = 0
    $expectedExeName = Split-Path -Leaf $VersionedExe

    foreach ($entry in $archive.Entries) {
      $entryPath = $entry.FullName.Replace("\", "/")
      $parts = $entryPath.Split("/", [System.StringSplitOptions]::RemoveEmptyEntries)
      if ($parts.Count -eq 0) { continue }

      [void]$rootEntries.Add($parts[0])

      if ($parts.Count -eq 1 -and $parts[0] -eq $expectedExeName) {
        $rootExeCount++
      } elseif ($parts.Count -eq 1 -and $parts[0] -eq "README.md") {
        $rootReadmeCount++
      } elseif ($parts.Count -gt 1 -and $parts[0] -eq "license" -and -not [string]::IsNullOrEmpty($entry.Name)) {
        $licenseFileCount++
      }
    }

    $allowedRoots = @($expectedExeName, "README.md", "license")
    foreach ($rootEntry in $rootEntries) {
      if ($allowedRoots -notcontains $rootEntry) {
        throw "Bundle verification failed for '$zipPath': unexpected root entry '$rootEntry'."
      }
    }
    if ($rootExeCount -ne 1) {
      throw "Bundle verification failed for '$zipPath': expected one root '$expectedExeName' entry, found $rootExeCount."
    }
    if ($rootReadmeCount -ne 1) {
      throw "Bundle verification failed for '$zipPath': expected one root 'README.md' entry, found $rootReadmeCount."
    }
    if ($licenseFileCount -lt 1) {
      throw "Bundle verification failed for '$zipPath': expected at least one file under 'license/'."
    }
  } finally {
    $archive.Dispose()
  }

  return $zipPath
}

# -----------------------------
# Repo root
# -----------------------------
$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

$DIST = Join-Path $ROOT "dist"
$BUILD = Join-Path $ROOT "build"

Write-Host "[INFO] BUS Core build starting" -ForegroundColor Cyan
Write-Host "[INFO] Root: $ROOT" -ForegroundColor DarkGray

# -----------------------------
# Pre-flight
# -----------------------------
$spec = Join-Path $ROOT "$Name.spec"
if (!(Test-Path $spec)) {
  throw "Spec not found: $spec`nExpected '$Name.spec' at repo root."
}

# -----------------------------
# Clean build outputs
# -----------------------------
Write-Host "[INFO] Cleaning previous builds" -ForegroundColor Cyan
Remove-Item -Recurse -Force $BUILD -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $DIST  -ErrorAction SilentlyContinue

# -----------------------------
# Env (prod mode)
# -----------------------------
$env:BUS_DEV = "0"
$env:APP_VERSION = $Version

# -----------------------------
# Ensure PyInstaller is available
# -----------------------------
# Prefer existing venv if present; do not auto-nuke unless you want that policy.
$venvPy = Join-Path $ROOT ".venv\Scripts\python.exe"
if (!(Test-Path $venvPy)) {
  throw "Missing venv at .venv. Create it once, then reuse.`nExpected: $venvPy"
}

$pyMM = (& $venvPy -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if ($pyMM -ne "3.11") {
  throw "Build venv must be Python 3.11.x (got $pyMM). Recreate .venv with: py -3.11 -m venv .venv"
}

$isExplicitVersion = -not [string]::IsNullOrWhiteSpace($Version)
if (-not $isExplicitVersion) {
  $Version = (& $venvPy -c "from core.version import VERSION; print(VERSION)").Trim()
  if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "Failed to read canonical version from core/version.py (got empty)."
  }
  Write-Host "[INFO] Using build version: $Version (from canonical core version)" -ForegroundColor DarkGray
} else {
  Write-Host "[INFO] Using build version: $Version (explicit override)" -ForegroundColor DarkGray
}

# Ensure version is X.Y.Z
$verParts = $Version.Split(".")
if ($verParts.Count -ne 3) { throw "Version must be X.Y.Z (got '$Version')" }
$VMAJOR = [int]$verParts[0]
$VMINOR = [int]$verParts[1]
$VPATCH = [int]$verParts[2]

# Ensure pyinstaller exists in the venv
& $venvPy -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "[INFO] Installing PyInstaller into .venv" -ForegroundColor Cyan
  & $venvPy -m pip install --upgrade pyinstaller
}

# -----------------------------
# Write Windows version-info file (Explorer metadata)
# -----------------------------
$versionFile = Join-Path $ROOT "scripts\_win_version_info.txt"
$year = (Get-Date).Year

@"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($VMAJOR, $VMINOR, $VPATCH, 0),
    prodvers=($VMAJOR, $VMINOR, $VPATCH, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x4,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '$Company'),
          StringStruct('FileDescription', '$Desc'),
          StringStruct('FileVersion', '$Version'),
          StringStruct('InternalName', '$Name'),
          StringStruct('LegalCopyright', 'Copyright (c) $year $Company'),
          StringStruct('OriginalFilename', '$Name.exe'),
          StringStruct('ProductName', '$Product'),
          StringStruct('ProductVersion', '$Version')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@ | Set-Content -Encoding UTF8 $versionFile

Write-Host "[INFO] Version info written: $versionFile" -ForegroundColor DarkGray

# -----------------------------
# Build via SPEC (canonical)
# -----------------------------
Write-Host "[INFO] Running PyInstaller (SPEC, expected ONEFILE)" -ForegroundColor Cyan
& $venvPy -m PyInstaller `
  --noconfirm `
  --clean `
  $spec

# -----------------------------
# Post: Validate onefile output
# -----------------------------
$exeOut = Join-Path $DIST "$Name.exe"
if (!(Test-Path $exeOut)) {
  Write-Host "[INFO] Dist contents:" -ForegroundColor Yellow
  if (Test-Path $DIST) { Get-ChildItem $DIST | Format-Table Name, Mode, Length }
  throw "Build failed: expected onefile EXE not found at: $exeOut"
}

# Hard fail if onedir artifacts exist (this prevents the exact bug you hit)
$onedirPath = Join-Path $DIST $Name
$internalPath = Join-Path $onedirPath "_internal"
if (Test-Path $internalPath) {
  throw "Build produced ONEDIR artifacts ($internalPath). Expected ONEFILE only. Fix the .spec (remove COLLECT and exclude_binaries)."
}

# Optional: rename output to include version (keeps releases sane)
$finalExe = Join-Path $DIST "$Name-$Version.exe"
$VersionedExe = $finalExe
Copy-Item $exeOut $VersionedExe -Force

$zipOut = $null

if ($Sign) {
  Write-Host "[INFO] Signing versioned EXE" -ForegroundColor Cyan
  & $SignToolPath sign `
    /fd SHA256 `
    /tr $TimestampUrl `
    /td SHA256 `
    /sha1 $SignerThumbprint `
    $VersionedExe

  if ($LASTEXITCODE -ne 0) {
    throw "Signing failed for: $VersionedExe"
  }

  Assert-ValidSignature -Path $VersionedExe -ExpectedThumbprint $SignerThumbprint

  & $SignToolPath verify /pa /all /v $VersionedExe
  if ($LASTEXITCODE -ne 0) {
    throw "signtool verification failed for: $VersionedExe"
  }
}

if ($Bundle) {
  $zipOut = New-ReleaseBundle `
    -VersionedExe $VersionedExe `
    -ReadmePath (Join-Path $ROOT "README.md") `
    -LicensePath (Join-Path $ROOT "license") `
    -DistPath $DIST `
    -BundleName "$Name-$Version"
}

Write-Host "[PASS] Build complete (ONEFILE): $VersionedExe" -ForegroundColor Green
if ($Sign) {
  Write-Host "[PASS] Signature verified: $VersionedExe" -ForegroundColor Green
}
if ($Bundle) {
  Write-Host "[PASS] Bundle complete: $zipOut" -ForegroundColor Green
}

Write-Host ""
Write-Host "Artifacts:" -ForegroundColor Cyan
Write-Host "  EXE: $VersionedExe"
if ($Bundle) {
  Write-Host "  ZIP: $zipOut"
}
