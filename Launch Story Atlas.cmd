@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
rem Prefer the current checkout when its preview runtime and assets are ready.
if exist ".build-env\Scripts\python.exe" if exist "preview\dist\index.html" if exist "preview\dist\app.js" goto source
if exist "dist\StoryAtlasPreview\StoryAtlasPreview.exe" goto packaged
rem Resolve installed copies in PowerShell, never execute registry text in cmd.
rem Rebuild native Windows PowerShell module paths if launched from PowerShell 7.
set "PSModulePath="
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\launch_installed.ps1" %*
goto finished
:source
echo Starting Story Atlas from this checkout...
".build-env\Scripts\python.exe" "preview_main.py" %*
goto finished
:packaged
echo Starting the local packaged Story Atlas...
"dist\StoryAtlasPreview\StoryAtlasPreview.exe" %*
goto finished
:finished
set "launch_result=%errorlevel%"
if not "%launch_result%"=="0" pause
exit /b %launch_result%
