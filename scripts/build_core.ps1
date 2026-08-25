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
  [string]$SignToolPath = "signtool",
  [string]$BuildPythonPath = ""
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

function Invoke-NativeChecked {
  param(
    [string]$FilePath,
    [string[]]$Arguments,
    [string]$Description
  )

  # Windows PowerShell can promote native stderr to NativeCommandError when the
  # global preference is Stop. Preserve the output and judge native success only
  # by the process exit code.
  $previousPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    & $FilePath @Arguments 2>&1 | ForEach-Object { Write-Host $_ }
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousPreference
  }

  if ($exitCode -ne 0) {
    throw "$Description failed with exit code $exitCode."
  }
}

function Invoke-NativeCapture {
  param(
    [string]$FilePath,
    [string[]]$Arguments,
    [string]$Description
  )

  $previousPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    $output = @(& $FilePath @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousPreference
  }

  if ($exitCode -ne 0) {
    $details = ($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
    throw "$Description failed with exit code $exitCode.`n$details"
  }

  return (($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine).Trim()
}

function Assert-OnefileArchive {
  param(
    [string]$PythonPath,
    [string]$VerifierPath,
    [string]$ExecutablePath
  )

  Invoke-NativeChecked `
    -FilePath $PythonPath `
    -Arguments @($VerifierPath, "exe", $ExecutablePath) `
    -Description "Onefile archive verification for '$ExecutablePath'"
}

function Assert-LaunchSmoke {
  param(
    [string]$ExecutablePath,
    [string]$SmokeRoot,
    [string]$Label
  )

  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  $listener.Start()
  $port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
  $listener.Stop()

  $localAppData = Join-Path $SmokeRoot $Label
  $configRoot = Join-Path $localAppData "BUSCore"
  New-Item -ItemType Directory -Path $configRoot -Force | Out-Null
  $smokeConfig = '{"launcher":{"auto_start_in_tray":true},"updates":{"verified_launch_policy":"current_only"}}'
  [System.IO.File]::WriteAllText(
    (Join-Path $configRoot "config.json"),
    $smokeConfig,
    [System.Text.UTF8Encoding]::new($false)
  )

  $savedLocalAppData = $env:LOCALAPPDATA
  $savedBusMode = $env:BUS_MODE
  $savedBusDb = $env:BUS_DB
  $process = $null
  try {
    $env:LOCALAPPDATA = $localAppData
    $env:BUS_MODE = "demo"
    Remove-Item Env:BUS_DB -ErrorAction SilentlyContinue

    $process = Start-Process `
      -FilePath $ExecutablePath `
      -ArgumentList @("--port", $port) `
      -PassThru `
      -WindowStyle Hidden

    # A newly-created executable can incur a one-time Windows Defender scan.
    # Keep the smoke bounded while allowing a genuinely cold onefile launch.
    $deadline = [DateTime]::UtcNow.AddSeconds(120)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline) {
      Start-Sleep -Milliseconds 500
      if ($process.HasExited) {
        throw "Launch smoke '$Label' exited early with code $($process.ExitCode): $ExecutablePath"
      }
      try {
        $response = Invoke-WebRequest `
          -Uri "http://127.0.0.1:$port/ui/shell.html" `
          -UseBasicParsing `
          -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
          $ready = $true
          break
        }
      } catch {
        # Startup may still be extracting the onefile archive or initializing the DB.
      }
    }

    if (-not $ready) {
      throw "Launch smoke '$Label' timed out waiting for the UI: $ExecutablePath"
    }
    Write-Host "[PASS] Launch smoke ($Label): HTTP 200 on port $port" -ForegroundColor Green
  } finally {
    if ($null -ne $process -and -not $process.HasExited) {
      $previousPreference = $ErrorActionPreference
      try {
        $ErrorActionPreference = "Continue"
        & taskkill.exe /PID $process.Id /T /F *> $null
      } finally {
        $ErrorActionPreference = $previousPreference
      }
    }
    $env:LOCALAPPDATA = $savedLocalAppData
    $env:BUS_MODE = $savedBusMode
    if ($null -eq $savedBusDb) {
      Remove-Item Env:BUS_DB -ErrorAction SilentlyContinue
    } else {
      $env:BUS_DB = $savedBusDb
    }
  }
}

function New-ReleaseBundle {
  param(
    [string]$VersionedExe,
    [string]$ReadmePath,
    [string]$LicensePath,
    [string]$SotPath,
    [string]$DistPath,
    [string]$BundleName,
    [string]$PythonPath,
    [string]$VerifierPath
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
  if (!(Test-Path $SotPath -PathType Leaf)) {
    throw "Cannot bundle: SOT.md not found: $SotPath"
  }

  $bundleRoot = Join-Path $DistPath "_bundle"
  $stagePath = Join-Path $bundleRoot $BundleName
  $zipPath = Join-Path $DistPath "$BundleName.zip"

  Remove-Item -Recurse -Force $stagePath -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Path $stagePath -Force | Out-Null

  Copy-Item $VersionedExe (Join-Path $stagePath (Split-Path -Leaf $VersionedExe)) -Force
  Copy-Item $ReadmePath (Join-Path $stagePath "README.md") -Force
  Copy-Item $LicensePath (Join-Path $stagePath "license") -Recurse -Force
  Copy-Item $SotPath (Join-Path $stagePath "license\SOT.md") -Force

  Remove-Item -Force $zipPath -ErrorAction SilentlyContinue
  Compress-Archive -Path (Join-Path $stagePath "*") -DestinationPath $zipPath -Force

  $archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
  try {
    $rootEntries = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $rootExeCount = 0
    $rootReadmeCount = 0
    $licenseFileCount = 0
    $licenseSotCount = 0
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
        if ($entryPath -eq "license/SOT.md") {
          $licenseSotCount++
        }
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
    if ($licenseSotCount -ne 1) {
      throw "Bundle verification failed for '$zipPath': expected one 'license/SOT.md' entry, found $licenseSotCount."
    }
  } finally {
    $archive.Dispose()
  }

  Invoke-NativeChecked `
    -FilePath $PythonPath `
    -Arguments @(
      $VerifierPath,
      "zip",
      $zipPath,
      "--expected-exe",
      $expectedExeName,
      "--expected-exe-source",
      $VersionedExe
    ) `
    -Description "Release ZIP verification for '$zipPath'"

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

$buildLock = Join-Path $ROOT "requirements-windows.lock.txt"
$artifactVerifier = Join-Path $ROOT "scripts\verify_release_artifact.py"
if (!(Test-Path $buildLock -PathType Leaf)) {
  throw "Governed Windows build lock not found: $buildLock"
}
if (!(Test-Path $artifactVerifier -PathType Leaf)) {
  throw "Release artifact verifier not found: $artifactVerifier"
}

# -----------------------------
# Env (prod mode)
# -----------------------------
$env:BUS_DEV = "0"
$env:APP_VERSION = $Version

# -----------------------------
# Ensure PyInstaller is available
# -----------------------------
# Prefer the repository venv, while allowing an explicit isolated Python 3.11
# environment for reproducible build agents and forensic rebuilds.
$venvPy = if ([string]::IsNullOrWhiteSpace($BuildPythonPath)) {
  Join-Path $ROOT ".venv\Scripts\python.exe"
} else {
  $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($BuildPythonPath)
}
if (!(Test-Path $venvPy)) {
  throw "Build Python not found. Create a Python 3.11 venv or pass -BuildPythonPath.`nExpected: $venvPy"
}

$pyMM = Invoke-NativeCapture `
  -FilePath $venvPy `
  -Arguments @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") `
  -Description "Build Python version probe"
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

# Install the governed runtime and build graph. The lock contains exact
# versions and reviewed distribution hashes for the Python 3.11 Windows target.
Write-Host "[INFO] Ensuring governed build dependencies" -ForegroundColor Cyan
Invoke-NativeChecked `
  -FilePath $venvPy `
  -Arguments @("-m", "pip", "install", "--disable-pip-version-check", "--require-hashes", "-r", $buildLock) `
  -Description "Governed build dependency installation"
Invoke-NativeChecked `
  -FilePath $venvPy `
  -Arguments @("-m", "pip", "check") `
  -Description "Build dependency consistency check"

$pyInstallerVersion = Invoke-NativeCapture `
  -FilePath $venvPy `
  -Arguments @("-c", "import importlib.metadata as m; from PIL import Image; print(m.version('pyinstaller'))") `
  -Description "PyInstaller and Pillow dependency probe"
$expectedPyInstallerVersion = (
  Select-String -LiteralPath $buildLock -Pattern '^pyinstaller==([^\s\\]+)(?:\s+\\)?$'
).Matches.Groups[1].Value
if ([string]::IsNullOrWhiteSpace($expectedPyInstallerVersion)) {
  throw "requirements-windows.lock.txt must contain an exact pyinstaller==X.Y.Z pin."
}
if ($pyInstallerVersion -ne $expectedPyInstallerVersion) {
  throw "PyInstaller version drift: expected $expectedPyInstallerVersion, got $pyInstallerVersion."
}
Write-Host "[INFO] PyInstaller: $pyInstallerVersion (governed pin)" -ForegroundColor DarkGray

# -----------------------------
# Clean build outputs only after the environment is proven usable
# -----------------------------
Write-Host "[INFO] Cleaning previous builds" -ForegroundColor Cyan
Remove-Item -Recurse -Force $BUILD -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $DIST  -ErrorAction SilentlyContinue

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
Invoke-NativeChecked `
  -FilePath $venvPy `
  -Arguments @("-m", "PyInstaller", "--noconfirm", "--clean", $spec) `
  -Description "PyInstaller onefile build"

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

Assert-OnefileArchive `
  -PythonPath $venvPy `
  -VerifierPath $artifactVerifier `
  -ExecutablePath $exeOut

# Optional: rename output to include version (keeps releases sane)
$finalExe = Join-Path $DIST "$Name-$Version.exe"
$VersionedExe = $finalExe
Copy-Item $exeOut $VersionedExe -Force

$sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $exeOut).Hash
$versionedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $VersionedExe).Hash
if ($sourceHash -ne $versionedHash) {
  throw "Versioned copy hash mismatch before signing: '$VersionedExe'."
}
Assert-OnefileArchive `
  -PythonPath $venvPy `
  -VerifierPath $artifactVerifier `
  -ExecutablePath $VersionedExe
Assert-LaunchSmoke `
  -ExecutablePath $VersionedExe `
  -SmokeRoot (Join-Path $BUILD "launch-smoke") `
  -Label "unsigned-versioned"

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

  Assert-OnefileArchive `
    -PythonPath $venvPy `
    -VerifierPath $artifactVerifier `
    -ExecutablePath $VersionedExe
  Assert-LaunchSmoke `
    -ExecutablePath $VersionedExe `
    -SmokeRoot (Join-Path $BUILD "launch-smoke") `
    -Label "signed-versioned"
}

if ($Bundle) {
  $zipOut = New-ReleaseBundle `
    -VersionedExe $VersionedExe `
    -ReadmePath (Join-Path $ROOT "README.md") `
    -LicensePath (Join-Path $ROOT "license") `
    -SotPath (Join-Path $ROOT "SOT.md") `
    -DistPath $DIST `
    -BundleName "$Name-$Version" `
    -PythonPath $venvPy `
    -VerifierPath $artifactVerifier
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
