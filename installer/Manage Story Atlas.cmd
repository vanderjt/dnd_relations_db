@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0manage_installation.ps1"
set "manage_result=%errorlevel%"
if not "%manage_result%"=="0" pause
exit /b %manage_result%
