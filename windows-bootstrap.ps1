param(
    [switch]$UseDocker,
    [switch]$RunApi,
    [switch]$RunTests,
    [switch]$InstallPlaywrightBrowsers,
    [switch]$InstallMissingTools,
    [switch]$Interactive
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

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3.12")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    if ($InstallMissingTools -and (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Step "Installing Python 3.12 via winget"
        winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        if (Get-Command py -ErrorAction SilentlyContinue) {
            return @("py", "-3.12")
        }
        if (Get-Command python -ErrorAction SilentlyContinue) {
            return @("python")
        }
    }
    throw "Python 3.12 was not found. Install it first or rerun with -InstallMissingTools."
}

function Invoke-Python {
    param(
        [string[]]$PythonCommand,
        [string[]]$Arguments
    )

    if ($PythonCommand.Length -gt 1) {
        & $PythonCommand[0] $PythonCommand[1..($PythonCommand.Length - 1)] @Arguments
    }
    else {
        & $PythonCommand[0] @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Arguments -join ' ')"
    }
}

function Get-VenvPython {
    param([string]$ProjectRoot)
    return Join-Path $ProjectRoot ".venv\Scripts\python.exe"
}

function Ensure-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        if ($InstallMissingTools -and (Get-Command winget -ErrorAction SilentlyContinue)) {
            Write-Step "Installing Docker Desktop via winget"
            winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
        }
    }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker was not found. Install Docker Desktop or rerun with -InstallMissingTools."
    }
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $null = Invoke-RestMethod $Url
            return
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "Timed out waiting for $Url"
}

function Select-InteractiveMode {
    Write-Host ""
    Write-Host "Select bootstrap mode:" -ForegroundColor Cyan
    Write-Host "1) Setup dependencies only"
    Write-Host "2) Setup + run tests"
    Write-Host "3) Setup + Docker-first start"
    Write-Host "4) Setup + local API"
    Write-Host "5) Setup + install Playwright browser"
    $choice = Read-Host "Enter choice [1-5]"
    switch ($choice) {
        "2" { $script:RunTests = $true }
        "3" { $script:UseDocker = $true }
        "4" { $script:RunApi = $true }
        "5" { $script:InstallPlaywrightBrowsers = $true }
        default { }
    }
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (
    $Interactive -or
    (-not $UseDocker -and -not $RunApi -and -not $RunTests -and -not $InstallPlaywrightBrowsers)
) {
    Select-InteractiveMode
}

Write-Step "Bootstrapping Local AI Agent in $projectRoot"

try {
    $pythonCommand = Get-PythonCommand
    $venvPython = Get-VenvPython -ProjectRoot $projectRoot

    Write-Step "Checking Python version"
    Invoke-Python -PythonCommand $pythonCommand -Arguments @("--version")

    if (-not (Test-Path $venvPython)) {
        Write-Step "Creating virtual environment"
        Invoke-Python -PythonCommand $pythonCommand -Arguments @("-m", "venv", ".venv")
    }

    Write-Step "Upgrading pip"
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip."
    }

    Write-Step "Installing project dependencies"
    & $venvPython -m pip install -e ".[dev,integrations]"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install project dependencies."
    }

    if ($InstallPlaywrightBrowsers) {
        Write-Step "Installing Playwright Chromium browser"
        & $venvPython -m playwright install chromium
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install Playwright browser."
        }
    }

    if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
        Write-Step "Creating .env from .env.example"
        Copy-Item ".env.example" ".env"
        Write-Advice "Run configure-env.cmd to customize local settings."
    }

    if ($RunTests) {
        Write-Step "Running test suite"
        & $venvPython -m pytest
        if ($LASTEXITCODE -ne 0) {
            throw "Pytest failed."
        }
    }

    Write-Step "Running CLI status check"
    & $venvPython -m apps.cli.main status
    if ($LASTEXITCODE -ne 0) {
        throw "CLI status check failed."
    }

    if ($UseDocker) {
        Write-Step "Starting Docker services"
        Ensure-Docker
        Push-Location (Join-Path $projectRoot "infra")
        docker compose up --build -d qdrant coding api
        $dockerExitCode = $LASTEXITCODE
        Pop-Location
        if ($dockerExitCode -ne 0) {
            throw "docker compose failed."
        }

        Write-Step "Waiting for API readiness"
        Wait-ForUrl -Url "http://127.0.0.1:8000/health"

        Write-Step "Checking API status endpoint"
        Invoke-RestMethod "http://127.0.0.1:8000/status" | ConvertTo-Json -Depth 8
        Write-Advice "Use open-agent.cmd to open the local admin panel."
    }

    if ($RunApi -and -not $UseDocker) {
        Write-Step "Starting local FastAPI server"
        & $venvPython -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
        exit $LASTEXITCODE
    }

    Write-Step "Bootstrap completed successfully"
    Write-Host "Virtual environment: .venv" -ForegroundColor Green
    Write-Host "Config file: .env" -ForegroundColor Green
    Write-Host "Guide: docs/WINDOWS_SETUP_GUIDE.md" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "Bootstrap failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Advice "Review docs/WINDOWS_SETUP_GUIDE.md for troubleshooting steps."
    Write-Advice "Run healthcheck-agent.cmd after startup to validate the environment."
    exit 1
}
