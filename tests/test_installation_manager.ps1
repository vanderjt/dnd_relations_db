# Dependency-free Windows PowerShell 5.1 tests. All registry/process operations
# are mocked; no installation, user registration, or story data is touched.
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_installation_manager.ps1
$ErrorActionPreference = 'Stop'
$manager = Join-Path (Split-Path -Parent $PSScriptRoot) 'installer\manage_installation.ps1'

# Fail closed if any test forgets to replace an external operation.
function Start-Process { throw 'Tests must not start a real installer or uninstaller.' }
function Read-Host { throw 'Importing the manager must not display its menu.' }
function Get-ItemProperty { throw 'Tests must not read real registry entries.' }
function Test-Path {
    param([string]$LiteralPath, [string]$PathType)
    if ($LiteralPath -match '^(HKCU:|HKLM:|Registry::)') { throw 'Tests must not read the real registry.' }
    $parameters = @{LiteralPath = $LiteralPath}
    if ($PathType) { $parameters.PathType = $PathType }
    Microsoft.PowerShell.Management\Test-Path @parameters
}
. $manager

function Assert-Equal($Actual, $Expected) {
    if ($Actual -cne $Expected) { throw "Expected [$Expected], got [$Actual]." }
}
function Assert-Throws([scriptblock]$Body, [string]$Pattern) {
    try { & $Body } catch {
        if ($_.Exception.Message -notlike $Pattern) { throw "Unexpected error: $($_.Exception.Message)" }
        return
    }
    throw "Expected an error matching [$Pattern]."
}
$script:passed = 0
$script:failed = @()
function Invoke-Test([string]$Name, [scriptblock]$Body) {
    try {
        & $Body
        $script:passed++
        Write-Host "PASS: $Name"
    } catch {
        $script:failed += $Name
        Write-Host "FAIL: $Name - $($_.Exception.Message)" -ForegroundColor Red
    }
}

$fixture = Join-Path ([IO.Path]::GetTempPath()) ('story-atlas-manager-tests-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $fixture
$fixtureSetup = Join-Path $fixture 'StoryAtlasPreview-1.2.3-Windows-x64-Offline-Setup.exe'
[IO.File]::WriteAllBytes($fixtureSetup, (New-Object byte[] (1MB)))
function Write-ReleaseFixture([hashtable]$Changes = @{}) {
    $release = @{
        version = '1.2.3'
        installer = [IO.Path]::GetFileName($fixtureSetup)
        source_commit = '0123456789abcdef0123456789abcdef01234567'
        sha256 = (Get-FileHash -LiteralPath $fixtureSetup -Algorithm SHA256).Hash
    }
    foreach ($key in $Changes.Keys) { $release[$key] = $Changes[$key] }
    $release | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $fixture 'release.json') -Encoding UTF8
}

try {
    Invoke-Test 'valid replacement manifest and checksum' {
        Write-ReleaseFixture
        Assert-Equal (Get-VerifiedSetup -ReleaseDirectory $fixture) $fixtureSetup
    }
    Invoke-Test 'manifest version must match installer filename' {
        Write-ReleaseFixture @{version = '9.9.9'}
        Assert-Throws { Get-VerifiedSetup -ReleaseDirectory $fixture } '*Invalid release metadata*'
    }
    Invoke-Test 'manifest must contain a full source commit' {
        Write-ReleaseFixture @{source_commit = 'not-a-commit'}
        Assert-Throws { Get-VerifiedSetup -ReleaseDirectory $fixture } '*Invalid release metadata*'
    }
    Invoke-Test 'manifest fields must be strings' {
        Write-ReleaseFixture @{version = @('1.2.3')}
        Assert-Throws { Get-VerifiedSetup -ReleaseDirectory $fixture } '*invalid version*'
    }
    Invoke-Test 'installer path traversal is rejected' {
        Write-ReleaseFixture @{installer = '..\StoryAtlasPreview-1.2.3-Windows-x64-Offline-Setup.exe'}
        Assert-Throws { Get-VerifiedSetup -ReleaseDirectory $fixture } '*Invalid release metadata*'
    }
    Invoke-Test 'checksum mismatch stops verification' {
        Write-ReleaseFixture @{sha256 = ('0' * 64)}
        Assert-Throws { Get-VerifiedSetup -ReleaseDirectory $fixture } '*checksum does not match*'
    }
    Invoke-Test 'missing installer is rejected' {
        Write-ReleaseFixture
        function Test-Path { return $false }
        Assert-Throws { Get-VerifiedSetup -ReleaseDirectory $fixture } '*has not been downloaded*'
    }
    Invoke-Test 'LFS pointer is not an installer' {
        Write-ReleaseFixture
        function Get-Item { return @{Length = 130} }
        Assert-Throws { Get-VerifiedSetup -ReleaseDirectory $fixture } '*has not been downloaded*'
    }
    Invoke-Test 'custom registered path and numbered uninstaller' {
        function Test-Path { return $true }
        function Get-ItemProperty {
            return @{UninstallString = '"D:\My Apps\Story Atlas\unins001.exe"'; InstallLocation = 'D:\My Apps\Story Atlas\'}
        }
        Assert-Equal (Get-InstalledUninstaller) 'D:\My Apps\Story Atlas\unins001.exe'
    }
    Invoke-Test 'uninstaller arguments cannot be injected from registry' {
        function Test-Path { return $true }
        function Get-ItemProperty {
            return @{UninstallString = '"D:\Story Atlas\unins000.exe" /SILENT'; InstallLocation = 'D:\Story Atlas'}
        }
        Assert-Throws { Get-InstalledUninstaller } '*uninstall command is invalid*'
    }
    Invoke-Test 'uninstaller outside registered install is rejected' {
        function Test-Path { return $true }
        function Get-ItemProperty {
            return @{UninstallString = '"D:\Other App\unins000.exe"'; InstallLocation = 'D:\Story Atlas'}
        }
        Assert-Throws { Get-InstalledUninstaller } '*outside the app installation directory*'
    }
    Invoke-Test 'relative install directory is rejected' {
        function Test-Path { return $true }
        function Get-ItemProperty {
            return @{UninstallString = '"D:\Story Atlas\unins000.exe"'; InstallLocation = 'D:Story Atlas'}
        }
        Assert-Throws { Get-InstalledUninstaller } '*installation directory is invalid*'
    }
    Invoke-Test 'missing registered uninstaller requests repair' {
        function Test-Path { param($LiteralPath); return $LiteralPath -eq $script:UninstallRegistryKey }
        function Get-ItemProperty {
            return @{UninstallString = '"D:\Story Atlas\unins000.exe"'; InstallLocation = 'D:\Story Atlas'}
        }
        Assert-Throws { Get-InstalledUninstaller } '*registered uninstaller is missing*'
    }
    Invoke-Test 'absent registration means not installed' {
        function Test-Path { return $false }
        Assert-Equal (Get-InstalledUninstaller) $null
        Assert-Equal (Invoke-Uninstall) $true
    }
    Invoke-Test 'installed launcher resolves a custom path literally' {
        function Test-Path { return $true }
        function Get-ItemProperty { return @{InstallLocation = 'C:\My Apps & Stories!\Story Atlas'} }
        Assert-Equal (Get-InstalledExecutable) 'C:\My Apps & Stories!\Story Atlas\StoryAtlasPreview.exe'
    }
    Invoke-Test 'installed launcher rejects quotes newlines and relative registration' {
        function Test-Path { return $true }
        function Get-ItemProperty { return @{InstallLocation = $script:badLocation} }
        foreach ($location in @('C:Story Atlas', '\Story Atlas', 'C:\Story" & calc & "', "C:\Story`nAtlas", $null)) {
            $script:badLocation = $location
            Assert-Throws { Get-InstalledExecutable } '*installation directory is invalid*'
        }
    }
    Invoke-Test 'installed launcher does not hide a broken custom registration' {
        function Test-Path { param($LiteralPath); return $LiteralPath -eq $script:UninstallRegistryKey }
        function Get-ItemProperty { return @{InstallLocation = 'C:\Missing App'} }
        Assert-Throws { Get-InstalledExecutable } '*registered Story Atlas app is missing*'
    }
    Invoke-Test 'legacy default fallback is used only without registration' {
        function Test-Path { param($LiteralPath); return $LiteralPath -ne $script:UninstallRegistryKey }
        $expected = Join-Path $env:LOCALAPPDATA 'Programs\Story Atlas Preview\StoryAtlasPreview.exe'
        Assert-Equal (Get-InstalledExecutable) $expected
    }
    Invoke-Test 'missing installed copies have a setup instruction' {
        function Test-Path { return $false }
        Assert-Throws { Get-InstalledExecutable } '*Story Atlas is not ready to launch*'
    }
    Invoke-Test 'Windows argument quoting preserves spaces quotes and backslashes' {
        Assert-Equal (ConvertTo-WindowsArgument '--home') '"--home"'
        Assert-Equal (ConvertTo-WindowsArgument 'C:\My Stories\') '"C:\My Stories\\"'
        Assert-Equal (ConvertTo-WindowsArgument 'say "hi"') '"say \"hi\""'
        Assert-Equal (ConvertTo-WindowsArgument 'ends with \"') '"ends with \\\""'
        Assert-Equal (ConvertTo-WindowsArgument '') '""'
    }
    Invoke-Test 'installed launch forwards story and home arguments without a shell' {
        function Get-InstalledExecutable { return 'C:\My Apps & Stories!\StoryAtlasPreview.exe' }
        function Start-Process {
            param($FilePath, $WorkingDirectory, $ArgumentList, [switch]$Wait, [switch]$PassThru)
            Assert-Equal $FilePath 'C:\My Apps & Stories!\StoryAtlasPreview.exe'
            Assert-Equal $WorkingDirectory 'C:\My Apps & Stories!'
            Assert-Equal $ArgumentList '"--home" "C:\My Stories\\" "--story" "C:\My Stories\A & B!.atlas-preview"'
            Assert-Equal $Wait.IsPresent $true
            Assert-Equal $PassThru.IsPresent $true
            return @{ExitCode = 42}
        }
        Assert-Equal (Invoke-InstalledApp -AppArguments @('--home', 'C:\My Stories\', '--story', 'C:\My Stories\A & B!.atlas-preview')) 42
    }
    Invoke-Test 'installed launch supports no arguments' {
        function Get-InstalledExecutable { return 'C:\Story Atlas\StoryAtlasPreview.exe' }
        function Start-Process {
            param($FilePath, $WorkingDirectory, $ArgumentList, [switch]$Wait, [switch]$PassThru)
            if ($PSBoundParameters.ContainsKey('ArgumentList')) { throw 'Empty ArgumentList must be omitted.' }
            return @{ExitCode = 0}
        }
        Assert-Equal (Invoke-InstalledApp -AppArguments @()) 0
    }
    Invoke-Test 'cleanup waits for both registration and original executable' {
        $script:pollReads = 0
        $script:pollSleeps = 0
        function Test-Path {
            $script:pollReads++
            # The registry goes first; its uninstaller survives one more poll.
            return $script:pollReads -in @(1, 2, 4)
        }
        function Start-Sleep { $script:pollSleeps++ }
        Assert-Equal (Wait-ForUninstall -Uninstaller 'D:\Story Atlas\unins000.exe') $true
        Assert-Equal $script:pollReads 6
        Assert-Equal $script:pollSleeps 2
    }
    Invoke-Test 'cleanup tolerates executable disappearing before registry' {
        $script:pollReads = 0
        function Test-Path {
            $script:pollReads++
            return $script:pollReads -in @(1, 2, 3)
        }
        function Start-Sleep { }
        Assert-Equal (Wait-ForUninstall -Uninstaller 'D:\Story Atlas\unins000.exe') $true
        Assert-Equal $script:pollReads 6
    }
    Invoke-Test 'cleanup timeout is bounded' {
        function Test-Path { return $true }
        function Start-Sleep { throw 'Zero timeout must not sleep.' }
        Assert-Equal (Wait-ForUninstall -Uninstaller 'D:\Story Atlas\unins000.exe' -TimeoutSeconds 0) $false
    }
    Invoke-Test 'uninstall does not declare success after timeout' {
        function Start-Process { return @{ExitCode = 0} }
        function Wait-ForUninstall { return $false }
        Assert-Throws { Invoke-Uninstall -Uninstaller 'D:\Story Atlas\unins000.exe' } '*Reinstall was not started*'
    }
    Invoke-Test 'every nonzero uninstall exit stops reinstall' {
        function Get-VerifiedSetup { return $fixtureSetup }
        function Get-InstalledUninstaller { return 'D:\Story Atlas\unins000.exe' }
        function Start-Process { return @{ExitCode = $script:uninstallExitCode} }
        function Wait-ForUninstall { throw 'Cancelled/failed uninstall must not be polled.' }
        function Invoke-Setup { throw 'Cancelled/failed uninstall must not start Setup.' }
        foreach ($code in @(1, 2, 5, 3010)) {
            $script:uninstallExitCode = $code
            Assert-Throws { Invoke-InstallationAction -Action Reinstall } "*Uninstall was cancelled or did not complete (code $code).*"
        }
    }
    Invoke-Test 'replacement validation precedes any uninstall' {
        function Get-VerifiedSetup { throw 'Replacement validation failed.' }
        function Get-InstalledUninstaller { throw 'Must not inspect or change installation before validation.' }
        function Invoke-Uninstall { throw 'Must not remove a working installation before validation.' }
        function Invoke-Setup { throw 'Must not start an unverified setup.' }
        Assert-Throws { Invoke-InstallationAction -Action Reinstall } 'Replacement validation failed.'
    }
    Invoke-Test 'Check only verifies release without touching installation' {
        $script:verified = 0
        function Get-VerifiedSetup { $script:verified++; return $fixtureSetup }
        function Get-InstalledUninstaller { throw 'Check must not inspect installation.' }
        function Invoke-Uninstall { throw 'Check must not uninstall.' }
        function Invoke-Setup { throw 'Check must not install.' }
        Invoke-InstallationAction -Action Check
        Assert-Equal $script:verified 1
    }
    Invoke-Test 'Install update never uninstalls' {
        $script:setupCalls = 0
        function Get-VerifiedSetup { return $fixtureSetup }
        function Invoke-Uninstall { throw 'Update must not uninstall first.' }
        function Invoke-Setup { $script:setupCalls++ }
        Invoke-InstallationAction -Action Install
        Assert-Equal $script:setupCalls 1
    }
    Invoke-Test 'standalone uninstall needs no replacement installer' {
        $script:uninstallCalls = 0
        function Get-VerifiedSetup { throw 'Uninstall must not require release files.' }
        function Invoke-Uninstall { $script:uninstallCalls++; return $true }
        Invoke-InstallationAction -Action Uninstall
        Assert-Equal $script:uninstallCalls 1
    }
    Invoke-Test 'reinstall retains custom directory and waits before Setup' {
        $script:stages = @()
        function Get-VerifiedSetup { $script:stages += 'verify'; return $fixtureSetup }
        function Get-InstalledUninstaller { $script:stages += 'registration'; return 'D:\My Apps\Story Atlas\unins002.exe' }
        function Invoke-Uninstall {
            param($Uninstaller)
            Assert-Equal $Uninstaller 'D:\My Apps\Story Atlas\unins002.exe'
            $script:stages += 'uninstall'
            return $true
        }
        function Invoke-Setup {
            param($Setup, $InstallDirectory)
            Assert-Equal $Setup $fixtureSetup
            Assert-Equal $InstallDirectory 'D:\My Apps\Story Atlas'
            $script:stages += 'setup'
        }
        Invoke-InstallationAction -Action Reinstall
        Assert-Equal ($script:stages -join ',') 'verify,registration,uninstall,setup'
    }
    Invoke-Test 'incomplete uninstall cannot start Setup' {
        function Get-VerifiedSetup { return $fixtureSetup }
        function Get-InstalledUninstaller { return 'D:\Story Atlas\unins000.exe' }
        function Invoke-Uninstall { return $false }
        function Invoke-Setup { throw 'Incomplete uninstall must not start Setup.' }
        Invoke-InstallationAction -Action Reinstall
    }
    Invoke-Test 'reinstall without an installed copy uses Setup defaults' {
        $script:setupCalls = 0
        function Get-VerifiedSetup { return $fixtureSetup }
        function Get-InstalledUninstaller { return $null }
        function Invoke-Setup {
            param($Setup, $InstallDirectory)
            Assert-Equal ([string]$InstallDirectory) ''
            $script:setupCalls++
        }
        Invoke-InstallationAction -Action Reinstall
        Assert-Equal $script:setupCalls 1
    }
    Invoke-Test 'Setup quotes custom path and requests explicit restart code' {
        function Start-Process {
            param($FilePath, $ArgumentList, [switch]$Wait, [switch]$PassThru)
            Assert-Equal $FilePath $fixtureSetup
            Assert-Equal ($ArgumentList -join ' ') '/NORESTART /RESTARTEXITCODE=3010 /DIR="D:\My Apps\Story Atlas"'
            Assert-Equal $Wait.IsPresent $true
            Assert-Equal $PassThru.IsPresent $true
            return @{ExitCode = 0}
        }
        Invoke-Setup -Setup $fixtureSetup -InstallDirectory 'D:\My Apps\Story Atlas\'
    }
    Invoke-Test 'Setup accepts restart-required success' {
        function Start-Process { return @{ExitCode = 3010} }
        Invoke-Setup -Setup $fixtureSetup
    }
    Invoke-Test 'Setup cancellation is reported without retry' {
        $script:setupCalls = 0
        function Start-Process { $script:setupCalls++; return @{ExitCode = 2} }
        Invoke-Setup -Setup $fixtureSetup
        Assert-Equal $script:setupCalls 1
    }
    Invoke-Test 'Setup errors stop the manager' {
        function Start-Process { return @{ExitCode = 7} }
        Assert-Throws { Invoke-Setup -Setup $fixtureSetup } '*Setup did not complete (code 7).*'
    }
} finally {
    Remove-Item -LiteralPath $fixture -Recurse -Force
}

if ($script:failed.Count) { throw "$($script:failed.Count) manager tests failed: $($script:failed -join ', ')" }
Write-Host "$script:passed installation manager tests passed. Registry and process operations were mocked."
