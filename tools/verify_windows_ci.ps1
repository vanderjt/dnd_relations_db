# Hosted Windows verification only. This never installs the production candidate:
# the lifecycle harness uses unique AppIds and disposable synthetic data.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (!$IsWindows -or $env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'Run this helper only on a disposable GitHub-hosted Windows runner.'
}
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root
$EvidenceDirectory = Join-Path $Root 'build-verification\ci'
New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null
$EvidencePath = Join-Path $EvidenceDirectory 'verification.json'
$PreviousCommit = 'd6376bc388169bfe636115be5ea2ef444ff875b8'
$PreviousVersion = '0.1.1'
$PreviousRoot = Join-Path $Root 'build\ci\previous'
$Python = Join-Path $Root '.build-env\Scripts\python.exe'
$Runtime = Join-Path $Root 'build\installer-deps\MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
$RuntimeUrl = 'https://go.microsoft.com/fwlink/?linkid=2124701'
$Evidence = [ordered]@{
    status = 'running'
    started_utc = [DateTime]::UtcNow.ToString('o')
    previous_source_commit = $PreviousCommit
    previous_version = $PreviousVersion
    previous_build_note = 'Rebuilt historical source with current pinned dependencies; not a byte-for-byte reproduction of the shipped 0.1.1 EXE.'
    phases = @()
    native_sample = @{ status = 'not run' }
    excluded = @('network-disabled clean-machine installation', 'interactive installer cancellation',
        'production desktop/Start Menu shortcuts', 'installed/frozen native UI acceptance', 'macOS acceptance')
}

function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE." }
}

function Save-Evidence {
    $Evidence | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $EvidencePath -Encoding utf8
}

function Get-WebViewRegistration {
    # Microsoft's documented x64 per-user and per-machine registry locations.
    foreach ($Key in @(
        'Registry::HKEY_CURRENT_USER\Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
        'Registry::HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    )) {
        $Item = Get-ItemProperty -LiteralPath $Key -Name pv -ErrorAction SilentlyContinue
        if ($null -ne $Item -and $Item.pv -and $Item.pv -ne '0.0.0.0') {
            [ordered]@{ key = $Key; version = [string]$Item.pv }
        }
    }
}

function Invoke-BoundedProcess([string]$Program, [string]$Arguments, [string]$Label, [int]$Seconds) {
    $Process = Start-Process -FilePath $Program -ArgumentList $Arguments -PassThru -NoNewWindow `
        -RedirectStandardOutput (Join-Path $EvidenceDirectory "$Label-stdout.txt") `
        -RedirectStandardError (Join-Path $EvidenceDirectory "$Label-stderr.txt")
    try {
        if (!$Process.WaitForExit($Seconds * 1000)) {
            # Only terminate this test process and its descendants, never other apps.
            $Process.Kill($true)
            $Process.WaitForExit()
            throw "$Label exceeded its $Seconds second timeout. See its logs."
        }
        $Process.WaitForExit()
        if ($Process.ExitCode -ne 0) { throw "$Label failed with exit code $($Process.ExitCode). See its logs." }
    } finally { $Process.Dispose() }
}

Start-Transcript -Path (Join-Path $EvidenceDirectory 'verification-transcript.txt') | Out-Null
try {
    $SourceJson = & python tools/release_metadata.py
    if ($LASTEXITCODE -ne 0) { throw 'Candidate source is not a clean committed checkout.' }
    $Source = $SourceJson | ConvertFrom-Json
    $Evidence.source_commit = $Source.source_commit
    $Evidence.version = $Source.version
    $Published = Get-Content -LiteralPath 'installer\release.json' -Raw | ConvertFrom-Json
    if ($Published.source_commit -ne $PreviousCommit -or $Published.version -ne $PreviousVersion) {
        throw 'The historical CI baseline no longer matches the recorded previous release.'
    }
    $Compiler = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (!$Compiler) { throw 'The hosted runner does not contain the expected Inno Setup compiler.' }
    $Evidence.environment = [ordered]@{
        windows = [Environment]::OSVersion.VersionString
        runner_image = $env:ImageOS
        runner_image_version = $env:ImageVersion
        powershell = $PSVersionTable.PSVersion.ToString()
        python = (& python --version)
        node = (& node --version)
        npm = (& npm.cmd --version)
        inno_compiler = $Compiler
        inno_file_version = (Get-Item -LiteralPath $Compiler).VersionInfo.ProductVersion
        inno_compiler_banner = ((& $Compiler '/?' 2>&1) -join "`n")
        inno_note = 'Use the compiler already supplied by the hosted image; historical release documentation used 6.7.3.'
        user_interactive = [Environment]::UserInteractive
        session_id = (Get-Process -Id $PID).SessionId
        webview2_before = @(Get-WebViewRegistration)
    }
    Save-Evidence

    Write-Host 'Installing the pinned build and runtime requirements.'
    Invoke-Checked python @('-m', 'venv', '.build-env')
    Invoke-Checked $Python @('-m', 'pip', 'install', '-r', 'requirements-preview.txt', '-r', 'requirements-build.lock.txt')
    Invoke-Checked $Python @('-m', 'pip', 'check')
    & $Python -m pip freeze | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'python-packages.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not record installed Python dependencies.' }
    $Evidence.phases += 'pinned build/runtime requirements installed and checked'

    Write-Host 'Downloading and verifying Microsoft standalone WebView2.'
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Runtime) | Out-Null
    Invoke-Checked curl.exe @('--fail', '--location', '--retry', '3', '--connect-timeout', '30',
        '--max-time', '600', '--proto', '=https', '--proto-redir', '=https', '--output', $Runtime, $RuntimeUrl)
    $Signature = Get-AuthenticodeSignature -LiteralPath $Runtime
    if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notlike '*Microsoft Corporation*') {
        throw 'The offline WebView2 installer must have a valid Microsoft Authenticode signature.'
    }
    $Evidence.webview2_download = [ordered]@{
        url = $RuntimeUrl
        sha256 = (Get-FileHash -LiteralPath $Runtime -Algorithm SHA256).Hash
        size_bytes = (Get-Item -LiteralPath $Runtime).Length
        file_version = (Get-Item -LiteralPath $Runtime).VersionInfo.FileVersion
        signature_status = [string]$Signature.Status
        signer = $Signature.SignerCertificate.Subject
    }
    $Evidence.phases += 'official Microsoft offline runtime downloaded and signature verified'
    Save-Evidence

    Write-Host 'Building genuine previous-source frozen payload.'
    $env:GIT_LFS_SKIP_SMUDGE = '1'
    Invoke-Checked git @('worktree', 'add', '--detach', $PreviousRoot, $PreviousCommit)
    Push-Location -LiteralPath $PreviousRoot
    try {
        $ActualPrevious = & git rev-parse HEAD
        if ($LASTEXITCODE -ne 0 -or $ActualPrevious -ne $PreviousCommit) { throw 'Wrong historical source checkout.' }
        Push-Location preview
        try {
            Invoke-Checked npm.cmd @('ci')
            Invoke-Checked npm.cmd @('run', 'build')
        } finally { Pop-Location }
        $env:PYINSTALLER_CONFIG_DIR = Join-Path $Root 'build\ci\previous-pyinstaller-cache'
        Invoke-Checked $Python @('-m', 'PyInstaller', '--clean', '--noconfirm', '--distpath', 'dist',
            '--workpath', 'build/preview-freeze', 'StoryAtlasPreview.spec')
        $PreviousStatus = & git status '--porcelain' '--untracked-files=all'
        if ($LASTEXITCODE -ne 0 -or $PreviousStatus) { throw 'Historical build modified its source checkout.' }
    } finally { Pop-Location }
    $Evidence.phases += 'historical source frozen using its original spec and frontend'
    Save-Evidence

    Write-Host 'Building complete offline candidate from current committed source.'
    & (Join-Path $Root 'build_preview_installer.ps1') -Compiler $Compiler -Python $Python
    if ($LASTEXITCODE -ne 0) { throw 'Candidate packaging failed.' }
    $CandidateManifest = Join-Path $Root "build\releases\$($Source.version)\release.json"
    $Evidence.candidate = Get-Content -LiteralPath $CandidateManifest -Raw | ConvertFrom-Json
    $Evidence.phases += 'full offline candidate built with source provenance and checksum'
    Save-Evidence

    foreach ($Payload in @(
        @{ label = 'previous-frozen-help'; folder = (Join-Path $PreviousRoot 'dist\StoryAtlasPreview') },
        @{ label = 'candidate-frozen-help'; folder = (Join-Path $Root 'dist\StoryAtlasPreview') }
    )) {
        $HelpHome = Join-Path $EvidenceDirectory ($Payload.label + '-home')
        Invoke-BoundedProcess (Join-Path $Payload.folder 'StoryAtlasPreview.exe') "--home `"$HelpHome`" --help" $Payload.label 60
        if (Test-Path -LiteralPath $HelpHome) { throw 'The --help probe unexpectedly created application data.' }
        $Evidence.phases += "$($Payload.label) exited successfully; bootstrap/import/argument parsing only"
    }
    Save-Evidence

    Write-Host 'Running real installers and manager under isolated test AppIds.'
    Invoke-Checked $Python @('tools/verify_installer_lifecycle.py', '--run-windows-sandbox',
        '--old-payload', (Join-Path $PreviousRoot 'dist\StoryAtlasPreview'), '--old-version', $PreviousVersion,
        '--new-payload', (Join-Path $Root 'dist\StoryAtlasPreview'), '--new-version', $Source.version,
        '--compiler', $Compiler)
    $Evidence.phases += 'isolated install, distinct-version upgrade, custom-path reinstall, uninstall, reinstall and data preservation passed'
    Save-Evidence

    if (!$Evidence.environment.user_interactive -or $Evidence.environment.session_id -eq 0) {
        $Evidence.native_sample = @{ status = 'skipped'; reason = 'Hosted process has no interactive desktop session; native WebView2 UI acceptance needs another Windows session.' }
    } else {
        $Evidence.native_sample = @{ status = 'running'; scope = 'Source-native WebView2 sample/bridge, not installed/frozen UI acceptance.' }
        Save-Evidence
        if (@(Get-WebViewRegistration).Count -eq 0) {
            Write-Host 'Installing the verified runtime on this disposable runner for the native probe.'
            Invoke-BoundedProcess $Runtime '/silent /install' 'webview2-install' 300
            if (@(Get-WebViewRegistration).Count -eq 0) { throw 'WebView2 registration is still absent after its installer exited.' }
        }
        $Evidence.environment.webview2_for_native_sample = @(Get-WebViewRegistration)
        $NativeHome = Join-Path $Root 'build-verification\native-sample'
        $NativeScript = Join-Path $Root 'tools\preview_native_smoke.py'
        Invoke-BoundedProcess $Python "`"$NativeScript`" --home `"$NativeHome`" --stage sample" 'native-sample' 180
        $NativeResult = Get-Content -LiteralPath (Join-Path $NativeHome 'sample-result.json') -Raw | ConvertFrom-Json
        if (!$NativeResult.passed) { throw 'The native sample reported a failed result.' }
        $Evidence.native_sample = @{ status = 'passed'; scope = 'Source-native WebView2 sample/bridge only.'; result = $NativeResult }
        $Evidence.phases += 'source-native Greyhaven sample passed through real WebView2 and bridge'
    }
    $Evidence.status = 'passed'
} catch {
    $Evidence.status = 'failed'
    $Evidence.error = $_.Exception.Message
    if ($Evidence.native_sample.status -eq 'running') {
        $Evidence.native_sample.status = 'failed'
        $Evidence.native_sample.error = $_.Exception.Message
    }
    throw
} finally {
    $Evidence.finished_utc = [DateTime]::UtcNow.ToString('o')
    Save-Evidence
    @(
        '## Windows candidate verification'
        "Status: $($Evidence.status)"
        "Native sample: $($Evidence.native_sample.status)"
        ''
        'See verification.json and lifecycle evidence.json for exact stages, versions, hashes, and exclusions.'
        'Artifacts are review candidates, not published releases or a claim of clean/offline acceptance.'
    ) | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
    Stop-Transcript | Out-Null
}
