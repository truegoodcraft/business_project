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

$ErrorActionPreference="Stop"
$base="http://127.0.0.1:8765"
# Ensure app.db stays in place
$db="$env:LOCALAPPDATA\BUSCore\app\business_project-main\data\app.db"
if (!(Test-Path $db)) { throw "app.db missing at $db" }
# Entry should be 200
$r=(Invoke-WebRequest "$base/ui/shell.html" -UseBasicParsing)
if ($r.StatusCode -ne 200){ throw "shell.html HTTP $($r.StatusCode)" }
"OK"
