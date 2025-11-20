# SPDX-License-Identifier: AGPL-3.0-or-later
# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

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
