$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BundledPython = "C:\Users\Utkarsh Raj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Port = if ($args.Count -gt 0) { $args[0] } else { "8000" }

Set-Location $ProjectRoot

if (Test-Path $BundledPython) {
    $Python = $BundledPython
} else {
    $Python = "python"
}

$ExistingPort = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($ExistingPort) {
    Write-Host "Port $Port is already in use, so FitGen AI was not started there." -ForegroundColor Yellow
    Write-Host "Run with another port, for example:"
    Write-Host "  .\run-fitgen.ps1 8010"
    Write-Host ""
    Write-Host "Then open http://127.0.0.1:8010"
    exit 1
}

Write-Host "Starting FitGen AI on http://127.0.0.1:$Port"
Write-Host "Keep this PowerShell window open while using the app."
Write-Host ""

& $Python -m uvicorn app.main:app --app-dir $ProjectRoot --host 127.0.0.1 --port $Port --reload
