@echo off
cd /d "%~dp0"
if exist "dist\PocketAtlas\PocketAtlas.exe" (
  start "" "dist\PocketAtlas\PocketAtlas.exe"
  exit /b 0
)
"..\.runtime\Scripts\python.exe" app.py
if errorlevel 1 pause
