param(
    [switch]$RunFullTests
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found. Run windows-bootstrap.ps1 first."
}

Set-Location $projectRoot

& $venvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade base packaging tools."
}

& $venvPython -m pip install -e ".[dev,integrations]"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to refresh project dependencies."
}

& $venvPython -m apps.cli.main status
if ($LASTEXITCODE -ne 0) {
    throw "CLI smoke test failed."
}

if ($RunFullTests) {
    & $venvPython -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw "Full test suite failed."
    }
}

Write-Host "Agent environment updated successfully." -ForegroundColor Green
