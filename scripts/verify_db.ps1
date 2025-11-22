param(
  [string]$Base = "http://127.0.0.1:8765"
)

$tok = (Invoke-RestMethod "$Base/session/token").token
$hdr = @{ "X-Session-Token" = $tok; "Content-Type"="application/json" }

# Touch a row
$null = Invoke-RestMethod -Method POST -Uri "$Base/app/vendors" -Headers $hdr -Body '{"name":"path-fixed-check"}'

# Ask the server where the DB is
$info = Invoke-RestMethod -Method GET -Uri "$Base/dev/db/where" -Headers $hdr
$info | ConvertTo-Json -Depth 5

$configured = $info.configured_path
"Configured DB path: $configured"
"Exists on FS:       " + ([bool](Test-Path $configured))

if (-not (Test-Path $configured)) {
  Write-Warning "DB file not found at configured path."
  exit 2
}
exit 0
