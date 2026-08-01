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

$defaultAllow = "bootstrap,noop,reflect,sandbox_run,web_fetch,web_search,coding_agent,code_intel,fs_scan,fs_watch,vision_inspect,browser_open"
$defaultDeny = "format_disk,wipe_system,exfiltrate_secrets"

$ollamaUrl = if ($values.ContainsKey("LOCAL_AI_AGENT_OLLAMA_URL")) {
    $values["LOCAL_AI_AGENT_OLLAMA_URL"]
}
else {
    "http://127.0.0.1:11434"
}
$suggestedPrimary = "gemma4"
$suggestedEmbed = "nomic-embed-text"
try {
    $tags = Invoke-RestMethod -Uri "$ollamaUrl/api/tags" -TimeoutSec 3
    $names = @()
    if ($null -ne $tags.models) {
        $names = @($tags.models | ForEach-Object { $_.name } | Where-Object { $_ })
    }
    if ($names.Count -gt 0) {
        Write-Host "Ollama models at ${ollamaUrl}:" -ForegroundColor Cyan
        foreach ($name in $names) {
            Write-Host "  - $name"
        }
        $chatCandidate = $names | Where-Object {
            $_ -notmatch "embed|whisper|tts"
        } | Select-Object -First 1
        $embedCandidate = $names | Where-Object { $_ -match "embed" } | Select-Object -First 1
        if ($chatCandidate) {
            $suggestedPrimary = $chatCandidate
        }
        if ($embedCandidate) {
            $suggestedEmbed = $embedCandidate
        }
    }
    else {
        Write-Host "Ollama is online but no models are installed yet." -ForegroundColor Yellow
        Write-Host "Suggested: ollama pull gemma4 && ollama pull nomic-embed-text" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "Ollama not reachable at $ollamaUrl (continuing with defaults)." -ForegroundColor Yellow
}

$prompts = @(
    @{ Key = "LOCAL_AI_AGENT_ENV"; Prompt = "Environment"; Default = "dev" },
    @{ Key = "LOCAL_AI_AGENT_APP_NAME"; Prompt = "App name"; Default = "local-ai-agent" },
    @{ Key = "LOCAL_AI_AGENT_MODEL_PRIMARY"; Prompt = "Primary model (chat/swarm)"; Default = $suggestedPrimary },
    @{ Key = "LOCAL_AI_AGENT_MODEL_ROUTER"; Prompt = "Router model"; Default = $suggestedPrimary },
    @{ Key = "LOCAL_AI_AGENT_MODEL_VISION"; Prompt = "Vision model"; Default = $suggestedPrimary },
    @{ Key = "LOCAL_AI_AGENT_MODEL_EMBED"; Prompt = "Embedding model"; Default = $suggestedEmbed },
    @{ Key = "LOCAL_AI_AGENT_EMBEDDING_PREFER_NATIVE"; Prompt = "Prefer native Ollama embedding dims (true/false)"; Default = "true" },
    @{ Key = "LOCAL_AI_AGENT_OLLAMA_URL"; Prompt = "Ollama URL"; Default = $ollamaUrl },
    @{ Key = "LOCAL_AI_AGENT_QDRANT_URL"; Prompt = "Qdrant URL"; Default = "http://localhost:6333" },
    @{ Key = "LOCAL_AI_AGENT_QDRANT_COLLECTION"; Prompt = "Qdrant collection"; Default = "agent_memory" },
    @{ Key = "LOCAL_AI_AGENT_DOWNLOADS_WATCH_PATH"; Prompt = "Downloads watch path"; Default = "$HOME\Downloads" },
    @{ Key = "LOCAL_AI_AGENT_SANDBOX_PREFER_DOCKER"; Prompt = "Prefer Docker sandbox (true/false)"; Default = "true" },
    @{ Key = "LOCAL_AI_AGENT_CODING_AGENTS_ENABLED"; Prompt = "Enable Ollama coding CLIs (true/false)"; Default = "true" },
    @{ Key = "LOCAL_AI_AGENT_CODING_AGENT_DEFAULT"; Prompt = "Coding agent default (auto|codex|opencode|droid|claude)"; Default = "auto" },
    @{ Key = "LOCAL_AI_AGENT_CODING_AGENT_TIMEOUT_SECONDS"; Prompt = "Coding agent timeout seconds"; Default = "300" },
    @{ Key = "LOCAL_AI_AGENT_API_BIND_HOST"; Prompt = "API bind host"; Default = "127.0.0.1" },
    @{ Key = "LOCAL_AI_AGENT_TRUSTED_HOSTS"; Prompt = "Trusted hosts (csv)"; Default = "127.0.0.1,localhost" },
    @{ Key = "LOCAL_AI_AGENT_API_TOKEN"; Prompt = "API token (blank=disabled)"; Default = "" },
    @{ Key = "LOCAL_AI_AGENT_REQUIRE_API_TOKEN"; Prompt = "Require API token in prod (true/false)"; Default = "false" },
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

if (-not $values.ContainsKey("LOCAL_AI_AGENT_LOG_LEVEL")) {
    $values["LOCAL_AI_AGENT_LOG_LEVEL"] = "INFO"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_RUNTIME_LOG_PATH")) {
    $values["LOCAL_AI_AGENT_RUNTIME_LOG_PATH"] = "./runtime/logs/agent.log"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_AUDIT_LOG_PATH")) {
    $values["LOCAL_AI_AGENT_AUDIT_LOG_PATH"] = "./runtime/audit/events.jsonl"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_TASK_STORE_PATH")) {
    $values["LOCAL_AI_AGENT_TASK_STORE_PATH"] = "./runtime/tasks/state.json"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_MEMORY_STORE_PATH")) {
    $values["LOCAL_AI_AGENT_MEMORY_STORE_PATH"] = "./runtime/memory/preferences.json"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_BACKUP_DIR")) {
    $values["LOCAL_AI_AGENT_BACKUP_DIR"] = "./backups"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_ADMIN_UI_TITLE")) {
    $values["LOCAL_AI_AGENT_ADMIN_UI_TITLE"] = "Local AI Agent Admin"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW")) {
    $values["LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW"] = $defaultAllow
}
else {
    $allow = $values["LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW"]
    foreach ($actionName in @("fs_watch", "web_search", "coding_agent", "write_file")) {
        if ($allow -notmatch [regex]::Escape($actionName)) {
            $allow = $allow.TrimEnd(",") + ",$actionName"
        }
    }
    $values["LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW"] = $allow
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_DENIED_EXECUTE_ACTIONS_RAW")) {
    $values["LOCAL_AI_AGENT_DENIED_EXECUTE_ACTIONS_RAW"] = $defaultDeny
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_SANDBOX_PREFER_DOCKER")) {
    $values["LOCAL_AI_AGENT_SANDBOX_PREFER_DOCKER"] = "true"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_EMBEDDING_PREFER_NATIVE")) {
    $values["LOCAL_AI_AGENT_EMBEDDING_PREFER_NATIVE"] = "true"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_API_BIND_HOST")) {
    $values["LOCAL_AI_AGENT_API_BIND_HOST"] = "127.0.0.1"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_TRUSTED_HOSTS")) {
    $values["LOCAL_AI_AGENT_TRUSTED_HOSTS"] = "127.0.0.1,localhost"
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_API_TOKEN")) {
    $values["LOCAL_AI_AGENT_API_TOKEN"] = ""
}
if (-not $values.ContainsKey("LOCAL_AI_AGENT_REQUIRE_API_TOKEN")) {
    $values["LOCAL_AI_AGENT_REQUIRE_API_TOKEN"] = "false"
}

$orderedKeys = @(
    "LOCAL_AI_AGENT_ENV",
    "LOCAL_AI_AGENT_LOG_LEVEL",
    "LOCAL_AI_AGENT_APP_NAME",
    "LOCAL_AI_AGENT_MODEL_PRIMARY",
    "LOCAL_AI_AGENT_MODEL_ROUTER",
    "LOCAL_AI_AGENT_MODEL_VISION",
    "LOCAL_AI_AGENT_MODEL_EMBED",
    "LOCAL_AI_AGENT_EMBEDDING_PREFER_NATIVE",
    "LOCAL_AI_AGENT_OLLAMA_URL",
    "LOCAL_AI_AGENT_QDRANT_URL",
    "LOCAL_AI_AGENT_QDRANT_COLLECTION",
    "LOCAL_AI_AGENT_RUNTIME_LOG_PATH",
    "LOCAL_AI_AGENT_AUDIT_LOG_PATH",
    "LOCAL_AI_AGENT_TASK_STORE_PATH",
    "LOCAL_AI_AGENT_MEMORY_STORE_PATH",
    "LOCAL_AI_AGENT_BACKUP_DIR",
    "LOCAL_AI_AGENT_DOWNLOADS_WATCH_PATH",
    "LOCAL_AI_AGENT_ADMIN_UI_TITLE",
    "LOCAL_AI_AGENT_SANDBOX_PREFER_DOCKER",
    "LOCAL_AI_AGENT_CODING_AGENTS_ENABLED",
    "LOCAL_AI_AGENT_CODING_AGENT_DEFAULT",
    "LOCAL_AI_AGENT_CODING_AGENT_TIMEOUT_SECONDS",
    "LOCAL_AI_AGENT_CODING_AGENT_MODEL",
    "LOCAL_AI_AGENT_CODING_AGENTS_URL",
    "LOCAL_AI_AGENT_API_BIND_HOST",
    "LOCAL_AI_AGENT_TRUSTED_HOSTS",
    "LOCAL_AI_AGENT_API_TOKEN",
    "LOCAL_AI_AGENT_REQUIRE_API_TOKEN",
    "LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW",
    "LOCAL_AI_AGENT_DENIED_EXECUTE_ACTIONS_RAW",
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
