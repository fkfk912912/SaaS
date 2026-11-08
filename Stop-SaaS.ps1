$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
docker compose --env-file (Join-Path $PSScriptRoot 'SaaSBackend\.env') -f (Join-Path $PSScriptRoot 'compose.yaml') down
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose 停止失败，请查看上方错误。' }
