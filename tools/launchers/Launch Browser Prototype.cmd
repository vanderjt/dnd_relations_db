@echo off
setlocal
cd /d "%~dp0..\.."
echo Open http://127.0.0.1:8765 in your browser.
echo Keep this window open. Press Ctrl+C to stop.
if exist ".build-env\Scripts\python.exe" (
  ".build-env\Scripts\python.exe" prototypes\phase2\serve.py
) else (
  python prototypes\phase2\serve.py
)
