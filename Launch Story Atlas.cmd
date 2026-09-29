@echo off
setlocal
rem Packaged launcher only. It never falls back to source or an older executable.
if exist "%~dp0StoryAtlas.exe" (
  "%~dp0StoryAtlas.exe" %*
  exit /b %errorlevel%
)
if exist "%~dp0dist\releases\0.17.0\StoryAtlas\StoryAtlas.exe" (
  "%~dp0dist\releases\0.17.0\StoryAtlas\StoryAtlas.exe" %*
  exit /b %errorlevel%
)
if exist "%~dp0dist\StoryAtlas\StoryAtlas.exe" (
  "%~dp0dist\StoryAtlas\StoryAtlas.exe" %*
  exit /b %errorlevel%
)
echo No packaged Story Atlas executable was found. Build the release or use "Launch Story Atlas Source.cmd".
exit /b 1
