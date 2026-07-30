param(
    [Parameter(Mandatory = $true)]
    [string]$ArchivePath
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$tempDir = Join-Path $projectRoot "backups\restore-temp"

if (-not (Test-Path $ArchivePath)) {
    throw "Archive not found: $ArchivePath"
}

$confirmation = Read-Host "This will overwrite runtime and .env if present. Type RESTORE to continue"
if ($confirmation -ne "RESTORE") {
    throw "Restore cancelled."
}

if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
Expand-Archive -Path $ArchivePath -DestinationPath $tempDir -Force

if (Test-Path (Join-Path $tempDir "runtime")) {
    Copy-Item (Join-Path $tempDir "runtime") -Destination $projectRoot -Recurse -Force
}
if (Test-Path (Join-Path $tempDir ".env")) {
    Copy-Item (Join-Path $tempDir ".env") -Destination (Join-Path $projectRoot ".env") -Force
}

Remove-Item $tempDir -Recurse -Force
Write-Host "Restore completed from $ArchivePath" -ForegroundColor Green
