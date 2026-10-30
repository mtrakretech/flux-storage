@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0FluxStorage.exe" (
  start "" "%~dp0FluxStorage.exe"
  exit /b
)
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" bootstrap.py
) else (
  where py.exe >nul 2>nul
  if not errorlevel 1 (py -3 bootstrap.py) else (python bootstrap.py)
)
if errorlevel 1 pause
