# E41 — run AFTER cmp_fb1/fb0 are gone. Do not steal the 3MB core.
# Usage: run_e41_oovptr.ps1 [cmp_fb1.exe|cmp_fb0.exe]
$ErrorActionPreference = "Stop"
$gxx = "C:\Users\vivi\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin"
$env:PATH = "$gxx;" + $env:PATH
$root = "C:\Users\vivi\hutter"
$work = "$root\work"
if (Get-Process cmp_fb1,cmp_fb0 -ErrorAction SilentlyContinue) {
  Write-Host "cmp still running; refuse E41"
  exit 2
}
$cmpName = if ($args.Count -ge 1) { $args[0] } else { "cmp_fb1.exe" }
$cmp = Join-Path $work $cmpName
if (-not (Test-Path $cmp)) { Write-Host "missing $cmp"; exit 1 }
$env:OOVPTR_DIC = "$work\english.dic"
if (-not (Test-Path "$work\agent7\oovptr.exe")) {
  g++ -O2 -std=c++11 -o "$work\agent7\oovptr.exe" "$work\agent7\oovptr.cpp"
}
& "$work\agent7\oovptr.exe" e "$root\data\enwik8.3m.dic" "$work\runs\enwik8.3m.dic.oovptr"
Set-Location $work
Write-Host "E41 compress with $cmp"
& $cmp c "$work\runs\enwik8.3m.dic.oovptr" "$work\runs\e41.arc"
Write-Host "E41_ARCHIVE=$((Get-Item $work\runs\e41.arc).Length)"
& $cmp d "$work\runs\e41.arc" "$work\runs\e41.ptr.back"
& "$work\agent7\oovptr.exe" d "$work\runs\e41.ptr.back" "$work\runs\e41.dic.back"
python -c "from pathlib import Path; a=Path(r'$root\data\enwik8.3m.dic').read_bytes(); b=Path(r'$work\runs\e41.dic.back').read_bytes(); print('E41_DIC', 'EXACT' if a==b else 'FAIL')"
