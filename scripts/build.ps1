[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$NoSmokeTest
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')

$exitCode = 0

try {
    Write-PmaiBanner
    Write-PmaiInfo 'Preparing the PMAI build...'
    $runtime = Initialize-PmaiPython
    Ensure-PmaiPyInstaller -Runtime $runtime

    $assetsDirectory = Join-Path $script:PmaiRoot 'assets'
    $iconPath = Join-Path $assetsDirectory 'pmai.ico'
    New-Item -ItemType Directory -Force -Path $assetsDirectory | Out-Null

    if ($Clean -or -not (Test-Path -LiteralPath $iconPath -PathType Leaf)) {
        Write-PmaiInfo 'Generating the application icon...'
        $arguments = @($runtime.Prefix) + @(
            (Join-Path $script:PmaiRoot 'tools\make_icon.py'),
            '--output',
            $iconPath
        )
        & $runtime.Exe @arguments
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $iconPath -PathType Leaf)) {
            throw 'The application icon could not be generated.'
        }
    } else {
        Write-PmaiInfo "Using the existing icon: $iconPath"
    }

    $buildDirectory = Join-Path $script:PmaiRoot 'build'
    $distDirectory = Join-Path $script:PmaiRoot 'dist'
    New-Item -ItemType Directory -Force -Path $buildDirectory, $distDirectory | Out-Null

    $executable = Join-Path $distDirectory 'PMAI.exe'
    if (Test-Path -LiteralPath $executable -PathType Leaf) {
        Remove-Item -LiteralPath $executable -Force
    }

    Write-PmaiInfo 'Building dist\PMAI.exe with PyInstaller...'
    $arguments = @($runtime.Prefix) + @(
        '-m', 'PyInstaller',
        '--noconfirm',
        '--clean',
        '--onefile',
        '--windowed',
        '--name', 'PMAI',
        '--icon', $iconPath,
        '--collect-submodules', 'pmai',
        '--distpath', $distDirectory,
        '--workpath', $buildDirectory,
        '--specpath', $buildDirectory,
        (Join-Path $script:PmaiRoot 'app.py')
    )

    Push-Location $script:PmaiRoot
    try {
        & $runtime.Exe @arguments
        $buildCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    if ($buildCode -ne 0) {
        throw "PyInstaller failed with exit code $buildCode."
    }
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw 'PyInstaller finished, but dist\PMAI.exe was not created.'
    }

    $sizeMb = [math]::Round((Get-Item -LiteralPath $executable).Length / 1MB, 1)
    Write-PmaiOk "Built dist\PMAI.exe ($sizeMb MB)."

    if (-not $NoSmokeTest) {
        Write-PmaiInfo 'Checking that the executable starts...'
        $testProcess = Start-Process -FilePath $executable -ArgumentList '--smoke-test' -WorkingDirectory $script:PmaiRoot -PassThru
        if (-not $testProcess.WaitForExit(120000)) {
            try {
                $testProcess.Kill()
            } catch {
                # The process may have exited between the check and the kill.
            }
            throw 'The built program did not finish its start-up check within two minutes.'
        }
        if ($testProcess.ExitCode -ne 0) {
            throw "The built program failed its start-up check (exit code $($testProcess.ExitCode))."
        }
        Write-PmaiOk 'Start-up check passed.'
    }

    Write-Host ''
    Write-PmaiOk 'Build complete. Double-click dist\PMAI.exe to run PMAI.'
} catch {
    Write-Host ''
    Write-Host '  PMAI build failed.' -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ''
    $exitCode = 1
}

exit $exitCode
