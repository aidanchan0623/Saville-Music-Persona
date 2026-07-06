$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PrereqScript = Join-Path $PSScriptRoot "check_prerequisites.ps1"

Write-Host "Saville Music Persona setup"
Write-Host "Project root: $Root"

$Prereqs = & $PrereqScript -Quiet

if (-not $Prereqs.CoreReady) {
    Write-Host ""
    Write-Host "One or more core prerequisites are missing. Install the missing tools above, then re-run this script."
    & $PrereqScript
    exit 1
}

$PythonExe = $Prereqs.Python.Exe
$PythonArgs = @($Prereqs.Python.Args)

$VenvPath = Join-Path $Root "backend\.venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating backend virtual environment..."
    & $PythonExe @PythonArgs -m venv $VenvPath
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
Write-Host "Installing Python dependencies..."
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $Root "backend\requirements.txt")

Write-Host "Installing frontend dependencies with npm.cmd..."
& $Prereqs.Npm --prefix (Join-Path $Root "frontend") install

if (-not $Prereqs.Ollama) {
    Write-Host ""
    Write-Host "Ollama is not installed or not on PATH."
    if ($Prereqs.Winget) {
        Write-Host "You can install it with:"
        Write-Host "  winget install Ollama.Ollama"
    } else {
        Write-Host "Install Ollama from https://ollama.com/download/windows"
    }
    Write-Host "After installing Ollama, re-run this setup script so it can pull gemma3:4b."
    exit 0
}

Write-Host "Pulling local Ollama model gemma3:4b..."
& $Prereqs.Ollama pull gemma3:4b

Write-Host "Installed Ollama models:"
& $Prereqs.Ollama list

try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 4 | Out-Null
    Write-Host "Ollama endpoint is reachable at http://localhost:11434."
} catch {
    Write-Host "Ollama is installed but the local endpoint is not reachable."
    Write-Host "Start Ollama, then run:"
    Write-Host "  ollama pull gemma3:4b"
}

Write-Host ""
Write-Host "Setup complete. Next run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\run_dev.ps1"
