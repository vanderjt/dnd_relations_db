# No named parameters: every command-line value belongs to the app, including
# --home/--story. Capture them before importing the installation helpers.
$appArguments = @($args)
. (Join-Path $PSScriptRoot 'manage_installation.ps1')
try {
    exit (Invoke-InstalledApp -AppArguments $appArguments)
} catch {
    Write-Host "Story Atlas could not start: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
