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
& $python -m unittest tests.test_preview_portrait tests.test_preview_picker tests.test_preview_close tests.test_preview_store tests.test_preview_platform tests.test_profile_history -q
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
$definition = Get-Content -LiteralPath 'installer/StoryAtlasPreview.iss' -Raw
$versionMatch = [regex]::Match($definition, '#define AppVersion "([0-9]+\.[0-9]+\.[0-9]+)"')
if (!$versionMatch.Success) { throw 'Installer version is missing from StoryAtlasPreview.iss.' }
$version = $versionMatch.Groups[1].Value
$setup = Join-Path $PSScriptRoot "installer\StoryAtlasPreview-$version-Windows-x64-Offline-Setup.exe"
$hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash
Set-Content -LiteralPath "$setup.sha256" -Value "$hash  $([IO.Path]::GetFileName($setup))"
$commit = (& git rev-parse HEAD).Trim()
if ($LASTEXITCODE) { throw 'Unable to identify the source commit.' }
@{ version = $version; source_commit = $commit; installer = [IO.Path]::GetFileName($setup); sha256 = $hash } |
    ConvertTo-Json | Set-Content -LiteralPath 'installer/release.json' -Encoding UTF8
Write-Host "Ready for verification: $setup"
