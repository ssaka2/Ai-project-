$ErrorActionPreference = "Stop"
$target = Join-Path (Split-Path $PSScriptRoot -Parent) ".env"
if (Test-Path $target) {
    Write-Host "Existing .env kept. Run docker compose up --build -d."
    exit 0
}
$bytes = New-Object byte[] 24
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$rng.Dispose()
$password = ([BitConverter]::ToString($bytes)).Replace("-", "") + "Aa1!"
$content = "SQL_PASSWORD=$password" + [Environment]::NewLine + "AI_ENABLED=false" + [Environment]::NewLine + "AI_MODEL=" + [Environment]::NewLine + "AI_API_KEY=" + [Environment]::NewLine
$stream = [System.IO.File]::Open($target, [System.IO.FileMode]::CreateNew)
$writer = New-Object System.IO.StreamWriter($stream)
try { $writer.Write($content) } finally { $writer.Dispose() }
Write-Host "Local configuration created. Run docker compose up --build -d."
