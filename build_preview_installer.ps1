param(
    [string]$Compiler = "$PSScriptRoot\build\inno\ISCC.exe",
    [string]$Python = "$PSScriptRoot\.build-env\Scripts\python.exe",
    [string]$OutputDirectory = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Set-Location -LiteralPath $PSScriptRoot

if (!(Test-Path -LiteralPath $Compiler -PathType Leaf)) {
    throw 'Install Inno Setup and pass -Compiler <path to ISCC.exe>.'
}
if (!(Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Create .build-env and install the runtime and locked build requirements first.'
}

# Capture only committed inputs, before doing any expensive packaging work.
$sourceJson = & $Python tools/release_metadata.py
if ($LASTEXITCODE) { throw 'Release source validation failed.' }
$source = $sourceJson | ConvertFrom-Json
$version = $source.version
if (!$OutputDirectory) {
    $OutputDirectory = Join-Path $PSScriptRoot "build\releases\$version"
}
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
$publishedDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'installer'))
if ($OutputDirectory.TrimEnd('\') -eq $publishedDirectory.TrimEnd('\')) {
    throw 'Stage the candidate outside installer/. Promote it only after native verification.'
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$runtime = Join-Path $PSScriptRoot 'build\installer-deps\MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
if (!(Test-Path -LiteralPath $runtime -PathType Leaf)) {
    throw 'Download the official x64 offline WebView2 installer into build\installer-deps first.'
}
$signature = Get-AuthenticodeSignature -LiteralPath $runtime
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*Microsoft Corporation*') {
    throw 'A valid Microsoft-signed offline WebView2 installer is required.'
}

Push-Location preview
try {
    npm.cmd ci
    if ($LASTEXITCODE) { throw 'Frontend dependency installation failed.' }
    npm.cmd run build
    if ($LASTEXITCODE) { throw 'Frontend build failed.' }
    npm.cmd run test:build
    if ($LASTEXITCODE) { throw 'Frontend rebuild verification failed.' }
} finally { Pop-Location }
& $Python -m unittest discover -s tests -q
if ($LASTEXITCODE) { throw 'Tests failed.' }
& $Python tools/verify_examples.py
if ($LASTEXITCODE) { throw 'Example verification failed.' }

# Both the renderer and the frozen host must discard obsolete generated files.
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot 'build\pyinstaller-preview-cache'
& $Python -m PyInstaller --clean --noconfirm --distpath dist --workpath build/preview-freeze StoryAtlasPreview.spec
if ($LASTEXITCODE) { throw 'Application packaging failed.' }
& $Compiler "/DAppVersion=$version" "/O$OutputDirectory" installer/StoryAtlasPreview.iss
if ($LASTEXITCODE) { throw 'Installer compilation failed.' }

$setup = Join-Path $OutputDirectory "StoryAtlasPreview-$version-Windows-x64-Offline-Setup.exe"
& $Python tools/release_metadata.py --installer $setup --source-commit $source.source_commit
if ($LASTEXITCODE) { throw 'Release provenance or checksum verification failed.' }
Write-Host "Candidate ready for native verification: $setup"
Write-Host 'The existing installer/ release has not been replaced.'
