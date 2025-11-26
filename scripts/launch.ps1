param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8765
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\.venv")) {
  Write-Host "[launch] Creating venv..."
  python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r .\requirements.txt

if ($env:BUSCORE_EXTRAS -eq "1" -and (Test-Path .\requirements-extras.txt)) {
  Write-Host "[launch] Installing extras..."
  pip install -r .\requirements-extras.txt
}

Write-Host "[launch] Starting BUS Core at http://$BindHost`:$Port"
python -c "import uvicorn; uvicorn.run('tgc.http:app', host='$BindHost', port=$Port, log_level='info')"
