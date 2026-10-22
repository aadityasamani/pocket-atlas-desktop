@echo off
cd /d "%~dp0"
call Setup.cmd
if errorlevel 1 goto failed
"%ATLAS_PYTHON%" -m PyInstaller --noconfirm --clean --onedir --windowed --name PocketAtlas --exclude-module PySide6 --exclude-module PyQt5 app.py
if errorlevel 1 goto failed
echo Build complete: dist\PocketAtlas\PocketAtlas.exe
pause
exit /b 0
:failed
echo Build failed. Please read the error above.
pause
exit /b 1
