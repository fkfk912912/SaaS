$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskEnvFile = Join-Path $PSScriptRoot 'SaaSBackend\.env'
if (-not (Test-Path -LiteralPath $taskEnvFile)) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SaaSBackend\.env.example') -Destination $taskEnvFile
}
$taskKeyLine = Get-Content -LiteralPath $taskEnvFile | Where-Object { $_ -match '^OPENAI_API_KEY=.+\S' }
if (-not $taskKeyLine) { throw '请先在 SaaSBackend/.env 中填写 OPENAI_API_KEY，使用你的 DeepSeek Key。' }
$taskPreviousProxy = @{}
try {
    # Docker Buildx also requests registry tokens from the Windows client process.
    # Inherit an enabled single-address Windows proxy when the shell has none.
    $taskSystemProxy = Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
    $taskProxyAddress = [string]$taskSystemProxy.ProxyServer
    if ($taskSystemProxy.ProxyEnable -eq 1 -and $taskProxyAddress -and $taskProxyAddress -notmatch '[=;]') {
        if ($taskProxyAddress -notmatch '^https?://') { $taskProxyAddress = 'http://' + $taskProxyAddress }
        foreach ($taskProxyName in @('HTTP_PROXY', 'HTTPS_PROXY')) {
            $taskProxyValue = [Environment]::GetEnvironmentVariable($taskProxyName, 'Process')
            if (-not $taskProxyValue) {
                $taskPreviousProxy[$taskProxyName] = $taskProxyValue
                [Environment]::SetEnvironmentVariable($taskProxyName, $taskProxyAddress, 'Process')
            }
        }
        if ($taskPreviousProxy.Count -gt 0) { Write-Host 'Docker build: using the Windows system proxy.' }
    }
    docker compose --env-file $taskEnvFile -f (Join-Path $PSScriptRoot 'compose.yaml') up -d --build
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose 启动失败，请查看上方错误。' }
}
finally {
    foreach ($taskProxyName in $taskPreviousProxy.Keys) {
        [Environment]::SetEnvironmentVariable($taskProxyName, $taskPreviousProxy[$taskProxyName], 'Process')
    }
}
Write-Host '前端：http://localhost:5175  API：http://localhost:8010/docs'
