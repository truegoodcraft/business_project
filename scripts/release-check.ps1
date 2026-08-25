# SPDX-License-Identifier: AGPL-3.0-or-later
[CmdletBinding()]
param(
  [switch]$Release,
  [string]$BuildPythonPath = "",
  [string]$SignerThumbprint = "55474aa9a2d562022a6590d487045e069457f985",
  [string]$TimestampUrl = "http://timestamp.digicert.com",
  [string]$SignToolPath = "signtool"
)

$ErrorActionPreference = 'Stop'

function Normalize-Thumbprint {
  param([string]$Thumbprint)

  return (($Thumbprint -replace "\s", "").ToUpperInvariant())
}

function Invoke-NativeChecked {
  param(
    [string]$FilePath,
    [string[]]$Arguments,
    [string]$Description
  )

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

$Root = Split-Path -Parent $PSScriptRoot
$OriginalLocation = Get-Location

$SmokeScript = Join-Path $PSScriptRoot 'smoke_isolated.ps1'
$BuildScript = Join-Path $PSScriptRoot 'build_core.ps1'
$BuildLock = Join-Path $Root 'requirements-windows.lock.txt'
$TestLock = Join-Path $Root 'requirements-test-windows.lock.txt'
$SeedPython = if ([string]::IsNullOrWhiteSpace($BuildPythonPath)) {
  Join-Path $Root '.venv\Scripts\python.exe'
} else {
  $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($BuildPythonPath)
}
$DistDir = Join-Path $Root 'dist'

foreach ($requiredPath in @($SmokeScript, $BuildScript, $BuildLock, $TestLock)) {
  if (!(Test-Path $requiredPath -PathType Leaf)) {
    throw "Missing release-check input: $requiredPath"
  }
}
if (!(Test-Path $SeedPython -PathType Leaf)) {
  throw "Missing Python 3.11 seed environment: $SeedPython"
}

$PythonVersion = Invoke-NativeCapture `
  -FilePath $SeedPython `
  -Arguments @('-c', "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") `
  -Description 'Seed Python version probe'
if ($PythonVersion -ne '3.11') {
  throw "Release check requires Python 3.11.x (got $PythonVersion)."
}

$ModeLabel = if ($Release) { 'signed release' } else { 'unsigned developer' }
$TempVenvRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("buscore-release-check-{0}" -f [guid]::NewGuid().ToString())

try {
  Set-Location $Root
  Write-Host ("BUS Core Release Check ({0} mode)" -f $ModeLabel) -ForegroundColor Cyan
  Write-Host ("[INFO] Creating clean Python 3.11 environment: {0}" -f $TempVenvRoot) -ForegroundColor DarkGray
  Invoke-NativeChecked `
    -FilePath $SeedPython `
    -Arguments @('-m', 'venv', $TempVenvRoot) `
    -Description 'Clean release-check environment creation'

  $VenvPython = Join-Path $TempVenvRoot 'Scripts\python.exe'
  if (!(Test-Path $VenvPython -PathType Leaf)) {
    throw "Clean release-check Python was not created: $VenvPython"
  }

  Write-Host '[INFO] Installing governed Windows runtime/build graph' -ForegroundColor Cyan
  Invoke-NativeChecked `
    -FilePath $VenvPython `
    -Arguments @('-m', 'pip', 'install', '--disable-pip-version-check', '--require-hashes', '-r', $BuildLock) `
    -Description 'Governed Windows dependency installation'
  Write-Host '[INFO] Installing governed test graph' -ForegroundColor Cyan
  Invoke-NativeChecked `
    -FilePath $VenvPython `
    -Arguments @('-m', 'pip', 'install', '--disable-pip-version-check', '--require-hashes', '-r', $TestLock) `
    -Description 'Governed test dependency installation'
  Invoke-NativeChecked `
    -FilePath $VenvPython `
    -Arguments @('-m', 'pip', 'check') `
    -Description 'Dependency consistency check'

  $Version = Invoke-NativeCapture `
    -FilePath $VenvPython `
    -Arguments @('-c', 'from core.version import VERSION; print(VERSION)') `
    -Description 'Canonical version probe'
  if ([string]::IsNullOrWhiteSpace($Version)) {
    throw 'Failed to read canonical VERSION from core/version.py.'
  }
  Write-Host "[INFO] Canonical VERSION: $Version" -ForegroundColor DarkGray

  Write-Host '[INFO] Compiling Python sources' -ForegroundColor Cyan
  Invoke-NativeChecked `
    -FilePath $VenvPython `
    -Arguments @('-m', 'compileall', '-q', 'core', 'tgc', 'scripts', 'launcher.py') `
    -Description 'Python source compilation'

  Write-Host '[INFO] Running test suite' -ForegroundColor Cyan
  Invoke-NativeChecked `
    -FilePath $VenvPython `
    -Arguments @('-m', 'pytest', '-q') `
    -Description 'Test suite'

  Write-Host '[INFO] Running governance checks' -ForegroundColor Cyan
  Invoke-NativeChecked `
    -FilePath $VenvPython `
    -Arguments @((Join-Path $PSScriptRoot 'validate_version_governance.py')) `
    -Description 'Version governance validation'
  Invoke-NativeChecked `
    -FilePath $VenvPython `
    -Arguments @((Join-Path $PSScriptRoot 'validate_change_trace.py')) `
    -Description 'Change-trace validation'

  Write-Host '[INFO] Running isolated source smoke with the governed Python environment' -ForegroundColor Cyan
  $SmokeArguments = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $SmokeScript,
    '-PythonPath', $VenvPython
  )
  Invoke-NativeChecked `
    -FilePath 'powershell' `
    -Arguments $SmokeArguments `
    -Description "Smoke script failed: $SmokeScript"

  $BuildArguments = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $BuildScript,
    '-BuildPythonPath', $VenvPython
  )
  if ($Release) {
    $BuildArguments += @(
      '-Release',
      '-SignerThumbprint', $SignerThumbprint,
      '-TimestampUrl', $TimestampUrl,
      '-SignToolPath', $SignToolPath
    )
  }

  Write-Host ("[INFO] Running canonical {0} build" -f $ModeLabel) -ForegroundColor Cyan
  Invoke-NativeChecked `
    -FilePath 'powershell' `
    -Arguments $BuildArguments `
    -Description "Build script failed: $BuildScript"

  $PrimaryArtifact = Join-Path $DistDir 'BUS-Core.exe'
  $VersionedArtifact = Join-Path $DistDir ("BUS-Core-{0}.exe" -f $Version)

  if (!(Test-Path $PrimaryArtifact -PathType Leaf)) {
    throw "Missing primary build artifact: $PrimaryArtifact"
  }
  if (!(Test-Path $VersionedArtifact -PathType Leaf)) {
    throw "Missing versioned build artifact: $VersionedArtifact"
  }

  $VerifiedArtifacts = @($PrimaryArtifact, $VersionedArtifact)
  if ($Release) {
    $BundleArtifact = Join-Path $DistDir ("BUS-Core-{0}.zip" -f $Version)
    if (!(Test-Path $BundleArtifact -PathType Leaf)) {
      throw "Missing release bundle: $BundleArtifact"
    }

    $signature = Get-AuthenticodeSignature -FilePath $VersionedArtifact
    if ($signature.Status -ne 'Valid' -or $null -eq $signature.SignerCertificate) {
      throw "Release artifact signature is not valid: $VersionedArtifact"
    }
    $actualThumbprint = Normalize-Thumbprint $signature.SignerCertificate.Thumbprint
    $expectedThumbprint = Normalize-Thumbprint $SignerThumbprint
    if ($actualThumbprint -ne $expectedThumbprint) {
      throw "Release artifact signer '$actualThumbprint' did not match expected '$expectedThumbprint'."
    }
    $VerifiedArtifacts += $BundleArtifact
  }

  Write-Host '[PASS] Release check passed.' -ForegroundColor Green
  Write-Host '[INFO] Verified artifacts:' -ForegroundColor DarkGray
  foreach ($artifact in $VerifiedArtifacts) {
    Write-Host "  $artifact"
  }
}
finally {
  Set-Location $OriginalLocation
  if (Test-Path $TempVenvRoot) {
    try {
      Remove-Item -Path $TempVenvRoot -Recurse -Force -ErrorAction Stop
    } catch {
      Write-Warning ("Failed to remove temporary release-check environment '{0}': {1}" -f $TempVenvRoot, $_.Exception.Message)
    }
  }
}
