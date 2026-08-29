# AGENT 7 — Novel / blue-sky

Baseline: fxcm26 + tree-head block-diagonal LSTM 92c/3L b=4 (LOCKED, +0.614% on 3 MB).
Not cmix-lex. Legal Hutter only: no extra corpus, no pretrained nets, 1 core, <10 GB, CPU-hour cap, byte-exact.
Do not run the 3 MB compressor from this note.

---

## The assumption that might be wrong

The programme has converged on a single story:

1. E12: words last seen >16k tokens cost 12.5 bits (20.8% of all bits); novel words cost 21.5 bits (17.3%). Halving CM RAM moved that bucket 0.20%. Therefore *distant cost is intrinsic rarity, not model amnesia. Long-range is dead.*
2. E14: oracle recalibration of fxcm is +0.136%. Therefore *only new information helps.*
3. E15–E29: every extra hashed context died (≤0.024%). An online *byte* LSTM mixed as two stretched probabilities is the only verified lever. Therefore *spend the remaining budget on a better byte-LSTM* (width, depth, blocks, init, forget bias).

(1) does not imply what everyone took it to imply.

E12 falsified **bigger hash tables**. A context map stores *local occurrence statistics keyed by a finite window*. Enlarging it cannot *name* a token from 16k steps ago in a new local window. That is not a proof that identity is unmodelable. It is a proof that **statistic-collecting finite contexts are the wrong inductive bias for identity** — the same class of result as E14 (mixing the same p) and E19 (bucketing lastCW the way fxcm already clusters word types).

Meanwhile the LSTM was wired as a *local byte-syntax* expert, so it cannot be the identity model either:

| wiring (`fxcm26_bd92.cpp` / `btl-bd.cpp`) | what that actually does |
|---|---|
| `Perceive(x.c0 & 0xff)` every DIC **byte** | alphabet is the prefix-code, not the word |
| `auxiliary_input_size = 0` (E22) | `lastCW` (0..44514), match bit, gap-to-last-same-word never enter the net |
| tree head → mixer slots **544/545 only**; 546–559 stay zero | 92×3 hidden state is discarded; mixer sees one bit-p |
| BPTT `horizon = 50` **bytes** | credit assignment of a few words; E12's expensive bucket is >16k tokens |
| homogeneous forget (E30: bias 0 beats +1) | a uniform net that wants *fast topic turnover* cannot also be a sticky name tag |

fxcm already has the near-misses that make this easy to overlook: `MatchModel2` copies when a *byte prefix* matches; `wp[word0 & 0xffff]` stores last position of a **colliding 16-bit letter-hash**, not `lastCW`. Rare-word identity is exactly what those collisions and prefix-mismatch destroy.

**69% of residual bits sit on dictionary codes (≥0x80) at 3.95 bits each (E11).** That is word *choice*, not XML, not calibration, not another order-N context. First occurrences really are entropy. **Reoccurrences of the same rare id in a dissimilar local window are not** — they are a pointer, which nobody has measured.

If that reading is right, scaling the byte-LSTM (including E30 forgetBias) is polishing the wrong object. The five ideas below are identity / long-range / cheaper-neural mechanisms that finite CMs and a 50-byte net structurally miss.

Killed on purpose (do not revive): ordinary extra CMs, page reorder (E10), dictionary-code buckets (E19), SSE/APM (E14), bigger softmax LSTM (E18/E21: output_size is the cost, softmax lost to the tree head).

---

## Idea 1 — Word-identity recency cache (pointer expert)  ★ BEST

**Mechanism.** At every completed `lastCW` (and every completed OOV fingerprint, idea 4), push `(pos, id, h_t)` onto a ring of K ∈ [4k, 64k] word steps. Predict the *next* dict-code bits by mixing fxcm+LSTM with a cache expert:

- **Exact (cheap, do this first):** `p_cache` = recency distribution over ids in the ring (count or exponential decay). Factor onto bits of the current code prefix the same way the tree head factors a byte (`c0`).
- **Neural (if exact lives):** Grave-style `p_cache(w) ∝ Σ_i exp(θ h_t · h_i) 1[id_i = w]` using hidden states stored *only at word boundaries* (32k × 277 floats ≈ 35 MB, legal).

This is not a new hashed CM and not E19's `lastCW >> 6` clusters. It *names* the token. It is not MatchModel2: match requires a matching *byte context*; a rare entity in a new sentence has a different prefix. It is not `wp[word0&0xffff]`: that aliases 44k ids into 64k colliding slots and then bins the gap at 255.

**Why it could move >0.2%.** E12's distant bucket is 20.8% of bits at 12.5 vs 3.75 bits at gap 64–256. That 8.75-bit hole is *exactly* "I have seen this id before, not in the current finite window." Closing 5% of that hole is ~0.2% of S; closing 15% is ~0.6%. Memory doubling did not touch it (E12 control) because there was no pointer to enlarge. Cache RAM is tens of MB, not a second copy of fxcm's maps.

**Cheapest falsifying test (no 3 MB compressor).**

Dump the causal `lastCW` stream from a 2–10 MB DIC prefix (fxcm already decodes it; a 50-line scanner over DIC bytes ≥0x80 is enough). For K ∈ {64, 256, 1k, 4k, 16k, 64k} and for an **unbounded oracle** (γ-code the true gap to previous occurrence of this id, else escape + log2(V)):

1. Bits/token of pointer-vs-escape vs a unigram on the same stream.
2. Split by previous-gap and by id-frequency (1, 2–5, 6–20, rest).
3. Convert to % of *file* bits using E11's 69% dict-code share (or a one-pass bit-attribution if a `-cost` dump exists).

**Kill if** the unbounded oracle saves <0.4% of file bits on second+ occurrences — then reoccurrence identity is not the residual (E12's "intrinsic rarity" was right after all). **Also kill if** ≥80% of the oracle's saving is already present at K≤64 — then `worcxt.Word(1..6)` already owns it and the cache is a duplicate. Survive if the oracle is large *and* the mass sits at K ≥ 1k (ideally ≥16k). Only then wire a 2-slot mixer expert.

---

## Idea 2 — Word-step LSTM (stop burning BPTT on cheap bytes)

**Mechanism.** `Perceive()` once per completed word (`lastCW` or OOV string), not once per DIC byte. Intra-code bits still use the tree head against a *held* hidden state (or fxcm alone until the word completes). Input is the completed id, not `c0&0xff`.

Effective horizon 50 *words* is several times the current 50 *bytes*, at *fewer* Forward/Backward passes. DIC is ~1.81 MB per 3 MB raw; dict codes are 40% of those bytes but far fewer *tokens*. XML/space/punctuation that E11 prices at 0.07–0.75 bpb currently consume full 3-layer BPTT.

This is cheaper neural capacity, not a bigger softmax: the tree head stays; the recurrent core runs less often. The 120c/3L b=4 point that was +0.716% / 53.9 h (OVER) becomes plausible inside 42.48 h, *and* the net finally lives at the timescale of word identity.

**Why >0.2%.** Width alone 92c→120c was +0.10% but illegal on time. Word-stepping should cut LSTM MACs by ~2–3× if word rate is in that range; that pays for 120c *plus* longer credit assignment on the 69% dict-code bits. Those two are independent of mixer recalibration (E14).

**Cheapest falsifying test.**

On 400 KB DIC, standalone (the E27/E30 harness — not the 3 MB pipeline):

1. Count ForwardPass calls: byte-step vs word-step. **Kill the budget claim if word-step is not ≥2× fewer passes.**
2. Word-level 16-bit tree LSTM on the `lastCW` sequence vs bits the byte-LSTM actually spent on bytes ≥0x80 (same file). **Kill if word-LSTM is not ≥0.3 bits/word better on those tokens.** If it is worse, the byte net is already doing the word LM and stepping less only throws away intra-code signal.

---

## Idea 3 — Narrow aux: give the LSTM `lastCW` and the gap (it is currently blind)

**Mechanism.** E22 deleted a 256-wide aux block of zeros and won 3.9× speed. The *cmix* LSTM was designed to `SetInput` from other models; this integration never did. Restore a **16–32 dim** aux, not 256:

- 16 bits of the just-completed `lastCW` (unique over 44515 ids — this is identity, not E19's `>>6` buckets).
- `log2(pos - lastpos[lastCW])` from a 44515-int table (the E12 feature, causal, ~174 KB).
- 1 bit: in-dict vs OOV-spell; 1 bit: MatchModel2 active.

Cost: 32 extra MACs per cell per gate vs the 256 zeros that used to dominate. Legal, zero shipped bytes, byte-exact if the table is causal.

This does not predict the *current* code (id is only known at the end); it conditions the net for the *next* word — i.e. turns the byte-LSTM into a word-LM without changing the alphabet. Combined with idea 2 it is the same object; alone it is a one-afternoon patch on `ForwardPass` aux.

**Why >0.2%.** E14: new information only. `lastCW` is information the net does not have. The byte prefix-code is a lossy, variable-length view of the same id; a 50-byte BPTT window does not have to parse it if you hand it over. Decorrelated from fxcm because fxcm already *uses* `lastCW` in exact compares (`cwHTTP`, …) and whole hashes, but the LSTM's mixer input is only p(bit).

**Cheapest falsifying test.**

Offline 2-input vs 4-input logistic mixer on a recorded `(p_fxcm, y)` stream from any existing 200–400 KB run (E15 harness; ranking only):

- extra features: `lastCW & 255`, `log2(gap[lastCW])`.
- report gain **restricted to dict-code bits**.

**Kill if** the extra features add ≲0.02% offline on that subset (either fxcm already swallowed the gap, or the residual is not identity). **Kill if** a linear probe can decode `lastCW` from the current LSTM hidden at word boundaries — then the net already has the id and aux is duplicate (go to idea 1 / 2 instead).

Do not treat a small offline % as a magnitude; E16 showed ~6× understatement. Use it only as a dead/alive gate.

---

## Idea 4 — Causal OOV copy (the E2 dictionary, but free and online)

**Mechanism.** E2 died because a *shipped* title vocabulary costs more than spelling, and 81% of link targets were hapax at that scale. That does not kill **copying an OOV string that already appeared in the decoded prefix**.

Maintain a causal map `hash(literal word) → last pos` for words not in `english.dic` (the scanner is the same as `Dictionary::EncodeWord`'s miss path). First occurrence: spell as now. Later occurrence: pointer (γ-coded gap or index into a recent-OOV ring) then resume. Zero side data: decoder has seen the same bytes.

Distinct from MatchModel2 (different preceding markup/sentence → no byte match). Distinct from E2 (nothing shipped; table cardinality = OOV types *seen so far*, not the title list). Distinct from E19 (not clustering in-dict codes).

**Why >0.2%.** E12's 17.3% of bits @ 21.5 bits are "novel" *in the CM's window / first-spell sense*. Wikipedia repeats proper names, titles, and infobox tokens inside and across nearby pages. If even a quarter of that bucket is second+ spellings, a pointer that replaces ~21 bits with ~8–12 is on the order of 0.2–0.5% of S. First-in-file hapaxes remain expensive; that is fine.

**Cheapest falsifying test.**

Scan a 10–30 MB enwik prefix through the real DIC encoder. Partition spelled-out tokens (not in `english.dic`, not a substring-code hit). Information budget:

`bits = spell(first) + Σ_{k≥2} γ(gap_k)` vs `bits = spell(every occurrence)`.

**Kill if** savings <0.4% of *raw file* bits (leave room for mixer overlap and for DIC already folding some substrings). **Kill if** almost all repeats have gap ≤32 bytes — MatchModel2 already copies those runs. Survive if savings are large *and* gaps are sentence/paragraph/article scale.

---

## Idea 5 — Two timescales: sticky identity block + skip-BPTT on easy bytes

**Mechanism.** E30: smaller forget bias is strictly better. The write-up said "Wikipedia topic shifts want faster state turnover." That is true of a **homogeneous** net. It does not imply nothing should persist. A uniform forget=0 throws away the 20.8% distant-identity bucket on purpose.

Use the block-diagonal split that already exists (`g_blocks = 4`):

- blocks 0–2: forgetBias = 0 (E30 winner, local syntax).
- block 3: forgetBias ≈ +2 to +4, maybe slower lr — *identity cells*. Mask already prevents them from being averaged away by the fast blocks.

Plus **skip BPTT on low-entropy bytes** (XML, space, fxcm |p−y| small): still `Advance()` so state tracks the stream; only `BackwardPass` on dict-code and OOV-spell bytes (the 69% + 17% bits). Forward is cheaper than backward; this is the remaining cost lever after E18 (fused loops did nothing) and E21 (tree head already cut output_size).

Not a bigger softmax. Not SSE. Heterogeneous inductive bias inside the net you already pay for.

**Why >0.2%.** Skip-BPTT is a budget play: 120c was +0.102% vs 92c and 11 h over cap. A 25–40% LSTM-time cut puts that point (or 100c with margin) in bounds. The sticky block is the quality play on E12's tail; E30 never tested *split* bias, only a global one. Together they can clear 0.2%; either alone might not.

**Cheapest falsifying test.**

Standalone 72c/3L b=4, 400 KB DIC (E30c harness):

1. **Split bias:** block 3 forgetBias ∈ {1, 2, 4}, blocks 0–2 at 0, vs all-0 and vs all-1. **Kill the sticky-block claim if split is not ≥0.02 bpb better than all-0.** If split ≈ all-1, E30's homogeneous conclusion stands.
2. **Skip-BPTT:** backward only when byte ≥0x80 vs always. **Kill if** bpb regresses >0.02 **or** us/byte drops <25% (no budget to give back). Ranking only; do not project Hutter-hours from standalone (E28: five consecutive underestimates).

---

## Ranking

| rank | idea | status | cheapest kill |
|---|---|---|---|
| 1 | Causal OOV copy, **len>=6 after DIC** | **live ceiling** 0.693% DIC-file vs spelling after LEN=5 | 3 MB mixer expert only if leftover stays after E30/E35 |
| 2 | Word-step LSTM | 50-byte horizon | pass-count + bits/word vs byte-LSTM |
| 3 | Narrow aux (`lastCW` + gap) | net never sees the id | G2 after E35; kill if zero-aux control matches |
| 4 | Word-identity lastCW cache | **KILLED** (gamma and LRU-index) | rare cnt2-5 = 0.18% of raw file vs unigram |
| 5 | Sticky block + skip-BPTT | E30 over-generalised forget | split-bias standalone after E30 |

Idea 1 died as lastCW. Idea 4 (OOV) is the remaining identity residual. Idea 3 is not lastCW-as-pointer; it is G2 residual aux.

---

## Return (single best)

**Causal OOV copy on DIC-stream letter-runs of length >=6**, mixed as a bit expert, not lastCW.

lastCW gamma and LRU-index both failed the rare-identity test (`IDENTITY.md`). The leftover is spelled names after DIC whose LEN=5 prefix does not match (`OOV.md`): ~12.6 KB ceiling vs 8-bit spelling.

**Falsify in-pipeline:** one mixer expert on those tokens after E30/E35. Kill if archive delta <100 B vs the same-compiler control.
