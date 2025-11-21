try { chcp 65001 > $null } catch {}
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$ErrorActionPreference="Stop"
$BASE = "http://127.0.0.1:8765/session/token"
for ($i=0; $i -lt 30; $i++) {
  try { Invoke-WebRequest -UseBasicParsing $BASE -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep 1 }
}
powershell -NoProfile -ExecutionPolicy Bypass -File ".\buscore-smoke.ps1"
