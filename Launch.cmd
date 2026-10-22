@echo off
cd /d "%~dp0"
if exist "dist\PocketAtlas\PocketAtlas.exe" (
  start "" "dist\PocketAtlas\PocketAtlas.exe"
  exit /b 0
)
call Setup.cmd
if errorlevel 1 goto failed
"%ATLAS_PYTHON%" app.py
if errorlevel 1 pause
exit /b 0
:failed
echo Setup failed. Please read the error above.
pause
exit /b 1
