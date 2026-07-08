$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Output = Join-Path $Root "backend\private\browser.json"

if (-not (Test-Path $Python)) {
    Write-Host "Backend virtual environment is missing. Run setup first:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1"
    exit 1
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Output) | Out-Null

Write-Host "Manual browser-header fallback"
Write-Host ""
Write-Host "This stores sensitive YouTube Music request headers in backend/private/browser.json."
Write-Host "Do not commit it. Do not share it. This script does not extract cookies automatically."
Write-Host ""
Write-Host "Paste the copied request headers below, then press Ctrl+Z and Enter on a new line."
Write-Host ""

$Script = @"
import sys
from pathlib import Path
from ytmusicapi import setup

headers_raw = sys.stdin.read()
if not headers_raw.strip():
    raise SystemExit("No headers were pasted.")
output = Path(r"$Output")
output.parent.mkdir(parents=True, exist_ok=True)
setup(filepath=str(output), headers_raw=headers_raw)
print(f"browser.json created at {output}")
"@

$TempScript = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), ".py")
try {
    Set-Content -LiteralPath $TempScript -Value $Script -Encoding UTF8
    & $Python $TempScript
} finally {
    Remove-Item -LiteralPath $TempScript -Force -ErrorAction SilentlyContinue
}
