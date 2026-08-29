# Reversible OOV pointer prototype

input=1814514 MARK=0x05 already_present=0 min_len=6
unbounded enc=1800107 delta=14407 copies=2488 first=6957 roundtrip=EXACT
K=256 enc=1800762 delta=13752 copies=2335 first=7110 roundtrip=EXACT
K=1024 enc=1800560 delta=13954 copies=2385 first=7060 roundtrip=EXACT
K=4096 enc=1800245 delta=14269 copies=2456 first=6989 roundtrip=EXACT

Best exact transform: unbounded saves 14407 bytes of DIC input (0.794%).

C++ `work/agent7/oovptr.cpp` matches: 1814514 -> 1800107, decode EXACT.

This is not an fxcm archive. After E30d/e, run same-compiler `cmp` on the pointer stream vs vanilla DIC. Kill if archive gain <100 B. Do not overwrite `locked/`.

