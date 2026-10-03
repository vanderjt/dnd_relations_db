param([string]$Compiler = "$PSScriptRoot\build\inno\ISCC.exe")
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.build-env\Scripts\python.exe'
$runtime = Join-Path $PSScriptRoot 'build\installer-deps\MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
if (!(Test-Path -LiteralPath $Compiler)) { throw 'Install Inno Setup and pass -Compiler <path to ISCC.exe>.' }
$signature = Get-AuthenticodeSignature -LiteralPath $runtime
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*Microsoft Corporation*') { throw 'A valid Microsoft-signed offline WebView2 installer is required.' }
Push-Location preview
try { npm.cmd run build; if ($LASTEXITCODE) { throw 'Frontend build failed' } } finally { Pop-Location }
& $python -m unittest tests.test_preview_portrait tests.test_preview_picker tests.test_preview_close tests.test_preview_store tests.test_profile_history -q
if ($LASTEXITCODE) { throw 'Tests failed' }
& $python tools/verify_literary_examples.py
if ($LASTEXITCODE) { throw 'Literary example verification failed' }
& $python tools/build_edgerunners_example.py 'examples/saved-stories/Cyberpunk Edgerunners S1.atlas-preview' --verify-only
if ($LASTEXITCODE) { throw 'Edgerunners example verification failed' }
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot 'build\pyinstaller-preview-cache'
& $python -m PyInstaller --noconfirm --distpath dist --workpath build/preview-freeze StoryAtlasPreview.spec
if ($LASTEXITCODE) { throw 'Application packaging failed' }
& $Compiler installer/StoryAtlasPreview.iss
if ($LASTEXITCODE) { throw 'Installer compilation failed' }
$setup = Join-Path $PSScriptRoot 'dist\installer\StoryAtlasPreview-0.1.0-Windows-x64-Offline-Setup.exe'
$hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash
Set-Content -LiteralPath "$setup.sha256" -Value "$hash  $([IO.Path]::GetFileName($setup))"
Copy-Item -LiteralPath 'installer/README.txt' -Destination 'dist/installer/README.txt' -Force
Write-Host "Ready for verification: $setup"
