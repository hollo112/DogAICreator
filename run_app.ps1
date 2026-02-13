$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] .venv Python not found: $venvPython" -ForegroundColor Red
    Write-Host "Create venv first: py -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Push-Location $projectRoot
try {
    & $venvPython -m streamlit run app.py
}
finally {
    Pop-Location
}
