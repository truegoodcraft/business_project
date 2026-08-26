$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$venvUsable = Test-Path $python -PathType Leaf

if ($venvUsable) {
    try {
        & $python -c "import sys" *> $null
        $venvUsable = $LASTEXITCODE -eq 0
    }
    catch {
        $venvUsable = $false
    }
}

if (-not $venvUsable) {
    $python = (Get-Command "python" -CommandType Application -ErrorAction Stop).Source
}

& $python (Join-Path $repoRoot "scripts\validate_version_governance.py")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $python (Join-Path $repoRoot "scripts\validate_change_trace.py")
exit $LASTEXITCODE
