# 汇智通停止脚本：停掉 Agent Runtime（8000 端口）与 Audit Worker
$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $root 'logs'

$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    $pids = $listener | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Write-Host "已停止 Agent Runtime（PID $procId）"
    }
} else {
    Write-Host 'Agent Runtime 未在运行'
}

$pidFile = Join-Path $logs 'audit-worker.pid'
if (Test-Path -LiteralPath $pidFile) {
    $workerPid = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
    $alive = Get-Process -Id $workerPid -ErrorAction SilentlyContinue
    if ($alive) {
        Stop-Process -Id $workerPid -Force -ErrorAction SilentlyContinue
        Write-Host "已停止 Audit Worker（PID $workerPid）"
    } else {
        Write-Host 'Audit Worker 未在运行（PID 文件已过期）'
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
} else {
    Write-Host 'Audit Worker 未在运行'
}