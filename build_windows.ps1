param([string]$Python = "python", [string]$DistPath = "dist")
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
& $Python -c "import sys,struct; assert sys.platform == 'win32' and sys.version_info[:3] == (3,13,9) and struct.calcsize('P') == 8, 'Use CPython 3.13.9 x64'"
if ($LASTEXITCODE -ne 0) { throw "Unsupported build interpreter" }
& $Python -m venv .build-env
if ($LASTEXITCODE -ne 0) { throw "Cannot create isolated build environment" }
$buildPython = Join-Path $PSScriptRoot ".build-env\Scripts\python.exe"
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot "build\pyinstaller-cache"
& $buildPython -m pip install -r requirements-build.lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
& $buildPython tools/make_icon.py
if ($LASTEXITCODE -ne 0) { throw "Icon generation failed" }
& $buildPython -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Tests failed; build stopped" }
& $buildPython tools/freeze_build_metadata.py
if ($LASTEXITCODE -ne 0) { throw "Cannot freeze build identity" }
& $buildPython -m PyInstaller --noconfirm --clean --distpath $DistPath StoryAtlas.spec
if ($LASTEXITCODE -ne 0) { throw "Packaging failed" }
$packagePath = Join-Path $DistPath 'StoryAtlas'
Copy-Item -LiteralPath 'DISTRIBUTION.md' -Destination (Join-Path $packagePath 'README-Windows.md') -Force
Copy-Item -LiteralPath 'Launch Story Atlas.cmd' -Destination (Join-Path $packagePath 'Launch Story Atlas.cmd') -Force
Compress-Archive -LiteralPath $packagePath -DestinationPath 'dist\StoryAtlas-Windows-x64.zip' -Force
$digest = (Get-FileHash -LiteralPath 'dist\StoryAtlas-Windows-x64.zip' -Algorithm SHA256).Hash
Set-Content -LiteralPath 'dist\StoryAtlas-Windows-x64.zip.sha256' -Value "$digest  StoryAtlas-Windows-x64.zip"
Write-Host "Built $packagePath\StoryAtlas.exe. Distribute the ENTIRE StoryAtlas folder."
Write-Host "Run tools\smoke_windows.ps1 before distributing."
