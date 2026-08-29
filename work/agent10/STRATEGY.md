# Campaign strategy (reset 2026-08-29)

**Win condition:** verified **S = compressor + archive9 on enwik9** under official rules that beats the paid record (today **110,793,128**) and then the moving 1% gate.

**Not the win condition:** any 3 MB DIC→fxcm26 number, including 517,996.

## Classification

- **A** — could remove megabytes on enwik9 or unlock a new mechanism of that weight.
- **B** — cheap test that characterizes or kills an A idea.
- **C** — local micro-opt. Run only if it credibly feeds A.

## 3 MB forget-bias series — STOPPED

- E30d forget=1 MinGW: archive **518,095**, compress 2122 s, decompress 1610 s, codec **EXACT**. Class **C**. Not comparable to Linux lock 517,996.
- E30e forget=0 MinGW: archive **517,905**, compress 886 s, decompress 817 s, codec **EXACT**. **−190 B** vs same-compiler E30d (passes the old ≥100 B MinGW gate). Still Class **C**. Do not replace `locked/`. Do not start E32/E35/E41.

## Killed this turn

**E41 OOV pointer** is Class **C**: exact −14,407 DIC bytes, but zlib9 **loses 1,702** and lzma6 **loses 1,092** vs vanilla DIC. A transform generic compressors reject will not move enwik9 S by megabytes. Do not start `tools/run_e41_oovptr.ps1`.

**3 MB exact duplicates** (Class B for A4): extra page-body copies **0.037%** of file; extra long-line copies **0.643%**. Wrong scale for identity. Measure PHDA9 tail at enwik9, not stubs.

## Work now

**A2 cheap filter + PHDA9-lite scale (E43/E44) are done.** Second-lex analogs die; lang/r2 lzma is **sublinear** 30→100 MB; a 20–30 MB cmix A/B is underpowered for A2. Leftover A2 hole is a Linux **post-WRT tail autopsy only**. The 10–30 MB full-stack A/B is **A1** (tree head + `SetInput` in cmix-lex). See `A2.md` and `INTEGRATION.md`.

Do not start E32, E35, E36, width sweeps, or E41 3 MB fxcm.
