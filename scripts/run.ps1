[CmdletBinding()]
param(
    [switch]$Wait,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArguments
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')

try {
    Write-PmaiBanner
    $runtime = Initialize-PmaiPython

    $launchArguments = @((Join-Path $script:PmaiRoot 'app.py'))
    if ($AppArguments) {
        $launchArguments += $AppArguments
    }
    $argumentString = ConvertTo-PmaiArgumentString -Arguments $launchArguments

    Write-PmaiInfo 'Opening PMAI...'
    $process = Start-Process -FilePath $runtime.Pythonw -ArgumentList $argumentString -WorkingDirectory $script:PmaiRoot -PassThru

    if ($Wait) {
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) {
            throw "PMAI exited with code $($process.ExitCode)."
        }
        Write-PmaiOk 'PMAI closed normally.'
    } else {
        Start-Sleep -Milliseconds 900
        $process.Refresh()
        if ($process.HasExited -and $process.ExitCode -ne 0) {
            throw "PMAI closed immediately with code $($process.ExitCode)."
        }
        Write-PmaiOk 'PMAI is running.'
    }
} catch {
    Write-Host ''
    Write-Host '  PMAI could not start.' -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ''
    exit 1
}
