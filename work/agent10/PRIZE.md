# Two scoreboards (do not mix them)

Verified 2026-08-29 from http://prize.hutter1.net/

## External frontier (what “win” means)

| | |
|---|---|
| Official record S | **110,793,128** (fx2-cmix, Orav & Knoll, 3 Sep 2024) |
| S = S1 + S2 | S1 compressor 441,463 + S2 archive9 110,351,665 |
| Next prize gate | **S < 109,685,197** (1% vs current L) |
| Constraints | 1 core, ≲50 h on the judging machine, <10 GB RAM, <100 GB disk, lossless enwik9 |

LTCB lists **cmix-lex ~109.19M** (fxcm_v26 inside cmix + shipped article order + lex tail). That is **not** the paid prize record until the committee accepts it. Treat it as a competing full-scale stack, not as our 3 MB number.

## Internal floor (what a 3 MB experiment must beat)

| | |
|---|---|
| Slice | first 3,000,000 bytes of enwik8 → DIC → fxcm26 |
| Locked archive | **517,996** (92c/3L/b=4/initMul=0.5) |
| fxcm-only baseline | 521,198 |
| MD5 | `a52a41bd426904afcc48d1b9a99c8f1d` |

A 10% cut of 517,996 is ~466 KB on this **slice**, not on enwik9. Do not scale 3 MB percents to S.

## The missing mass (why fxcm+LSTM alone cannot take the prize)

fx2-cmix **replaced paq8hp with fxcm** and kept cmix’s PPMD, match, indirect, word, LSTM-as-byte-mixer, SSE, and a **shipped** article permutation. This campaign’s compressor is **fxcm26 + a tree-head LSTM only**. That is the donor’s *one* expert, not the ensemble that holds the record.

Exploit on 92c/forget/mixer slots can move hundreds of bytes on 3 MB. The prize-scale gap is **megabytes on enwik9**, which is the rest of that ensemble (and/or a new mechanism of similar weight).

### Explore track that could actually compete

1. **A1:** replace only the 256-softmax LSTM **head** inside cmix-lex, keep `SetInput` / PPMD / fxcm_v26 / article order. Freeze **170c/1L/h=128**. Spec: `A1_PATCH.md`. Do not drop in our aux=0 92c/3L net.
2. **Paid semantic order** only if compressed permutation + archive gain beats 215 KB (STARLIT tax). Free title order is dead in DIC+fxcm (E10).
3. **Identity/OOV copy** only if an oracle beats fxcm’s match+word models on *rare* tokens (γ-gap vs unigram already died; see `work/agent7/IDENTITY.md`).

### Exploit track (3 MB)

E30d recorded (MinGW 518095 EXACT). E30e **517905 EXACT** (886 s / 817 s, −190 B vs E30d MinGW). Forget-bias series **STOPPED**. Class C. A2 and A3 cheap filters killed as megabyte (`A2.md`, `A3.md`). A1 spec is `A1_PATCH.md`. Do not start E35/E32/E41. Do not replace `locked/`.
