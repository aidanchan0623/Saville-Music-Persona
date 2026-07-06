param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Write-Check {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail
    )
    if (-not $Quiet) {
        $status = if ($Ok) { "OK" } else { "MISSING" }
        Write-Host "[$status] $Name - $Detail"
    }
}

function Get-PythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        try {
            $versionText = & $python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and [version]$versionText -ge [version]"3.11") {
                return [pscustomobject]@{ Exe = $python.Source; Args = @() }
            }
        } catch {
            # Continue to the py launcher check.
        }
    }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $versionText = & $py.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and [version]$versionText -ge [version]"3.11") {
                return [pscustomobject]@{ Exe = $py.Source; Args = @() }
            }
        } catch {
            # Continue to an explicit 3.11 launcher check.
        }
        try {
            $versionText = & $py.Source -3.11 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ([version]$versionText -ge [version]"3.11") {
                return [pscustomobject]@{ Exe = $py.Source; Args = @("-3.11") }
            }
        } catch {
            return $null
        }
    }
    return $null
}

$pythonCommand = Get-PythonCommand
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
}
$gitCommand = Get-Command git -ErrorAction SilentlyContinue
$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
$wingetCommand = Get-Command winget -ErrorAction SilentlyContinue

Write-Check "Python 3.11+" ([bool]$pythonCommand) ($(if ($pythonCommand) { "$($pythonCommand.Exe) $($pythonCommand.Args -join ' ')" } else { "Install Python 3.11 or newer from python.org." }))
Write-Check "Node.js" ([bool]$nodeCommand) ($(if ($nodeCommand) { $nodeCommand.Source } else { "Install Node.js 20 or newer." }))
Write-Check "npm" ([bool]$npmCommand) ($(if ($npmCommand) { $npmCommand.Source } else { "npm was not found. If PowerShell blocks npm.ps1, npm.cmd is preferred." }))
Write-Check "Git" ([bool]$gitCommand) ($(if ($gitCommand) { $gitCommand.Source } else { "Install Git for Windows." }))
Write-Check "Ollama" ([bool]$ollamaCommand) ($(if ($ollamaCommand) { $ollamaCommand.Source } elseif ($wingetCommand) { "Install with: winget install Ollama.Ollama" } else { "Install from https://ollama.com/download/windows" }))

$allCore = [bool]$pythonCommand -and [bool]$nodeCommand -and [bool]$npmCommand -and [bool]$gitCommand

[pscustomobject]@{
    Python = $pythonCommand
    Node = if ($nodeCommand) { $nodeCommand.Source } else { $null }
    Npm = if ($npmCommand) { $npmCommand.Source } else { $null }
    Git = if ($gitCommand) { $gitCommand.Source } else { $null }
    Ollama = if ($ollamaCommand) { $ollamaCommand.Source } else { $null }
    Winget = if ($wingetCommand) { $wingetCommand.Source } else { $null }
    CoreReady = $allCore
}
