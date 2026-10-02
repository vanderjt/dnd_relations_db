@echo off
setlocal
rem Development launcher only. It never starts a packaged executable.
if exist "%~dp0..\..\.build-env\Scripts\python.exe" (
  "%~dp0..\..\.build-env\Scripts\python.exe" "%~dp0..\..\main.py" %*
  exit /b %errorlevel%
)
where conda >nul 2>nul
if not errorlevel 1 (
  call conda run --no-capture-output -n story-atlas python "%~dp0..\..\main.py" %*
  exit /b %errorlevel%
)
echo Source mode needs .build-env or the story-atlas Conda environment.
exit /b 1
