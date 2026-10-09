param(
    [ValidateSet('Menu', 'Install', 'Uninstall', 'Reinstall', 'Check')]
    [string]$Action = 'Menu'
)
$ErrorActionPreference = 'Stop'
$script:UninstallRegistryKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{B1A827F6-93A7-4365-A494-D793125179DA}_is1'

function Get-VerifiedSetup([string]$ReleaseDirectory = $PSScriptRoot) {
    $release = Get-Content -LiteralPath (Join-Path $ReleaseDirectory 'release.json') -Raw | ConvertFrom-Json
    foreach ($field in @('version', 'installer', 'source_commit', 'sha256')) {
        if ($release.$field -isnot [string]) { throw "Missing or invalid $field in release.json." }
    }
    if ($release.version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+$' -or
        $release.installer -cne "StoryAtlasPreview-$($release.version)-Windows-x64-Offline-Setup.exe" -or
        $release.source_commit -notmatch '^[A-Fa-f0-9]{40}$') {
        throw 'Invalid release metadata in release.json.'
    }
    $setup = Join-Path $ReleaseDirectory $release.installer
    if (!(Test-Path -LiteralPath $setup -PathType Leaf) -or (Get-Item -LiteralPath $setup).Length -lt (1MB)) {
        throw 'The installer has not been downloaded. Run git lfs pull from the repository folder, then try again.'
    }
    if ($release.sha256 -notmatch '^[A-Fa-f0-9]{64}$' -or
        (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash -ne $release.sha256) {
        throw 'The installer checksum does not match this release. Run git lfs pull and try again.'
    }
    Write-Host "Ready: Story Atlas Preview $($release.version) (source $($release.source_commit))"
    return $setup
}

function Get-InstalledRegistration {
    if (!(Test-Path -LiteralPath $script:UninstallRegistryKey)) { return $null }
    $entry = Get-ItemProperty -LiteralPath $script:UninstallRegistryKey
    $location = $entry.InstallLocation
    # IsPathRooted also accepts drive-relative paths (C:folder and \folder).
    # Require a fully qualified drive or UNC path, and keep registry contents
    # out of cmd.exe so metacharacters can never become shell instructions.
    if ($location -isnot [string] -or
        $location -notmatch '^(?:[A-Za-z]:\\|\\\\[^\\]+\\[^\\]+)' -or
        $location -match '["\r\n]') {
        throw 'The registered installation directory is invalid. Use Install/update to repair the app first.'
    }
    return [pscustomobject]@{
        Directory = [IO.Path]::GetFullPath($location)
        UninstallString = [string]$entry.UninstallString
    }
}

function Get-InstalledUninstaller {
    $entry = Get-InstalledRegistration
    if (!$entry) { return $null }
    # Inno may choose unins001.exe after a reinstall; use its registered command,
    # but never execute command-line arguments or a path outside InstallLocation.
    $match = [regex]::Match($entry.UninstallString, '(?i)^"([^"\r\n]+\\unins[0-9]+\.exe)"$')
    if (!$match.Success) { throw 'The registered uninstall command is invalid. Use Windows Settings to uninstall.' }
    $uninstaller = $match.Groups[1].Value
    if ($uninstaller -notmatch '^(?:[A-Za-z]:\\|\\\\[^\\]+\\[^\\]+\\)') {
        throw 'The registered uninstall command is invalid. Use Windows Settings to uninstall.'
    }
    $parent = [IO.Path]::GetFullPath((Split-Path -Parent $uninstaller)).TrimEnd('\')
    if ($parent -ne $entry.Directory.TrimEnd('\')) { throw 'The registered uninstaller is outside the app installation directory.' }
    if (!(Test-Path -LiteralPath $uninstaller -PathType Leaf)) {
        throw 'The registered uninstaller is missing. Use Install/update to repair the app first.'
    }
    return $uninstaller
}

function Get-InstalledExecutable {
    $entry = Get-InstalledRegistration
    if ($entry) {
        $executable = [IO.Path]::Combine($entry.Directory, 'StoryAtlasPreview.exe')
        if (!(Test-Path -LiteralPath $executable -PathType Leaf)) {
            throw 'The registered Story Atlas app is missing. Use Install/update to repair it first.'
        }
        return $executable
    }
    # Keep the legacy default-path fallback only when no registration exists.
    # An invalid or broken custom registration must not launch a different copy.
    $executable = Join-Path $env:LOCALAPPDATA 'Programs\Story Atlas Preview\StoryAtlasPreview.exe'
    if (!(Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw 'Story Atlas is not ready to launch. Run Setup in installer, or follow README.md to set up source mode.'
    }
    return $executable
}

function ConvertTo-WindowsArgument([AllowEmptyString()][string]$Value) {
    # Windows PowerShell's Start-Process joins ArgumentList with spaces. Quote
    # each argument using the Windows argv rules, including trailing backslashes
    # and embedded quotes, so --home/--story paths remain single literal values.
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

function Invoke-InstalledApp([string[]]$AppArguments) {
    $executable = Get-InstalledExecutable
    $parameters = @{
        FilePath = $executable
        WorkingDirectory = Split-Path -Parent $executable
        Wait = $true
        PassThru = $true
    }
    if ($AppArguments.Count) {
        $parameters.ArgumentList = ($AppArguments | ForEach-Object { ConvertTo-WindowsArgument $_ }) -join ' '
    }
    Write-Host 'Starting the installed Story Atlas...'
    $process = Start-Process @parameters
    return $process.ExitCode
}

function Wait-ForUninstall {
    param(
        [Parameter(Mandatory = $true)][string]$Uninstaller,
        [ValidateRange(0, 300)][int]$TimeoutSeconds = 30,
        [ValidateRange(1, 1000)][int]$PollMilliseconds = 250
    )
    # Inno's original EXE can exit while its temporary clone is still cleaning
    # up. Do not parse the uninstall entry during that transition: the file or
    # some registry values can disappear before the entire key is removed.
    $timer = [Diagnostics.Stopwatch]::StartNew()
    do {
        $registered = Test-Path -LiteralPath $script:UninstallRegistryKey
        $uninstallerRemains = Test-Path -LiteralPath $Uninstaller -PathType Leaf
        if (!$registered -and !$uninstallerRemains) { return $true }
        if ($timer.Elapsed.TotalSeconds -ge $TimeoutSeconds) { return $false }
        Start-Sleep -Milliseconds $PollMilliseconds
    } while ($true)
}

function Invoke-Setup([string]$Setup, [string]$InstallDirectory) {
    Write-Host 'Follow Setup to install or replace the app. Stories and backups are preserved.'
    $arguments = @('/NORESTART', '/RESTARTEXITCODE=3010')
    if ($InstallDirectory) {
        # Uninstall removes Inno's previous-directory registry entry. Carry the
        # custom directory into the new wizard instead of silently resetting it.
        $directory = $InstallDirectory.TrimEnd('\')
        if ($directory -match '^[A-Za-z]:$') { $directory += '\.' }
        $arguments += '/DIR="' + $directory + '"'
    }
    $process = Start-Process -FilePath $Setup -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -eq 2) { Write-Host 'Setup was cancelled.'; return }
    if ($process.ExitCode -notin @(0, 3010)) { throw "Setup did not complete (code $($process.ExitCode))." }
    if ($process.ExitCode -eq 3010) { Write-Host 'Restart Windows to complete the update.' }
}

function Invoke-Uninstall([string]$Uninstaller = (Get-InstalledUninstaller)) {
    if (!$Uninstaller) { Write-Host 'Story Atlas Preview is not installed for this Windows account.'; return $true }
    Write-Host 'Follow the uninstaller. Your story files and backups will remain.'
    $process = Start-Process -FilePath $Uninstaller -ArgumentList '/NORESTART' -Wait -PassThru
    # Every nonzero Inno uninstall code means cancellation or failure. Never
    # launch a replacement after either, even if some files have disappeared.
    if ($process.ExitCode -ne 0) { throw "Uninstall was cancelled or did not complete (code $($process.ExitCode))." }
    if (!(Wait-ForUninstall -Uninstaller $Uninstaller)) {
        throw 'Uninstall cleanup did not finish within 30 seconds. Finish any open uninstall dialogs, then try again. Reinstall was not started.'
    }
    return $true
}

function Invoke-InstallationAction {
    param([Parameter(Mandatory = $true)][ValidateSet('Install', 'Uninstall', 'Reinstall', 'Check')][string]$Action)
    if ($Action -eq 'Uninstall') {
        $null = Invoke-Uninstall
        return
    }
    # Validate the replacement before offering to remove a working copy.
    $setup = Get-VerifiedSetup
    if ($Action -eq 'Check') { return }
    $installDirectory = $null
    if ($Action -eq 'Reinstall') {
        $uninstaller = Get-InstalledUninstaller
        if ($uninstaller) { $installDirectory = Split-Path -Parent $uninstaller }
        if (!(Invoke-Uninstall -Uninstaller $uninstaller)) { return }
    }
    Invoke-Setup -Setup $setup -InstallDirectory $installDirectory
}

# Importing the functions for isolated tests must never install or uninstall.
if ($MyInvocation.InvocationName -eq '.') { return }

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
    Invoke-InstallationAction -Action $Action
    exit 0
} catch {
    Write-Host "Could not complete installation: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
