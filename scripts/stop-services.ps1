# 汇智通停止脚本：停掉 Agent Runtime、Audit Worker、Tool Service、Gateway、前端
$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $root 'logs'

function Stop-Port($port, $name) {
  $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if ($listener) {
    $pids = $listener | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      Write-Host "已停止 $name（PID $procId）"
    }
  } else {
    Write-Host "$name 未在运行"
  }
}

Stop-Port 8000 'Agent Runtime'
Stop-Port 8083 'Tool Service'
Stop-Port 8080 'Gateway'
Stop-Port 5173 '前端'

$pidFile = Join-Path $logs 'audit-worker.pid'
if (Test-Path -LiteralPath $pidFile) {
  $workerPid = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
  $alive = Get-Process -Id $workerPid -ErrorAction SilentlyContinue
  if ($alive) {
    Stop-Process -Id $workerPid -Force -ErrorAction SilentlyContinue
    Write-Host "已停止 Audit Worker（PID $workerPid）"
  }
  Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
} else {
  Write-Host 'Audit Worker 未在运行'
}