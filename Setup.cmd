@echo off
if exist "%~dp0.venv\Scripts\python.exe" (
  set "ATLAS_PYTHON=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0..\.runtime\Scripts\python.exe" (
  set "ATLAS_PYTHON=%~dp0..\.runtime\Scripts\python.exe"
) else (
  py -m venv "%~dp0.venv"
  if errorlevel 1 exit /b 1
  set "ATLAS_PYTHON=%~dp0.venv\Scripts\python.exe"
)
"%ATLAS_PYTHON%" -c "from PyQt6.QtWidgets import QApplication; import PyInstaller" >nul 2>&1
if errorlevel 1 (
  "%ATLAS_PYTHON%" -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 exit /b 1
)
exit /b 0
