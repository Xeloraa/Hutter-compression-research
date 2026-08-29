# E30e MinGW — not a lock replacement

ForgetBias=0, 92c/3L/b=4, WinLibs MinGW, DIC→fxcm26 on `enwik8.3m.dic`.

| | |
|---|---|
| archive | **517,905** |
| vs same-compiler fb=1 | 518,095 − **190 B** |
| vs Linux lock 517,996 | **not comparable** (different `srand`/libstdc++) |
| roundtrip | EXACT (1814514 bytes) |
| ctime / dtime | 886 s / 817 s |

Do not copy into `locked/`. Promote only after Linux `locked/BUILD.sh` with
`FORGET_BIAS=0` beats **517,996 by ≥100 B** and VERIFY.sh is EXACT.

This machine has no WSL and Docker Desktop is not running.
