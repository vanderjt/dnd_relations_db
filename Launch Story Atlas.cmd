@echo off
setlocal
cd /d "%~dp0"
rem Prefer the current checkout when its preview runtime and assets are ready.
if exist ".build-env\Scripts\python.exe" if exist "preview\dist\index.html" goto source
if exist "dist\StoryAtlasPreview\StoryAtlasPreview.exe" goto packaged
if exist "%LOCALAPPDATA%\Programs\Story Atlas Preview\StoryAtlasPreview.exe" goto installed
echo Story Atlas is not ready to launch.
echo Run Setup in installer, or follow README.md to set up source mode.
pause
exit /b 1
:source
echo Starting Story Atlas from this checkout...
".build-env\Scripts\python.exe" "preview_main.py" %*
goto finished
:packaged
echo Starting the local packaged Story Atlas...
"dist\StoryAtlasPreview\StoryAtlasPreview.exe" %*
goto finished
:installed
echo Starting the installed Story Atlas...
"%LOCALAPPDATA%\Programs\Story Atlas Preview\StoryAtlasPreview.exe" %*
:finished
set "launch_result=%errorlevel%"
if not "%launch_result%"=="0" pause
exit /b %launch_result%
