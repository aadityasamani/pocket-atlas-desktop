@echo off
cd /d "%~dp0"
"..\.runtime\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name PocketAtlas --exclude-module PySide6 --exclude-module PyQt5 app.py
pause
