@echo off
setlocal
set "APPDIR=%LOCALAPPDATA%\BUSCore\app\tgc-bus-core"
set "LAUNCH=%APPDIR%\scripts\launch_buscore.ps1"
if not exist "%LAUNCH%" (
  echo Launcher missing: %LAUNCH%
  exit /b 1
)
echo Using launcher: %LAUNCH%
powershell -NoProfile -ExecutionPolicy Bypass -File "%LAUNCH%"
endlocal
