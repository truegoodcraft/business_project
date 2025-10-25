$u='http://127.0.0.1:8765'
$tok=(Invoke-RestMethod "$u/session/token").token
$H=@{'X-Session-Token'=$tok;'Content-Type'='application/json'}
Invoke-RestMethod "$u/dev/writes" -Headers $H -Method POST -Body (@{enabled=$false}|ConvertTo-Json)|Out-Null
$exp=Invoke-RestMethod "$u/app/export" -Headers $H -Method POST -Body (@{password='P@ss-w0rd'}|ConvertTo-Json)
$exp.path
try { Invoke-RestMethod "$u/app/import/preview" -Headers $H -Method POST -Body (@{password='P@ss-w0rd';path=$exp.path}|ConvertTo-Json) } catch { $_.Exception.Response.StatusCode }
Invoke-RestMethod "$u/dev/writes" -Headers $H -Method POST -Body (@{enabled=$true}|ConvertTo-Json)|Out-Null
$pv=Invoke-RestMethod "$u/app/import/preview" -Headers $H -Method POST -Body (@{password='P@ss-w0rd';path=$exp.path}|ConvertTo-Json)
$pv.preview
$cm=Invoke-RestMethod "$u/app/import/commit" -Headers $H -Method POST -Body (@{password='P@ss-w0rd';path=$exp.path}|ConvertTo-Json)
$cm.replaced; $cm.backup
try { Invoke-RestMethod "$u/app/import/preview" -Headers $H -Method POST -Body (@{password='wrong';path=$exp.path}|ConvertTo-Json) } catch { $_.ErrorDetails.Message }
try { Invoke-RestMethod "$u/app/import/preview" -Headers $H -Method POST -Body (@{password='P@ss-w0rd';path='C:\Windows\not.tgc'}|ConvertTo-Json) } catch { $_.ErrorDetails.Message }
