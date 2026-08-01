param(
    [switch]$NoCache,
    [switch]$Pull
)

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
        [int]$TimeoutSeconds = 120
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

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$infraDir = Join-Path $projectRoot "infra"
Set-Location $projectRoot

try {
    Write-Step "Rebuilding Local AI Agent Docker stack"

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker was not found in PATH. Install Docker Desktop and reopen the terminal."
    }

    Write-Step "Checking Docker daemon"
    docker info 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is not running. Start Docker Desktop, wait until it is Ready, then retry."
    }

    if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
        Write-Step "Creating .env from .env.example"
        Copy-Item ".env.example" ".env"
        Write-Advice "Run configure-env.ps1 to customize local settings."
    }

    Push-Location $infraDir
    try {
        Write-Step "Stopping compose services"
        docker compose stop qdrant coding api
        if ($LASTEXITCODE -ne 0) {
            Write-Advice "Stop returned non-zero; continuing with rebuild."
        }

        $buildArgs = @("compose", "build")
        if ($NoCache) {
            $buildArgs += "--no-cache"
        }
        if ($Pull) {
            $buildArgs += "--pull"
        }
        $buildArgs += @("api", "coding")

        Write-Step ("Building API + coding sidecar images" + ($(if ($NoCache) { " (no cache)" } else { "" })))
        & docker @buildArgs
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose build failed with exit code $LASTEXITCODE."
        }

        Write-Step "Recreating and starting services"
        docker compose up -d --force-recreate --remove-orphans qdrant coding api
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose up failed with exit code $LASTEXITCODE. Run logs-agent.cmd for details."
        }
    }
    finally {
        Pop-Location
    }

    Write-Step "Waiting for coding sidecar health"
    Wait-ForUrl -Url "http://127.0.0.1:8091/health"

    Write-Step "Waiting for API health"
    Wait-ForUrl -Url "http://127.0.0.1:8000/health"

    Write-Step "Coding agents readiness"
    Invoke-RestMethod "http://127.0.0.1:8091/agents" | ConvertTo-Json -Depth 8

    Write-Step "API status"
    Invoke-RestMethod "http://127.0.0.1:8000/status" | ConvertTo-Json -Depth 8

    Write-Host ""
    Write-Host "Docker rebuild finished successfully." -ForegroundColor Green
    Write-Advice "Admin panel: open-admin-panel.cmd or http://127.0.0.1:8000/admin"
    Write-Advice "Coding sidecar: http://127.0.0.1:8091/agents"
    Write-Advice "Logs: logs-agent.cmd"
}
catch {
    Write-Host ""
    Write-Host "Rebuild failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Advice "Review docs/WINDOWS_SETUP_GUIDE.md for troubleshooting steps."
    Write-Advice "Common fixes: start Docker Desktop, free port 8000, check logs-agent.cmd."
    exit 1
}
