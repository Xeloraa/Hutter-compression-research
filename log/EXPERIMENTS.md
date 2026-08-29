# Hutter experiment queue

Incumbent: 517,996 bytes (92c/3L/b=4/initMul=0.5) LOCKED

| id | hypothesis | dataset | config | archive | vs 517996 | runtime | exact | status |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| E30 | forgetBias=0 (standalone) | 200KB DIC | 72c/3L | n/a (bpb 3.086 vs 3.134) | n/a | ~41s | standalone only |
| E30b | forgetBias=0 at 92c | 200KB DIC | 92c/3L | n/a (3.060 vs 3.105) | n/a | ~67s | standalone only |
| E30c | forgetBias=0 at 400KB | 400KB DIC | 92c/3L | n/a (2.947 vs 2.977) | n/a | ~200s | standalone only |
| E30d | forgetBias=1 control | 3MB DIC pipeline | 92c/3L MinGW | 518095 compress | n/a (MinGW ≠ lock) | 2121 s compress | decompress RUNNING |
| E30e | forgetBias=0 pipeline | 3MB DIC pipeline | 92c/3L MinGW | queued | | | queued |
| E31 | tree-head Adam | 200KB DIC | 72c/3L fb=0 | | | | coded, not run |
| E32 | fill mixer slots 546-549 | 3MB pipeline | 92c + extras | | | | coded in fxcm26_slots.cpp |
| E33 | LSTM lr sweep with fb=0 | 200KB DIC | 72c | | | | queued |
| E35 | L2 mixer input stretch(bp)/2 | 3MB pipeline | fx2-cmix replica | | | | coded `-DLSTM_L2_INPUT=1` |
| E36a | mxA1[1] cxt = ExpectedByte | 3MB pipeline | M=256 | | | | coded `-DLSTM_MEX_CXT=1` |
| E36b | bpos+fails+lstmex cxt | 3MB pipeline | M=8192 | | | | coded `-DLSTM_MEX_CXT=2` |
| E37 | lastCW γ-gap identity cache | 3MB DIC lastCW stream | mixed vs unigram | n/a | n/a | n/a | KILLED (frequent-word overlap; rare+far γ never wins) |
| E38 | causal OOV copy vs spelling | enwik8.3m raw | gamma gap | n/a | n/a | n/a | raw ceiling; 3-byte overlap test overstated MatchModel2 |
| E38b | DIC-stream OOV + LEN=5 overlap | enwik8.3m.dic | a-z runs not in dic | n/a | n/a | n/a | PROMISING ceiling: len>=6 leftover 0.693% DIC-file after any-prior LEN=5 |
| E39 | lastCW LRU-index recode | lastCW stream | 1+log2(K) vs unigram | n/a | n/a | n/a | KILLED (rare cnt2-5 = 0.18% of raw file; mass still frequent words) |
| E40 | O2 first-template byte mass | enwik8.3m pages | no fxcm | n/a | n/a | n/a | unmodified O2 KILLED (hatnotes 30.5%); schema-only leftover |
