param()

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Advice {
    param([string]$Message)
    Write-Host "Tip: $Message" -ForegroundColor Yellow
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = $null
    while ((Get-Date) -lt $deadline) {
        try {
            $null = Invoke-RestMethod $Url
            return
        }
        catch {
            $lastError = $_.Exception.Message
            Start-Sleep -Seconds 2
        }
    }
    throw "Timed out waiting for $Url. Last error: $lastError"
}

function Test-PortListener {
    param([int]$Port)

    try {
        return @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    }
    catch {
        return @()
    }
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

try {
    Write-Step "Starting Local AI Agent (Docker-first)"

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker was not found in PATH. Install Docker Desktop and reopen the terminal."
    }

    Write-Step "Checking Docker daemon"
    docker info 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is not running. Start Docker Desktop, wait until it is Ready, then retry."
    }

    if (-not (Test-Path (Join-Path $projectRoot ".venv\Scripts\python.exe"))) {
        Write-Advice "Virtual environment is missing. Run windows-bootstrap.cmd once before daily start."
    }

    if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
        Write-Step "Creating .env from .env.example"
        Copy-Item ".env.example" ".env"
        Write-Advice "Run configure-env.cmd to customize local settings."
    }

    $existingApi = Test-PortListener -Port 8000
    if ($existingApi.Count -gt 0) {
        Write-Step "Port 8000 is already in use; checking if API is already healthy"
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:8000/health"
            if ($health.status -eq "ok") {
                Write-Host "API is already running on http://127.0.0.1:8000" -ForegroundColor Green
                Invoke-RestMethod "http://127.0.0.1:8000/status" | ConvertTo-Json -Depth 8
                Write-Advice "Use open-agent.cmd to open the local admin panel."
                Write-Advice "Use restart-agent.cmd if you need a forced rebuild."
                exit 0
            }
        }
        catch {
            throw "Port 8000 is busy, but /health is not responding. Stop the conflicting process or run stop-agent.cmd, then retry."
        }
    }

    Write-Step "Starting Docker services"
    Push-Location (Join-Path $projectRoot "infra")
    docker compose up --build -d qdrant api
    $dockerExitCode = $LASTEXITCODE
    Pop-Location
    if ($dockerExitCode -ne 0) {
        throw "docker compose failed with exit code $dockerExitCode. Run logs-agent.cmd for details."
    }

    Write-Step "Waiting for API readiness"
    Wait-ForUrl -Url "http://127.0.0.1:8000/health"

    Write-Step "Checking API status endpoint"
    Invoke-RestMethod "http://127.0.0.1:8000/status" | ConvertTo-Json -Depth 8

    Write-Host ""
    Write-Host "Local AI Agent started successfully." -ForegroundColor Green
    Write-Advice "Use open-agent.cmd to open the local admin panel."
    Write-Advice "Use healthcheck-agent.cmd to validate the environment."
}
catch {
    Write-Host ""
    Write-Host "Start failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Advice "Review docs/WINDOWS_SETUP_GUIDE.md for troubleshooting steps."
    Write-Advice "Common fixes: start Docker Desktop, free port 8000, run windows-bootstrap.cmd once."
    exit 1
}
