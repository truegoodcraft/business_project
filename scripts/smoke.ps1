<#
  PowerShell 5.1-compatible smoke test.
  Verifies cookie mint, protected ping, UI shell, and favicon.
  Falls back to the session cookie jar when Set-Cookie header is not exposed.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Use script directory as repo root to avoid CWD issues
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Base = "http://127.0.0.1:8765"

function Get-SessionCookie {
  param([string]$Base)
  Write-Host "== Smoke: /session/token"
  $session = $null
  try {
    $resp = Invoke-WebRequest -Uri "$Base/session/token" -UseBasicParsing -MaximumRedirection 0 -SessionVariable session
  } catch {
    throw "Failed to hit /session/token. Is the server running? Error: $($_.Exception.Message)"
  }

  # Try direct header first (works on PS7+)
  $cookie = $null
  if ($resp.Headers -and $resp.Headers.ContainsKey("Set-Cookie")) {
    $cookie = ($resp.Headers["Set-Cookie"] | Select-Object -First 1).Split(";")[0]
  }

  # Fallback: cookie jar (PS 5.1 often hides Set-Cookie from Headers)
  if (-not $cookie) {
    try {
      $jar = $session.Cookies.GetCookies($Base)
      if ($jar -and $jar.Count -gt 0) {
        $cookie = "$($jar[0].Name)=$($jar[0].Value)"
      }
    } catch { }
  }

  if (-not $cookie) {
    Write-Warning "No cookie via header or jar; dumping diagnostics..."
    if ($resp) {
      Write-Host "StatusCode: $($resp.StatusCode)"
      if ($resp.Headers) {
        Write-Host "Headers:"; $resp.Headers.GetEnumerator() | ForEach-Object { Write-Host " - $($_.Key): $($_.Value)" }
      }
    }
    try {
      $j = $session.Cookies.GetCookies($Base)
      Write-Host "CookieJar count: $($j.Count)"
    } catch { }
    throw "No session cookie obtained from /session/token"
  }
  # Extract the token value for header fallback (X-Session-Token)
  $token = $cookie -replace '^[^=]+=','' -replace ';.*$',''
  $token = $token.Trim()
  # Return a small object with both
  [pscustomobject]@{
    Cookie = $cookie
    Token  = $token
    Session = $session
  }
}

$auth = Get-SessionCookie -Base $Base
Write-Host "Cookie: $($auth.Cookie)"
Write-Host "Token:  $($auth.Token)"

Write-Host "== Smoke: /app/ping with cookie"
# Send both Cookie and X-Session-Token to avoid client cookie quirks
$headers = @{
  "Cookie"          = $auth.Cookie
  "X-Session-Token" = $auth.Token
}
# Prefer using the same WebSession to carry jar state too
$ping = Invoke-WebRequest -Uri "$Base/app/ping" -Headers $headers -UseBasicParsing -MaximumRedirection 0 -WebSession $auth.Session
if ($ping.StatusCode -ne 200) {
  throw "/app/ping expected 200, got $($ping.StatusCode)"
}

Write-Host "== Smoke: UI shell"
try {
  $ui = Invoke-WebRequest -Uri "$Base/ui/shell.html" -UseBasicParsing -MaximumRedirection 0
  if ($ui.StatusCode -ne 200) { throw "/ui/shell.html expected 200, got $($ui.StatusCode)" }
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
