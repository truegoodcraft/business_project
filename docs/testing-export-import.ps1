$ErrorActionPreference = 'Stop'
$u = 'http://127.0.0.1:8765'
$tok = (Invoke-RestMethod "$u/session/token").token
$H = @{ 'X-Session-Token' = $tok; 'Content-Type' = 'application/json' }

Write-Host "== disable writes =="
Invoke-RestMethod "$u/dev/writes" -Headers $H -Method POST -Body (@{ enabled = $false } | ConvertTo-Json) | Out-Null

Write-Host "== export =="
$exp = Invoke-RestMethod "$u/app/export" -Headers $H -Method POST -Body (@{ password = 'P@ss-w0rd' } | ConvertTo-Json)
$exp.path

Write-Host "== preview (writes disabled -> expect 403) =="
try {
    Invoke-RestMethod "$u/app/import/preview" -Headers $H -Method POST -Body (@{ password = 'P@ss-w0rd'; path = $exp.path } | ConvertTo-Json) | Out-Null
} catch {
    $_.Exception.Response.StatusCode
}

Write-Host "== enable writes =="
Invoke-RestMethod "$u/dev/writes" -Headers $H -Method POST -Body (@{ enabled = $true } | ConvertTo-Json) | Out-Null

Write-Host "== preview (200) =="
$pv = Invoke-RestMethod "$u/app/import/preview" -Headers $H -Method POST -Body (@{ password = 'P@ss-w0rd'; path = $exp.path } | ConvertTo-Json)
$pv.preview

Write-Host "== commit =="
$cm = Invoke-RestMethod "$u/app/import/commit" -Headers $H -Method POST -Body (@{ password = 'P@ss-w0rd'; path = $exp.path } | ConvertTo-Json)
$cm.replaced
$cm.backup

Write-Host "== negative cases =="
try {
    Invoke-RestMethod "$u/app/import/preview" -Headers $H -Method POST -Body (@{ password = 'wrong'; path = $exp.path } | ConvertTo-Json) | Out-Null
} catch {
    $_.ErrorDetails.Message
}
try {
    Invoke-RestMethod "$u/app/import/preview" -Headers $H -Method POST -Body (@{ password = 'P@ss-w0rd'; path = 'C:\\Windows\\not.tgc' } | ConvertTo-Json) | Out-Null
} catch {
    $_.ErrorDetails.Message
}
