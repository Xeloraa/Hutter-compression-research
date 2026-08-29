# Next 3 experiments (Agent 8)

Incumbent: 517,996 (fxcm26 + tree-head BD-LSTM 92c/3L/b=4/initMul=0.5). Headroom ~3.9 h. Only LSTM has ever moved the real-regime needle. Do **not** refill mixer slots with copies of existing predictions (killed). E30 forgetBias=0 is already queued — these three are the next **prior-art** bets.

## 1. P1 — LSTM aux from match `expectedByte` (tiny `SetInput`)

cmix’s LSTM is a **byte mixer with auxiliary inputs**. This fork zeroed aux (E22) so the LSTM is a blind byte model. Restore **width 2–4**, not 256: match expected bit, log-length, delta flag.

- **Falsify:** 400 KB standalone aux=0 vs aux=4 from a toy matcher; then 3 MB live `matchCandidates[best]`. Kill at ≤ +0.02%.
- **Cost:** should stay well under the 3.9 h margin if aux stays tiny.
- **Legal:** clean (online weights).

## 2. P2 — LSTM expected-byte as **mixer context**; delete monotone slot 545

fx2-cmix uses LSTM **expected byte as a mixer context**. Locked `n[545] = stretch((bp+2048)>>1)` is a copy of `n[544]` (killed class). Replace with `mxA[].cxt` keyed by LSTM argmax (or its current bit) × `c0`.

- **Falsify:** 3 MB (a) drop 545, (b) add expected-byte context. Kill if both ≤ ~20 B.
- **Cost:** ~0 CPU.
- **Legal:** clean.

## 3. P3 — Paid **semantic** page order vs E10 title-lex (10 MB proxy)

E10 killed **free title order** (−0.006%), not Voyage/STARLIT topic order. Inverse is still free (`<id>` sort). Pay S1 only if archive savings beat ~150–220 KB.

- **Falsify:** 10 MB original vs title vs STARLIT/`nao` (or minhash greedy). DIC+fxcm. Kill if semantic ≤ original or savings < xz(permutation).
- **Cost:** 0 codec CPU; preprocess only.
- **Legal:** shipping a permutation is accepted (STARLIT/fx2). Do **not** put embedding weights in the decompressor or hit the network.

If P3 dies like E10, the free **category-key** order (P8) is the leftover ordering test — still not title-lex.
