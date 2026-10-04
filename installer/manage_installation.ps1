param(
    [ValidateSet('Menu', 'Install', 'Uninstall', 'Reinstall', 'Check')]
    [string]$Action = 'Menu'
)
$ErrorActionPreference = 'Stop'

function Get-VerifiedSetup {
    $release = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'release.json') -Raw | ConvertFrom-Json
    if ($release.installer -notmatch '^StoryAtlasPreview-[0-9]+\.[0-9]+\.[0-9]+-Windows-x64-Offline-Setup\.exe$') {
        throw 'Invalid installer filename in release.json.'
    }
    $setup = Join-Path $PSScriptRoot $release.installer
    if (!(Test-Path -LiteralPath $setup -PathType Leaf) -or (Get-Item -LiteralPath $setup).Length -lt 1MB) {
        throw 'The installer has not been downloaded. Run git lfs pull from the repository folder, then try again.'
    }
    if ($release.sha256 -notmatch '^[A-Fa-f0-9]{64}$' -or
        (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash -ne $release.sha256) {
        throw 'The installer checksum does not match this release. Run git lfs pull and try again.'
    }
    Write-Host "Ready: Story Atlas Preview $($release.version) (source $($release.source_commit))"
    return $setup
}

function Get-InstalledUninstaller {
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{B1A827F6-93A7-4365-A494-D793125179DA}_is1'
    if (!(Test-Path -LiteralPath $key)) { return $null }
    $entry = Get-ItemProperty -LiteralPath $key
    # Inno records the installed directory even if the user chose a custom path.
    $uninstaller = Join-Path $entry.InstallLocation 'unins000.exe'
    if (!(Test-Path -LiteralPath $uninstaller -PathType Leaf)) {
        throw 'The registered uninstaller is missing. Use Install/update to repair the app first.'
    }
    return $uninstaller
}

function Invoke-Setup([string]$Setup) {
    Write-Host 'Follow Setup to install or replace the app. Stories and backups are preserved.'
    $process = Start-Process -FilePath $Setup -ArgumentList '/NORESTART' -Wait -PassThru
    if ($process.ExitCode -eq 2) { Write-Host 'Setup was cancelled.'; return }
    if ($process.ExitCode -notin @(0, 3010)) { throw "Setup did not complete (code $($process.ExitCode))." }
    if ($process.ExitCode -eq 3010) { Write-Host 'Restart Windows to complete the update.' }
}

function Invoke-Uninstall {
    $uninstaller = Get-InstalledUninstaller
    if (!$uninstaller) { Write-Host 'Story Atlas Preview is not installed for this Windows account.'; return $true }
    Write-Host 'Follow the uninstaller. Your story files and backups will remain.'
    $process = Start-Process -FilePath $uninstaller -ArgumentList '/NORESTART' -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Uninstall did not complete (code $($process.ExitCode))." }
    if (Get-InstalledUninstaller) { Write-Host 'Uninstall was cancelled or is incomplete.'; return $false }
    return $true
}

try {
    if ($Action -eq 'Menu') {
        Write-Host 'Story Atlas Preview - installation manager'
        Write-Host 'Close Story Atlas before changing its installation.'
        Write-Host '1. Install/update (recommended for new features)'
        Write-Host '2. Uninstall app (keep stories and backups)'
        Write-Host '3. Uninstall and reinstall (keep stories and backups)'
        Write-Host '4. Exit'
        switch (Read-Host 'Choose 1, 2, 3, or 4') {
            '1' { $Action = 'Install' }
            '2' { $Action = 'Uninstall' }
            '3' { $Action = 'Reinstall' }
            '4' { exit 0 }
            default { throw 'No valid option selected.' }
        }
    }
    if ($Action -eq 'Uninstall') {
        $null = Invoke-Uninstall
    } else {
        # Validate the new installer before offering to remove a working copy.
        $setup = Get-VerifiedSetup
        if ($Action -eq 'Check') { exit 0 }
        if ($Action -eq 'Install' -or (Invoke-Uninstall)) { Invoke-Setup $setup }
    }
    exit 0
} catch {
    Write-Host "Could not complete installation: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
