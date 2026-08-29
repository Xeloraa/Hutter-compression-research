# Compile AFTER cmp_fb1/fb0 finish. Do not steal the core.
# E35 only: L2 LSTM skip, no E32 slot fill, forgetBias=1 (lstm_forget1.cpp).
$env:PATH = "C:\Users\vivi\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin;" + $env:PATH
$src = "C:\Users\vivi\hutter\work\src"
$obj = "C:\Users\vivi\hutter\work\obj"
$out = "C:\Users\vivi\hutter\work"
New-Item -ItemType Directory -Force -Path $obj | Out-Null
g++ -O3 -march=native -ffast-math -fno-strict-aliasing -std=c++11 -c -o "$obj\fxcm_e35.o" "$src\fxcm26_slots.cpp" -I $src "-DLSTM_L2_INPUT=1" "-DFILL_SLOTS_546=0"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
g++ -O3 -march=native -ffast-math -fno-strict-aliasing -std=c++11 -c -o "$obj\btl_e35.o" "$src\btl-bd.cpp" -I $src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
g++ -O3 -march=native -ffast-math -fno-strict-aliasing -std=c++11 -c -o "$obj\sig.o" "$src\sigmoid.cpp" -I $src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
g++ -O3 -march=native -o "$out\cmp_e35.exe" "$obj\fxcm_e35.o" "$obj\btl_e35.o" "$src\lstm_forget1.cpp" "$obj\sig.o" -I $src
Write-Host "cmp_e35.exe exit $LASTEXITCODE"
