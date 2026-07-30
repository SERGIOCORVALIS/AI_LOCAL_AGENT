param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

function Test-Step {
    param(
        [string]$Name,
        [scriptblock]$Check
    )

    try {
        & $Check
        Write-Host "[OK] $Name" -ForegroundColor Green
    }
    catch {
        Write-Host "[FAIL] $Name - $($_.Exception.Message)" -ForegroundColor Red
        $script:failed = $true
    }
}

$failed = $false
Set-Location $projectRoot

Test-Step "Virtual environment" {
    if (-not (Test-Path $venvPython)) {
        throw ".venv python not found"
    }
}

Test-Step ".env file" {
    if (-not (Test-Path ".env")) {
        throw ".env file not found"
    }
}

Test-Step "Python CLI status" {
    & $venvPython -m apps.cli.main status | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "CLI status failed"
    }
}

Test-Step "Docker executable" {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "docker command not found"
    }
}

Test-Step "Docker services" {
    Push-Location (Join-Path $projectRoot "infra")
    docker compose ps
    $exitCode = $LASTEXITCODE
    Pop-Location
    if ($exitCode -ne 0) {
        throw "docker compose ps failed"
    }
}

Test-Step "API /health" {
    $health = Invoke-RestMethod "http://127.0.0.1:8000/health"
    if ($health.status -ne "ok") {
        throw "unexpected health payload"
    }
}

Test-Step "API /status" {
    $status = Invoke-RestMethod "http://127.0.0.1:8000/status"
    if (-not $status.memory_backend) {
        throw "missing memory_backend"
    }
}

Test-Step "API /metrics" {
    $metrics = Invoke-RestMethod "http://127.0.0.1:8000/metrics"
    if ($null -eq $metrics.task_count) {
        throw "missing task_count"
    }
}

if ($failed) {
    exit 1
}

Write-Host "Healthcheck completed successfully." -ForegroundColor Cyan
