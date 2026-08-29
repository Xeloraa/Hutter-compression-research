# Run after the 3MB pipeline is using only one core, or after it finishes.
$env:PATH = "C:\Users\vivi\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin;" + $env:PATH
$exe = "C:\Users\vivi\hutter\tools\lstm_stand.exe"
$adam = "C:\Users\vivi\hutter\tools\lstm_stand_adam.exe"
$in = "C:\Users\vivi\hutter\data\dic200k.bin"
$log = "C:\Users\vivi\hutter\log\e31_standalone.txt"
Write-Host "=== E31 Adam tree head vs SGD, 72c/3L fb=0 ==="
& $exe $in 200000 72 3 4 0.5 0.0 0.03 50 | Tee-Object -FilePath $log -Append
& $adam $in 200000 72 3 4 0.5 0.0 0.03 50 | Tee-Object -FilePath $log -Append
Write-Host "=== E33 lr sweep 72c fb=0 ==="
foreach ($lr in @("0.010","0.020","0.050","0.080")) {
  Write-Host "lr=$lr"
  & $exe $in 200000 72 3 4 0.5 0.0 $lr 50 | Tee-Object -FilePath $log -Append
}
Write-Host "=== E34 depth 64x4 vs 56x4 vs 72c3 ==="
& $exe $in 200000 64 4 4 0.5 0.0 0.03 50 | Tee-Object -FilePath $log -Append
& $exe $in 200000 56 4 4 0.5 0.0 0.03 50 | Tee-Object -FilePath $log -Append
Write-Host "=== standalone batch done ==="
