@echo off
setlocal
set "APPDIR=%LOCALAPPDATA%\BUSCore\app\tgc-bus-core"
set "LAUNCH=%APPDIR%\scripts\launch_buscore.ps1"
set "BCROOT=%LOCALAPPDATA%\BUSCore"
if not exist "%BCROOT%" mkdir "%BCROOT%"
if not exist "%BCROOT%\secrets" mkdir "%BCROOT%\secrets"
if not exist "%BCROOT%\state" mkdir "%BCROOT%\state"
if not exist "%LAUNCH%" (
  echo Launcher missing: %LAUNCH%
  exit /b 1
)
echo Using launcher: %LAUNCH%
powershell -NoProfile -ExecutionPolicy Bypass -File "%LAUNCH%"
endlocal
