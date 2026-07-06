$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PrereqScript = Join-Path $PSScriptRoot "check_prerequisites.ps1"
$Prereqs = & $PrereqScript -Quiet

if (-not $Prereqs.CoreReady) {
    Write-Host "Missing core prerequisites:"
    & $PrereqScript
    exit 1
}

if (-not $Prereqs.Ollama) {
    Write-Host "Ollama is not available. Deterministic pages can still run, but AI report writing will be disabled."
    if ($Prereqs.Winget) {
        Write-Host "Install command: winget install Ollama.Ollama"
    }
} else {
    try {
        $Tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 4
        $ModelNames = @($Tags.models | ForEach-Object { $_.name })
        if ($ModelNames -notcontains "gemma3:4b") {
            Write-Host "Ollama is reachable, but gemma3:4b is missing. Run:"
            Write-Host "  ollama pull gemma3:4b"
        }
    } catch {
        Write-Host "Ollama is installed but http://localhost:11434 is not reachable. Start Ollama before generating reports."
    }
}

$VenvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Backend virtual environment is missing. Run setup first:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1"
    exit 1
}

Write-Host "Starting Saville Music Persona"
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend:  http://localhost:8000"
Write-Host "Press Ctrl+C to stop both local servers."

$BackendJob = Start-Job -Name "saville-backend" -ScriptBlock {
    param($Root, $Python)
    Set-Location $Root
    & $Python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
} -ArgumentList $Root, $VenvPython

$FrontendJob = Start-Job -Name "saville-frontend" -ScriptBlock {
    param($Root, $Npm)
    Set-Location $Root
    & $Npm --prefix frontend run dev
} -ArgumentList $Root, $Prereqs.Npm

try {
    while ($true) {
        Receive-Job $BackendJob
        Receive-Job $FrontendJob
        Start-Sleep -Seconds 1
    }
} finally {
    Stop-Job $BackendJob, $FrontendJob -ErrorAction SilentlyContinue
    Remove-Job $BackendJob, $FrontendJob -Force -ErrorAction SilentlyContinue
}

