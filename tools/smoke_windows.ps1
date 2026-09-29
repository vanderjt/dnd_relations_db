param([string]$Executable = "$PSScriptRoot\..\dist\StoryAtlas\StoryAtlas.exe")
$ErrorActionPreference = "Stop"
$workspace = (Resolve-Path -LiteralPath "$PSScriptRoot\..").Path
$output = Join-Path $workspace "build-verification"
New-Item -ItemType Directory -Path $output -Force | Out-Null
$report = Join-Path $output "packaged-smoke.json"
$data = Join-Path $output "user-data"
$oldPath = $env:PATH
$names = @('PYTHONHOME','PYTHONPATH','CONDA_PREFIX','CONDA_DEFAULT_ENV','TCL_LIBRARY','TK_LIBRARY','MPLCONFIGDIR')
$saved = @{}
try {
    foreach ($name in $names) { $saved[$name] = [Environment]::GetEnvironmentVariable($name); [Environment]::SetEnvironmentVariable($name, $null) }
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $process = Start-Process -FilePath $Executable -ArgumentList @('--self-test', "`"$report`"", '--data-dir', "`"$data`"") -WorkingDirectory $output -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Packaged smoke test failed. See $report" }
    $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if (-not $result.ok -or -not $result.frozen) { throw "Report did not confirm a working frozen build" }
    Get-Content -LiteralPath $report
} finally {
    $env:PATH = $oldPath
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $saved[$name]) }
}
