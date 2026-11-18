# Shared bootstrap helpers for PMAI's run and build scripts.
# Windows PowerShell 5.1 or newer.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$script:PmaiRoot = Split-Path -Parent $PSScriptRoot
$script:PmaiPython = $null
$script:PmaiPythonTkMissing = $null
$script:PmaiPythonOld = $null
$script:PmaiProbePath = Join-Path $PSScriptRoot 'probe_python.py'


function Write-PmaiBanner {
    Write-Host ''
    Write-Host '  PMAI  ' -NoNewline -ForegroundColor Cyan
    Write-Host 'Project to Prompt'
    Write-Host '  ----------------------------------------' -ForegroundColor DarkGray
}

function Write-PmaiInfo {
    param([string]$Message)
    Write-Host '  > ' -NoNewline -ForegroundColor Cyan
    Write-Host $Message
}

function Write-PmaiOk {
    param([string]$Message)
    Write-Host '  OK ' -NoNewline -ForegroundColor Green
    Write-Host $Message
}

function Write-PmaiWarn {
    param([string]$Message)
    Write-Host '  ! ' -NoNewline -ForegroundColor Yellow
    Write-Host $Message
}

function ConvertTo-PmaiArgumentString {
    param([string[]]$Arguments)

    $parts = @()
    foreach ($argument in $Arguments) {
        if ([string]::IsNullOrEmpty($argument)) {
            $parts += '""'
        } elseif ($argument -match '[\s"]') {
            $parts += ('"' + ($argument -replace '"', '\"') + '"')
        } else {
            $parts += $argument
        }
    }
    return ($parts -join ' ')
}

function Get-PmaiPythonw {
    param([string]$Exe)

    $directory = Split-Path -Parent $Exe
    $name = [IO.Path]::GetFileName($Exe).ToLowerInvariant()
    $candidates = @()
    if ($name -eq 'py.exe') {
        $candidates += 'pyw.exe'
    }
    if ($name -eq 'python.exe' -or $name -eq 'python3.exe') {
        $candidates += 'pythonw.exe'
    }
    foreach ($candidate in $candidates) {
        $path = Join-Path $directory $candidate
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            return $path
        }
    }
    return $Exe
}

function Get-PmaiPythonCandidates {
    $candidates = New-Object System.Collections.Generic.List[object]
    $seen = @{}

    function Add-PmaiCandidate {
        param([string]$Exe, [string[]]$Prefix, [string]$Label)

        if ([string]::IsNullOrWhiteSpace($Exe)) {
            return
        }
        if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) {
            return
        }
        $key = ($Exe + '|' + ($Prefix -join ' ')).ToLowerInvariant()
        if ($seen.ContainsKey($key)) {
            return
        }
        $seen[$key] = $true
        $candidates.Add([pscustomobject]@{
            Exe = $Exe
            Prefix = @($Prefix)
            Label = $Label
        })
    }

    $py = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    if ($py) {
        Add-PmaiCandidate -Exe $py.Source -Prefix @('-3') -Label 'py -3'
        foreach ($version in @('3.13', '3.12', '3.11', '3.10')) {
            Add-PmaiCandidate -Exe $py.Source -Prefix @("-$version") -Label "py -$version"
        }
    }

    foreach ($name in @('python.exe', 'python3.exe')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source -and $command.Source -notmatch '\\WindowsApps\\') {
            Add-PmaiCandidate -Exe $command.Source -Prefix @() -Label $name
        }
    }

    $roots = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
        (Join-Path $env:ProgramFiles 'Python'),
        'C:\Python'
    )
    if (${env:ProgramFiles(x86)}) {
        $roots += (Join-Path ${env:ProgramFiles(x86)} 'Python')
    }

    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            continue
        }
        $directories = @(
            Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
                Sort-Object -Property Name -Descending
        )
        foreach ($directory in $directories) {
            Add-PmaiCandidate -Exe (Join-Path $directory.FullName 'python.exe') -Prefix @() -Label $directory.Name
        }
    }

    return $candidates.ToArray()
}

function Test-PmaiPython {
    param(
        [string]$Exe,
        [string[]]$Prefix,
        [string]$Label
    )

    if ([string]::IsNullOrWhiteSpace($Exe) -or -not (Test-Path -LiteralPath $Exe -PathType Leaf)) {
        return $null
    }

    try {
        $arguments = @($Prefix) + @($script:PmaiProbePath)
        $output = @(& $Exe @arguments 2>$null)
        if ($LASTEXITCODE -ne 0) {
            return $null
        }
    } catch {
        return $null
    }

    $versionText = $null
    $exeText = $null
    $hasTk = $false
    foreach ($line in $output) {
        $text = [string]$line
        if ($text.StartsWith('PMAI_EXE=')) {
            $exeText = $text.Substring('PMAI_EXE='.Length).Trim()
        } elseif ($text.StartsWith('PMAI_VERSION=')) {
            $versionText = $text.Substring('PMAI_VERSION='.Length).Trim()
        } elseif ($text -eq 'PMAI_TK=ok') {
            $hasTk = $true
        }
    }

    if (-not $versionText) {
        return $null
    }
    try {
        $version = [version]$versionText
    } catch {
        return $null
    }

    $resolvedExe = $Exe
    if ($exeText) {
        try {
            $decoded = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($exeText))
            if (Test-Path -LiteralPath $decoded -PathType Leaf) {
                $resolvedExe = $decoded
            }
        } catch {
            # Keep the original path when the launcher output cannot be decoded.
        }
    }

    return [pscustomobject]@{
        Exe = $resolvedExe
        Pythonw = Get-PmaiPythonw -Exe $resolvedExe
        Version = $version
        HasTk = $hasTk
        Label = $Label
    }
}

function Find-PmaiPython {
    $script:PmaiPythonTkMissing = $null
    $script:PmaiPythonOld = $null

    foreach ($candidate in @(Get-PmaiPythonCandidates)) {
        $info = Test-PmaiPython -Exe $candidate.Exe -Prefix $candidate.Prefix -Label $candidate.Label
        if (-not $info) {
            continue
        }
        if ($info.Version -lt [version]'3.10') {
            if (-not $script:PmaiPythonOld -or $info.Version -gt $script:PmaiPythonOld.Version) {
                $script:PmaiPythonOld = $info
            }
            continue
        }
        if (-not $info.HasTk) {
            if (-not $script:PmaiPythonTkMissing) {
                $script:PmaiPythonTkMissing = $info
            }
            continue
        }
        return $info
    }

    return $null
}

function Update-PmaiPath {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $combined = @($machine, $user) | Where-Object { $_ }
    if ($combined) {
        $env:Path = ($combined -join ';')
    }
}

function Install-PmaiPython {
    $winget = Get-Command 'winget.exe' -ErrorAction SilentlyContinue
    if ($winget) {
        Write-PmaiInfo 'Installing Python 3.12 with winget (this may take a minute)...'
        $wingetCode = -1
        try {
            $wingetOutput = @(
                & $winget.Source install --id Python.Python.3.12 -e --source winget --scope user --accept-package-agreements --accept-source-agreements --disable-interactivity 2>&1
            )
            $wingetCode = $LASTEXITCODE
            $wingetOutput | ForEach-Object { Write-Host $_ }
        } catch {
            Write-PmaiWarn "winget could not be started: $($_.Exception.Message)"
        }

        Update-PmaiPath
        if ($wingetCode -eq 0) {
            $found = Find-PmaiPython
            if ($found) {
                return $found
            }
        }
        Write-PmaiWarn "winget could not install Python (exit code $wingetCode). Trying python.org..."
    }

    $architecture = $env:PROCESSOR_ARCHITECTURE
    if ($env:PROCESSOR_ARCHITEW6432) {
        $architecture = $env:PROCESSOR_ARCHITEW6432
    }
    $suffix = ''
    switch ($architecture.ToUpperInvariant()) {
        'AMD64' { $suffix = '-amd64' }
        'ARM64' { $suffix = '-arm64' }
    }

    $url = "https://www.python.org/ftp/python/3.12.10/python-3.12.10$suffix.exe"
    $installer = Join-Path $env:TEMP 'pmai-python-3.12.10.exe'
    Write-PmaiInfo 'Downloading Python 3.12.10 from python.org...'

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    } catch {
        # Older systems may not expose the enum; Invoke-WebRequest still works.
    }

    try {
        Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    } catch {
        throw 'Could not download Python. Check your internet connection, or install Python 3.12 manually from https://www.python.org/downloads/ and run this again.'
    }

    try {
        Write-PmaiInfo 'Installing Python for the current user (this may take a minute)...'
        $installerArguments = @(
            '/quiet',
            'InstallAllUsers=0',
            'PrependPath=1',
            'Include_launcher=1',
            'Include_test=0',
            'Include_tcltk=1',
            'Include_pip=1',
            'Shortcuts=0'
        )
        $process = Start-Process -FilePath $installer -ArgumentList $installerArguments -Wait -PassThru
        if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 3010) {
            throw "The Python installer exited with code $($process.ExitCode)."
        }
    } finally {
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
    }

    Update-PmaiPath
    return Find-PmaiPython
}

function Initialize-PmaiPython {
    if ($script:PmaiPython) {
        return $script:PmaiPython
    }

    Write-PmaiInfo 'Looking for Python 3.10+ with Tkinter...'
    $runtime = Find-PmaiPython
    if (-not $runtime) {
        if ($script:PmaiPythonTkMissing) {
            Write-PmaiWarn "Python $($script:PmaiPythonTkMissing.Version) was found, but Tkinter is missing."
        } elseif ($script:PmaiPythonOld) {
            Write-PmaiWarn "Python $($script:PmaiPythonOld.Version) was found, but PMAI needs 3.10 or newer."
        } else {
            Write-PmaiWarn 'Python was not found.'
        }

        Write-PmaiInfo 'Setting up Python now. This is a one-time step.'
        $runtime = Install-PmaiPython
        if (-not $runtime) {
            $runtime = Find-PmaiPython
        }
    }

    if (-not $runtime) {
        if ($script:PmaiPythonTkMissing) {
            throw "Python is installed but Tkinter is missing. Run the Python installer, choose Modify, and enable 'tcl/tk and IDLE'."
        }
        throw 'PMAI could not set up Python. Install Python 3.12 from https://www.python.org/downloads/ (enable tcl/tk and IDLE, and Add python.exe to PATH), then try again.'
    }

    Write-PmaiOk "Using Python $($runtime.Version) ($($runtime.Label))."
    $script:PmaiPython = $runtime
    return $runtime
}

function Ensure-PmaiPip {
    param($Runtime)

    $arguments = @($Runtime.Prefix) + @('-m', 'pip', '--version')
    & $Runtime.Exe @arguments 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-PmaiInfo 'Preparing pip...'
    $arguments = @($Runtime.Prefix) + @('-m', 'ensurepip', '--upgrade')
    & $Runtime.Exe @arguments | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw 'pip is missing and could not be repaired. Reinstall Python with pip enabled.'
    }

    $arguments = @($Runtime.Prefix) + @('-m', 'pip', '--version')
    & $Runtime.Exe @arguments 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'pip is still not available after the repair attempt.'
    }
}

function Ensure-PmaiPyInstaller {
    param($Runtime)

    $arguments = @($Runtime.Prefix) + @('-m', 'PyInstaller', '--version')
    $version = @(& $Runtime.Exe @arguments 2>$null)
    if ($LASTEXITCODE -eq 0 -and $version.Count -gt 0) {
        Write-PmaiOk "PyInstaller $($version[-1]) is ready."
        return
    }

    Ensure-PmaiPip -Runtime $Runtime
    Write-PmaiInfo 'Installing PyInstaller (one-time, into your user profile)...'
    $arguments = @($Runtime.Prefix) + @(
        '-m', 'pip', 'install', '--user', '--upgrade', 'pyinstaller', '--disable-pip-version-check'
    )
    & $Runtime.Exe @arguments | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw 'PyInstaller could not be installed. Check your internet connection and try again.'
    }

    $arguments = @($Runtime.Prefix) + @('-m', 'PyInstaller', '--version')
    $version = @(& $Runtime.Exe @arguments 2>$null)
    if ($LASTEXITCODE -ne 0 -or $version.Count -eq 0) {
        throw 'PyInstaller was installed but could not be started.'
    }
    Write-PmaiOk "PyInstaller $($version[-1]) is ready."
}
