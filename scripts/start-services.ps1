# 汇智通一键启动：RabbitMQ + Agent Runtime + Audit Worker + Tool Service + Gateway + Frontend
# 用法：powershell -ExecutionPolicy Bypass -File scripts/start-services.ps1
# 前置：Docker Desktop 已运行；敏感配置写在 scripts/env.local.ps1（已 gitignore）
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $PSScriptRoot 'env.local.ps1'
if (Test-Path -LiteralPath $envFile) { . $envFile }

$pyDir = Join-Path $root 'python\agent-runtime'
$py = Join-Path $pyDir 'hzt-agent-venv\Scripts\python.exe'
$logs = Join-Path $root 'logs'
$java = 'C:\Users\王可安然\.jdks\ms-17.0.19\bin\java.exe'

New-Item -ItemType Directory -Force -Path $logs | Out-Null
if (-not (Test-Path -LiteralPath $py)) { throw "未找到 Python 虚拟环境：$py" }
if (-not $env:DEEPSEEK_API_KEY) { Write-Warning '未检测到 DEEPSEEK_API_KEY，Agent Runtime 的 LLM 调用可能失败' }
if (-not $env:MYSQL_PASSWORD) { $env:MYSQL_PASSWORD = $env:TICKET_MYSQL_PASSWORD }
if (-not $env:JWT_SECRET) { $env:JWT_SECRET = 'huizhitong-dev-jwt-secret-change-me-2026' }
$env:PYTHONIOENCODING = 'utf-8'

function Test-Port($port) {
  return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}
function Start-Java($name, $jar, $port) {
  if (Test-Port $port) { Write-Host "$name 已在运行（端口 $port），跳过启动"; return }
  if (-not (Test-Path -LiteralPath $jar)) { throw "未找到 $name 构建产物：$jar" }
  $proc = Start-Process -FilePath $java -ArgumentList '-jar',$jar -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs ($name + '.out.log')) `
    -RedirectStandardError (Join-Path $logs ($name + '.err.log')) -PassThru
  Write-Host "$name 已启动（PID $($proc.Id)）"
}

Write-Host '==> 1/6 启动 RabbitMQ（Docker Compose）'
docker compose -f (Join-Path $root 'deploy\docker-compose.infra.yml') up -d rabbitmq
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
  $status = docker inspect -f '{{.State.Health.Status}}' huizhitong-rabbitmq-1 2>$null
  if ($status -eq 'healthy') { $healthy = $true; break }
  Start-Sleep -Seconds 2
}
if ($healthy) { Write-Host 'RabbitMQ 已就绪（huizhitong-rabbitmq-1）' }
else { Write-Warning 'RabbitMQ 未在 60 秒内就绪，审计将降级直写 MySQL' }

Write-Host '==> 2/6 启动 Agent Runtime（端口 8000）'
if (Test-Port 8000) {
  $listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
  Write-Host "Agent Runtime 已在运行（PID $($listener.OwningProcess)），跳过启动"
} else {
  $proc = Start-Process -FilePath $py -ArgumentList '-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8000' `
    -WorkingDirectory $pyDir -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'agent-runtime.out.log') `
    -RedirectStandardError (Join-Path $logs 'agent-runtime.err.log') -PassThru
  Write-Host "Agent Runtime 已启动（PID $($proc.Id)）"
}

Write-Host '==> 3/6 启动 Audit Worker'
$worker = Start-Process -FilePath $py -ArgumentList '-m','app.audit.worker' `
  -WorkingDirectory $pyDir -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $logs 'audit-worker.out.log') `
  -RedirectStandardError (Join-Path $logs 'audit-worker.err.log') -PassThru
Set-Content -LiteralPath (Join-Path $logs 'audit-worker.pid') -Value $worker.Id
Write-Host "Audit Worker 已启动（PID $($worker.Id)）"

Write-Host '==> 4/6 启动 Tool Service（端口 8083）'
Start-Java 'tool-service' (Join-Path $root 'java\huizhitong-tool-service\target\huizhitong-tool-service-0.1.0-SNAPSHOT.jar') 8083

Write-Host '==> 5/6 启动 Gateway（端口 8080）'
Start-Java 'gateway' (Join-Path $root 'java\huizhitong-gateway\target\huizhitong-gateway-0.1.0-SNAPSHOT.jar') 8080

Write-Host '==> 6/6 启动前端（端口 5173）'
if (Test-Port 5173) {
  Write-Host '前端已在运行（5173），跳过启动'
} else {
  $front = Start-Process -FilePath 'cmd.exe' -ArgumentList '/d','/c','npm run dev' `
    -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'frontend.out.log') `
    -RedirectStandardError (Join-Path $logs 'frontend.err.log') -PassThru
  Write-Host "前端已启动（PID $($front.Id)）"
}

Write-Host '全部完成。日志目录：' $logs
Write-Host '默认登录：admin / admin123（见 scripts/env.local.ps1 的 ADMIN_INIT_PASSWORD）'