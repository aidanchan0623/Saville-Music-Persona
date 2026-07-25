$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Npm = (Get-Command npm.cmd -ErrorAction Stop).Source

function Test-LocalPort([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

if (-not (Test-Path $Python)) { throw "Backend virtual environment is missing. Run scripts\\setup_windows.ps1 first." }
if (-not (Test-LocalPort 8000)) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "Set-Location '$Root'; & '$Python' -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000"
}
if (-not (Test-LocalPort 5173)) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "Set-Location '$Root'; & '$Npm' --prefix frontend run dev"
}

$deadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 500
    try { $ready = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5173" -TimeoutSec 2).StatusCode -eq 200 } catch { $ready = $false }
} while (-not $ready -and (Get-Date) -lt $deadline)
if (-not $ready) { throw "Saville Music Persona did not become ready within 30 seconds." }
Start-Process "http://127.0.0.1:5173"
