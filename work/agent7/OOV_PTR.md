# Reversible OOV pointer prototype

input=1814514 MARK=0x05 already_present=0 min_len=6
unbounded enc=1800107 delta=14407 copies=2488 first=6957 roundtrip=EXACT
K=256 enc=1800762 delta=13752 copies=2335 first=7110 roundtrip=EXACT
K=1024 enc=1800560 delta=13954 copies=2385 first=7060 roundtrip=EXACT
K=4096 enc=1800245 delta=14269 copies=2456 first=6989 roundtrip=EXACT

Best exact transform: unbounded saves 14407 bytes of DIC input (0.794%).

C++ `work/agent7/oovptr.cpp` matches: 1814514 -> 1800107, decode EXACT.

**KILLED as a pipeline (Class C).** zlib9 911223→912925 (−1702 vs vanilla). lzma6 752544→753636 (−1092). Generic compressors lose; do not run 3 MB fxcm. `tools/run_e41_oovptr.ps1` stays unused.

