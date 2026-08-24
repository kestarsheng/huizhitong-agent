$log = 'D:\projects\huizhitong-agent\deploy\pull-progress.log'
function Log($m){ Add-Content -LiteralPath $log -Value ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m) }
function Pull-WithTimeout($src){
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = 'docker'
  $psi.Arguments = 'pull ' + $src
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $p = [System.Diagnostics.Process]::Start($psi)
  if(-not $p.WaitForExit(300000)){
    try { $p.Kill() } catch {}
    $p.WaitForExit()
    return $false
  }
  return ($p.ExitCode -eq 0)
}
$images = @(
  @{ src='docker.1ms.run/library/nginx:1.27-alpine';  tag='nginx:1.27-alpine' },
  @{ src='docker.1ms.run/library/eclipse-temurin:17-jre'; tag='eclipse-temurin:17-jre' },
  @{ src='docker.1ms.run/library/mysql:8.0'; tag='mysql:8.0' }
)
Log '===== PULL SCRIPT V2 START ====='
foreach($img in $images){
  $got = (docker images --format "{{.Repository}}:{{.Tag}}") | Where-Object { $_ -eq $img.tag }
  if($got){ Log ("ALREADY_LOCAL " + $img.tag); continue }
  $ok = $false
  for($i=1; $i -le 30; $i++){
    $src = if($i % 2 -eq 1){ $img.src } else { $img.src.Replace('docker.1ms.run','docker.1panel.live') }
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $okTry = Pull-WithTimeout $src
    $sw.Stop()
    if($okTry){
      docker tag $src $img.tag
      Log ("DONE tag {0} ({1}s, try {2})" -f $img.tag, [int]$sw.Elapsed.TotalSeconds, $i)
      $ok = $true
      break
    } else {
      Log ("FAIL try {0} {1} after {2}s" -f $i, $src, [int]$sw.Elapsed.TotalSeconds)
      Start-Sleep -Seconds 20
    }
  }
  if(-not $ok){ Log ("GIVEUP " + $img.tag) }
}
Log '===== PULL SCRIPT V2 DONE ====='