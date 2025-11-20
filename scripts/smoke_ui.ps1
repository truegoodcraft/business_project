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
