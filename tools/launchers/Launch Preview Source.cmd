@echo off
setlocal
cd /d "%~dp0..\.."
if not exist ".build-env\Scripts\python.exe" (
  echo Preview requires the local Python environment. See docs\MVP_DELIVERY.md.
  pause
  exit /b 1
)
if not exist "preview\dist\index.html" (
  echo Preview assets are missing. Run npm ci and npm run build in preview.
  pause
  exit /b 1
)
".build-env\Scripts\python.exe" preview_main.py %*
if errorlevel 1 pause
