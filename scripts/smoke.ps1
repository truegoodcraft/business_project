<#
  PowerShell 5.1-compatible smoke test.
  Verifies cookie mint and protected ping, plus UI shell and favicon.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Use script directory as repo root to avoid CWD issues
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Base = "http://127.0.0.1:8765"

Write-Host "== Smoke: /session/token"
$resp = Invoke-WebRequest -Uri "$Base/session/token" -UseBasicParsing -MaximumRedirection 0
if (-not $resp.Headers.ContainsKey("Set-Cookie")) {
  throw "No Set-Cookie header from /session/token"
}
$cookie = ($resp.Headers["Set-Cookie"] | Select-Object -First 1).Split(";")[0]
Write-Host "Cookie: $cookie"

Write-Host "== Smoke: /app/ping with cookie"
$headers = @{ "Cookie" = $cookie }
$ping = Invoke-WebRequest -Uri "$Base/app/ping" -Headers $headers -UseBasicParsing -MaximumRedirection 0
if ($ping.StatusCode -ne 200) {
  throw "/app/ping expected 200, got $($ping.StatusCode)"
}

Write-Host "== Smoke: UI shell"
try {
  $ui = Invoke-WebRequest -Uri "$Base/ui/shell.html" -UseBasicParsing -MaximumRedirection 0
  if ($ui.StatusCode -ne 200) {
    throw "/ui/shell.html expected 200, got $($ui.StatusCode)"
  }
} catch {
  throw "UI shell not available at /ui/shell.html: $($_.Exception.Message)"
}

Write-Host "== Smoke: favicon"
try {
  $fav = Invoke-WebRequest -Uri "$Base/favicon.ico" -UseBasicParsing -MaximumRedirection 0
  if (($fav.StatusCode -ne 200) -and ($fav.StatusCode -ne 204)) {
    throw "/favicon.ico expected 200 or 204, got $($fav.StatusCode)"
  }
} catch {
  throw "Favicon check failed: $($_.Exception.Message)"
}

Write-Host "All smoke checks passed."
