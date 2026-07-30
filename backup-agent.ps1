param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $projectRoot "backups"
$archivePath = Join-Path $backupDir "local-ai-agent-backup-$timestamp.zip"
$stagingDir = Join-Path $backupDir "staging-$timestamp"

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
New-Item -ItemType Directory -Force -Path $stagingDir | Out-Null

if (Test-Path (Join-Path $projectRoot "runtime")) {
    Copy-Item (Join-Path $projectRoot "runtime") -Destination $stagingDir -Recurse -Force
}
if (Test-Path (Join-Path $projectRoot ".env")) {
    Copy-Item (Join-Path $projectRoot ".env") -Destination $stagingDir -Force
}
if (Test-Path (Join-Path $projectRoot "NOTICE")) {
    Copy-Item (Join-Path $projectRoot "NOTICE") -Destination $stagingDir -Force
}

Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $archivePath -Force
Remove-Item $stagingDir -Recurse -Force

Write-Host "Backup created: $archivePath" -ForegroundColor Green
