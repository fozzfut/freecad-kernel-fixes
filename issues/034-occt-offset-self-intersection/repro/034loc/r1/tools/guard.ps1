# guard.ps1 -Exe -Args -Path -Out -Sec -MB : run one process with PATH prefix, kill at Sec seconds or MB working set; prints peak
param([string]$Exe, [string]$ArgLine, [string]$PathPrefix, [string]$Out, [int]$Sec = 240, [int]$MB = 1000)
$env:PATH = "$PathPrefix;$env:PATH"
$p = Start-Process -FilePath $Exe -ArgumentList $ArgLine -RedirectStandardOutput $Out -NoNewWindow -PassThru
if (-not $p) { "GUARD start-failed"; exit 1 }
$peak = 0; $sw = [Diagnostics.Stopwatch]::StartNew(); $why = "exit"
while (-not $p.HasExited) {
  Start-Sleep -Milliseconds 1000
  try { $p.Refresh(); $ws = [int]($p.WorkingSet64 / 1MB); if ($ws -gt $peak) { $peak = $ws } } catch {}
  if ($peak -gt $MB) { $why = "mem"; Stop-Process -Id $p.Id -Force; break }
  if ($sw.Elapsed.TotalSeconds -gt $Sec) { $why = "time"; Stop-Process -Id $p.Id -Force; break }
}
"GUARD pid=$($p.Id) end=$why sec=$([int]$sw.Elapsed.TotalSeconds) peakMB=$peak"
