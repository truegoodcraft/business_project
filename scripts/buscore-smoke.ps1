# recipes should 200
$resp = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8765/app/recipes" -Method GET
if ($resp.StatusCode -ne 200) { throw "GET /app/recipes not 200" }
