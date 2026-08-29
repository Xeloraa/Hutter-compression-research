# Chain: when the forget=1 3MB pipeline (PID from arg or auto) finishes, run forget=0.
$ErrorActionPreference = "Continue"
$work = "C:\Users\vivi\hutter\work"
$gxxbin = "C:\Users\vivi\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin"
$env:PATH = "$gxxbin;" + $env:PATH
Set-Location $work

$fb1pid = 21196
Write-Host "waiting for fb1 shell pid $fb1pid"
while (Get-Process -Id $fb1pid -ErrorAction SilentlyContinue) {
  Start-Sleep -Seconds 20
}
Write-Host "fb1 process gone; checking log"
Get-Content "C:\Users\vivi\.cursor\projects\c-Users-vivi-hutter\terminals\573706.txt" -Tail 15

if (-not (Test-Path "$work\english.dic")) { Copy-Item "$work\english.dic" . }
Write-Host "=== cmp_fb0 compress 3MB DIC ==="
$t0 = Get-Date
& .\cmp_fb0.exe c C:\Users\vivi\hutter\data\enwik8.3m.dic C:\Users\vivi\hutter\work\runs\fb0.arc
$t1 = Get-Date
$arc = (Get-Item C:\Users\vivi\hutter\work\runs\fb0.arc).Length
Write-Host "FB0_ARCHIVE=$arc ctime_s=$(($t1-$t0).TotalSeconds)"
Write-Host "=== cmp_fb0 decompress ==="
$t0 = Get-Date
& .\cmp_fb0.exe d C:\Users\vivi\hutter\work\runs\fb0.arc C:\Users\vivi\hutter\work\runs\fb0.back
$t1 = Get-Date
Write-Host "FB0_DTIME=$(($t1-$t0).TotalSeconds)"
python -c "from pathlib import Path; a=Path(r'C:\Users\vivi\hutter\data\enwik8.3m.dic').read_bytes(); b=Path(r'C:\Users\vivi\hutter\work\runs\fb0.back').read_bytes(); print('FB0_CODEC', 'EXACT' if a==b else 'FAIL', 'len', len(a), len(b))"
