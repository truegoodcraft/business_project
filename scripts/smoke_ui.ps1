$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8765"
# token check
$token = (Invoke-WebRequest -UseBasicParsing -Method GET "$base/health").Headers["X-Session-Token"]
Write-Host "Token header present: " ([bool]$token)
# shell entry 200
$r = Invoke-WebRequest -UseBasicParsing "$base/ui/shell.html"
if ($r.StatusCode -ne 200) { throw "shell.html not served" }
# app.js loads as module
$r2 = Invoke-WebRequest -UseBasicParsing "$base/ui/app.js"
if (-not $r2.Content.Contains("export ") -and -not $r2.Content.Contains("import ")) { throw "app.js not ESM" }
Write-Host "Smoke OK"
