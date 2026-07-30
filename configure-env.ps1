param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $projectRoot ".env"
$examplePath = Join-Path $projectRoot ".env.example"

if (-not (Test-Path $envPath)) {
    Copy-Item $examplePath $envPath
}

$values = @{}
foreach ($line in Get-Content $envPath) {
    if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#")) {
        continue
    }
    $parts = $line -split "=", 2
    if ($parts.Length -eq 2) {
        $values[$parts[0]] = $parts[1]
    }
}

$prompts = @(
    @{ Key = "LOCAL_AI_AGENT_ENV"; Prompt = "Environment"; Default = "dev" },
    @{ Key = "LOCAL_AI_AGENT_APP_NAME"; Prompt = "App name"; Default = "local-ai-agent" },
    @{ Key = "LOCAL_AI_AGENT_MODEL_PRIMARY"; Prompt = "Primary model"; Default = "gemma-4-31b" },
    @{ Key = "LOCAL_AI_AGENT_MODEL_ROUTER"; Prompt = "Router model"; Default = "gemma-4-2b" },
    @{ Key = "LOCAL_AI_AGENT_QDRANT_URL"; Prompt = "Qdrant URL"; Default = "http://localhost:6333" },
    @{ Key = "LOCAL_AI_AGENT_QDRANT_COLLECTION"; Prompt = "Qdrant collection"; Default = "agent_memory" },
    @{ Key = "LOCAL_AI_AGENT_DOWNLOADS_WATCH_PATH"; Prompt = "Downloads watch path"; Default = "$HOME\Downloads" },
    @{ Key = "LOCAL_AI_AGENT_TELEGRAM_BOT_TOKEN"; Prompt = "Telegram bot token"; Default = "" },
    @{ Key = "LOCAL_AI_AGENT_TELEGRAM_ADMIN_CHAT_ID"; Prompt = "Telegram admin chat id"; Default = "" }
)

foreach ($item in $prompts) {
    $current = if ($values.ContainsKey($item.Key)) { $values[$item.Key] } else { $item.Default }
    $answer = Read-Host "$($item.Prompt) [$current]"
    if ([string]::IsNullOrWhiteSpace($answer)) {
        $values[$item.Key] = $current
    }
    else {
        $values[$item.Key] = $answer
    }
}

$orderedKeys = @(
    "LOCAL_AI_AGENT_ENV",
    "LOCAL_AI_AGENT_LOG_LEVEL",
    "LOCAL_AI_AGENT_APP_NAME",
    "LOCAL_AI_AGENT_MODEL_PRIMARY",
    "LOCAL_AI_AGENT_MODEL_ROUTER",
    "LOCAL_AI_AGENT_QDRANT_URL",
    "LOCAL_AI_AGENT_QDRANT_COLLECTION",
    "LOCAL_AI_AGENT_RUNTIME_LOG_PATH",
    "LOCAL_AI_AGENT_AUDIT_LOG_PATH",
    "LOCAL_AI_AGENT_TASK_STORE_PATH",
    "LOCAL_AI_AGENT_MEMORY_STORE_PATH",
    "LOCAL_AI_AGENT_BACKUP_DIR",
    "LOCAL_AI_AGENT_DOWNLOADS_WATCH_PATH",
    "LOCAL_AI_AGENT_ADMIN_UI_TITLE",
    "LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW",
    "LOCAL_AI_AGENT_TELEGRAM_BOT_TOKEN",
    "LOCAL_AI_AGENT_TELEGRAM_ADMIN_CHAT_ID"
)

$output = foreach ($key in $orderedKeys) {
    if ($values.ContainsKey($key)) {
        "$key=$($values[$key])"
    }
}

Set-Content -Path $envPath -Value $output -Encoding UTF8
Write-Host "Updated .env at $envPath" -ForegroundColor Green
