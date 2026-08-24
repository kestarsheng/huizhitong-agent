# 汇智通一键启动：RabbitMQ + Agent Runtime + Audit Worker
# 用法：powershell -ExecutionPolicy Bypass -File scripts/start-services.ps1
# 前置：Docker Desktop 已运行；敏感配置写在 scripts/env.local.ps1（已 gitignore）
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $PSScriptRoot 'env.local.ps1'
if (Test-Path -LiteralPath $envFile) { . $envFile }

$pyDir = Join-Path $root 'python\agent-runtime'
$py = Join-Path $pyDir 'hzt-agent-venv\Scripts\python.exe'
$logs = Join-Path $root 'logs'

New-Item -ItemType Directory -Force -Path $logs | Out-Null
if (-not (Test-Path -LiteralPath $py)) { throw "未找到 Python 虚拟环境：$py" }
if (-not $env:DEEPSEEK_API_KEY) { Write-Warning '未检测到 DEEPSEEK_API_KEY，Agent Runtime 的 LLM 调用可能失败' }
$env:PYTHONIOENCODING = 'utf-8'

Write-Host '==> 1/3 启动 RabbitMQ（Docker Compose）'
docker compose -f (Join-Path $root 'deploy\docker-compose.infra.yml') up -d rabbitmq
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    $status = docker inspect -f '{{.State.Health.Status}}' huizhitong-rabbitmq-1 2>$null
    if ($status -eq 'healthy') { $healthy = $true; break }
    Start-Sleep -Seconds 2
}
if ($healthy) { Write-Host 'RabbitMQ 已就绪（huizhitong-rabbitmq-1）' }
else { Write-Warning 'RabbitMQ 未在 60 秒内就绪，审计将降级直写 MySQL' }

Write-Host '==> 2/3 启动 Agent Runtime（端口 8000）'
$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Host "Agent Runtime 已在运行（PID $($listener.OwningProcess)），跳过启动"
} else {
    $proc = Start-Process -FilePath $py -ArgumentList '-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8000' `
        -WorkingDirectory $pyDir -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs 'agent-runtime.out.log') `
        -RedirectStandardError (Join-Path $logs 'agent-runtime.err.log') -PassThru
    Write-Host "Agent Runtime 已启动（PID $($proc.Id)）"
}

Write-Host '==> 3/3 启动 Audit Worker'
$worker = Start-Process -FilePath $py -ArgumentList '-m','app.audit.worker' `
    -WorkingDirectory $pyDir -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'audit-worker.out.log') `
    -RedirectStandardError (Join-Path $logs 'audit-worker.err.log') -PassThru
Set-Content -LiteralPath (Join-Path $logs 'audit-worker.pid') -Value $worker.Id
Write-Host "Audit Worker 已启动（PID $($worker.Id)）"

Write-Host '全部完成。日志目录：' $logs