$ErrorActionPreference="Stop"
$base="http://127.0.0.1:8765"
# Ensure app.db stays in place
$db="$env:LOCALAPPDATA\BUSCore\app\business_project-main\data\app.db"
if (!(Test-Path $db)) { throw "app.db missing at $db" }
# Entry should be 200
$r=(Invoke-WebRequest "$base/ui/shell.html" -UseBasicParsing)
if ($r.StatusCode -ne 200){ throw "shell.html HTTP $($r.StatusCode)" }
"OK"
