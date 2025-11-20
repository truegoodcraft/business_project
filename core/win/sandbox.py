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

import win32job, win32process, win32con, win32security, pywintypes

def _create_job_kill_on_close():
    hjob = win32job.CreateJobObject(None, "")
    info = win32job.QueryInformationJobObject(hjob, win32job.JobObjectExtendedLimitInformation)
    info['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    win32job.SetInformationJobObject(hjob, win32job.JobObjectExtendedLimitInformation, info)
    return hjob

def _restricted_token():
    base = win32security.OpenProcessToken(win32process.GetCurrentProcess(), win32con.MAXIMUM_ALLOWED)
    return win32security.CreateRestrictedToken(base, win32security.DISABLE_MAX_PRIVILEGE, [], [], [])

def spawn_sandboxed(cmdline: str):
    si = win32process.STARTUPINFO()
    try:
        tok = _restricted_token()
        ph, th, pid, tid = win32process.CreateProcessAsUser(tok, None, cmdline, None, None, False,
            win32con.CREATE_SUSPENDED | win32con.CREATE_NEW_PROCESS_GROUP, None, None, si)
    except pywintypes.error:
        ph, th, pid, tid = win32process.CreateProcess(None, cmdline, None, None, False,
            win32con.CREATE_SUSPENDED | win32con.CREATE_NEW_PROCESS_GROUP, None, None, si)
    hjob = _create_job_kill_on_close()
    win32job.AssignProcessToJobObject(hjob, ph)
    win32process.ResumeThread(th)
    return ph, th, hjob
