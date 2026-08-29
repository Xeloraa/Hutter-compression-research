# Ordering after E10 — what can still be true

Status: **one idea still has a distinct mechanism; two are bookkeeping/constraints, not bit sources.** Title-lexicographic order is not revived. Nothing here is a claimed archive gain.

E3 (testbed, 10 MB): free title-lex **+0.479%**, greedy minhash of full content **+0.319%** and paid 2,168 B xz. Inverse permutation is free because `<id>` is strictly ascending in the dump (re-checked on this slice: 384/384 complete pages in `enwik8.3m`, ids 1…840).

E10 (DIC + fxcm26, 10 MB / 1,325 pages): title-lex **−0.006%** (1,672,492 → 1,672,597). Trajectory: testbed +0.479% → fxcm PLAINTEXT +0.075% → DIC+fxcm26 −0.006%. Log: “DIC's word dictionary already captures cross-article redundancy.”

STARLIT still ships `new_article_order`: 173,361 entries, **215,748 B** delta+xz (raw 1,131,233 B; arbitrary-perm entropy floor ~346 KB). That is **0.14–0.26% of S**, paid every submission, for a Doc2Vec+TSP order that is *not* title-lex and was **never measured in the DIC+fxcm26 regime**. E10 killed a different permutation.

Do not re-run title-lex. Do not run 3 MB fxcm for these probes.

## Why anything could still work after DIC, given that title-sort failed

Title-lex groups pages whose *names* share prefixes. That is a proxy for shared **English vocabulary**. After `english.dic`, those words are already global short codes (E11: dict codes ≥0x80 are 40% of DIC bytes and **69% of bits**). Adjacent “Anarchism / Anarchy” pages do not make `the`/`of`/`philosophy` cheaper. E10 is that proxy dying.

Three things DIC does **not** fold the same way:

1. **Dump-order locality among long articles.** Early Wikipedia ids are creation/batch order (Conversion-script CamelCase redirects, country-stub bursts). Title-lex *destroys* those runs (this slice: 7.6% of original adjacencies kept). If the leftover bits are rare OOV strings and markup, the dump's existing clumps can already be the right prior. E10 going slightly negative is consistent with “shuffle hurt more than title-similarity helped.”
2. **Page-schema / template n-grams.** E11 still spends **5.6% of bits @ 1.420 bpb** on templates. `{{Taxobox` / `{{Infobox_country` pages share parameter order and table syntax, not title prefixes (`Canis lupus` vs `Escherichia coli`). That is a different key than E10.
3. **STARLIT's 215 KB tax.** A free reconstructible order (identity, or a derived key) deletes that file. Even a *zero* archive-side ordering gain is **+215,748 B on S** if STARLIT's order is dropped. That accounting is independent of E10's −0.006%.

What does **not** survive as a rationale: “put similar titles together so the CM reuses words.” That is E10. Title-token clustering on this slice raises adjacent title overlap and does **not** raise body OOV overlap — same failure mode, measured without a codec.

Inverse is free for every encoder-side page permutation: decode, then sort pages by in-band `<id>`. Ship a permutation only if the decoder cannot see pages before emitting original order, or if you are compressing a *deviation* from a prior. STARLIT chose the latter poorly (full-ish perm, 215 KB) even though the file is block-preserving.

## Cheapest test (no fxcm)

On `data/enwik8.3m` (3,000,000 B prefix; last page dropped if truncated):

1. Split complete `<page>…</page>`. Record title, id, class (redirect / disambig / list / infobox / article), `#REDIRECT [[target]]`, first `{{template`, first wikilink, body token sets split by `english.dic` membership, first 96 bytes of text.
2. For each candidate order, report **adjacent** Jaccard (all / in-dic / OOV / title), prefix-96 agreement, same-class / same-template rates, and how much of the original adjacency list is kept. **Do not treat overlap as compression.**
3. Always also report **article-only** (non-redirect) pairs. Redirects are 215/384 pages here but **0.27% of text bytes** (7,455 B vs ~2.78 MB of articles+infobox). All-page Jaccard is dominated by 35-byte `#REDIRECT` stubs sharing boilerplate.
4. Kill without fxcm if: (a) the order only lifts **title** or **in-dic** Jaccard the way title-lex does, (b) article-only body/OOV/prefix all move against original, (c) byte mass of the pages you actually move is ≪ 215 KB and the mechanism is “near-duplicate stubs” that a match model already sees at distance.
5. Only then, on a later agent's budget: DIC+fxcm26 vs original on **10 MB**, not 3 MB, and not title-lex.

Script: `work/agent3/page_stats.py` → `page_stats.json`, `page_stats.tsv`.

## Measurements (384 complete pages)

| class | pages | text bytes |
|---|---:|---:|
| redirect | 215 | 7,455 |
| article | 141 | 2,027,418 |
| infobox | 22 | 735,268 |
| disambig | 5 | 10,037 |
| list | 1 | 2,770 |

Original dump already has a 53-page redirect run. Title-lex max class run = 19.

**All pages** (redirect-inflated; diagnostic only):

| order | jac body | jac in-dic | jac OOV | jac title | prefix96 | keep orig adj |
|---|---:|---:|---:|---:|---:|---:|
| original | 0.191 | 0.197 | 0.398 | 0.098 | 0.204 | 1.000 |
| title-lex (E10 dead) | 0.207 | 0.212 | **0.366** | **0.167** | 0.202 | 0.076 |
| title-token clusters | 0.190 | 0.195 | 0.386 | **0.156** | 0.196 | 0.635 |
| schema-stable | 0.235 | 0.243 | 0.522 | 0.091 | 0.260 | 0.655 |
| first-template | 0.221 | 0.227 | 0.479 | 0.083 | 0.256 | 0.480 |
| first-hub | 0.256 | 0.264 | 0.421 | 0.076 | 0.312 | 0.068 |
| schema + redir-target | 0.308 | 0.318 | 0.520 | 0.085 | 0.368 | 0.285 |

Title-lex is the only order that clearly **raises title overlap while lowering OOV overlap**. That is E10 in page stats.

**Non-redirect pages only** (~99.73% of text) — this is the table that matters:

| order | jac body | jac in-dic | jac OOV | jac title | prefix96 | same template |
|---|---:|---:|---:|---:|---:|---:|
| original | 0.094 | 0.104 | 0.047 | 0.051 | 0.065 | 0.036 |
| title-lex | **0.083** | **0.092** | **0.040** | 0.064 | **0.048** | 0.012 |
| title-token clusters | 0.095 | 0.105 | 0.047 | 0.085 | 0.061 | 0.030 |
| schema-stable | 0.098 | 0.109 | 0.048 | 0.053 | 0.063 | 0.066 |
| schema + redir-target | 0.098 | 0.109 | 0.048 | 0.053 | 0.063 | 0.066 |
| alias-bundle (redir→article) | 0.094 | 0.104 | 0.047 | 0.051 | 0.065 | 0.036 |
| **first-template** | 0.096 | 0.108 | 0.043 | **0.029** | **0.101** | **0.357** |
| first-hub | 0.088 | 0.097 | 0.041 | 0.041 | 0.072 | 0.024 |

Title-token clustering (union-find on title tokens with document frequency 2–12, 36 non-trivial components, largest 83): adjacent shared-title-token 0.113 → 0.208 on articles, body/OOV/prefix **flat**. Clustering titles is not a new mechanism. It is E10 without lexicographic order.

First-hub sort looks strong on all-pages and **fails on articles** (body and OOV down, 6.8% original adjacencies kept). Same shuffle signature as title-lex; the all-page win is redirects whose first link *is* the target.

## Three experiments (not title-sort, not random, not greedy full-content minhash)

All three are encoder permutations of `<page>` blocks with siteinfo held fixed. Decoder restores by sorting on `<id>` unless noted. Cost of a shipped perm, if any, is counted against S.

### O1 — Schema-stable partition

**Key (in-band):** `class(page)` then original index. Class = redirect if text matches `#REDIRECT [[…]]`, else disambig / list / infobox / article from title + lead markup. **No title comparison.**

**Inverse:** free (`<id>`).

**Why it is not E10:** it does not group “similar names.” It *refuses* to interleave 35-byte redirects with 14 KB articles — which is exactly what title-lex does (`Aardvark` next to `AardvarK`). On articles it is nearly original order (keeps 65.5% of all-page adjacencies; article-only metrics ≈ original, slightly up). Title-lex is **strictly worse than original** on article body/OOV/prefix.

**Why it might still fail:** redirect text is 0.27% of this prefix. fxcm's match model can already latch onto `#REDIRECT [[` at a distance (E12: distant cost is rarity, not amnesia). Ceiling on this slice is a few kilobytes of stub text, not 215 KB.

**Cheap next measurement:** class histogram + redirect byte mass on full `enwik8` (still no fxcm). If redirect bytes stay ≪ 0.2% of the file, O1 is a **constraint on other keys** (never interleave stubs with prose), not a standalone lever.

**Verdict:** survives E10 as a constraint. Does not survive as a promised % on S.

### O2 — Lead-template / infobox class, original tie-break

**Key (in-band):** first `{{template-name` in page text (lowercased), empty last, original index. Optional composition: O1 class as primary key, template as secondary, so Taxobox articles clump *inside* the article stream.

**Inverse:** free (`<id>`). Encoder-only parse; decoder never needs the key.

**Why it is not E10 and not minhash:** one markup token, not a title string, not a content sketch. On articles it **lowers** title Jaccard (0.051 → 0.029) while raising prefix-96 (0.065 → 0.101) and same-template (0.036 → 0.357). That is the opposite covariance from title-lex.

**Budget it aims at:** E11 template bits (5.6% @ 1.42 bpb), not DIC-coded function words. Species pages sharing `{{Taxobox` (9 on this slice) and country pages sharing `{{Infobox_country` (3) are alphabetically far apart; STARLIT's Doc2Vec would also group them, but STARLIT pays 215 KB for a general embedding. This key is coarse and free.

**Why it might still fail:** (1) 3 MB template DF is sparse (82 distinct first templates, 144 pages with any template); empty-template pages form a large stable clump and can fake “same-class.” (2) OOV Jaccard did **not** rise (0.047 → 0.043) — this is markup locality, not rare-name locality. (3) match model may already find `{{Taxobox` far away. (4) E10's lesson still applies if the residual after DIC inside templates is mostly dictionary words (`name`, `image`, `capital`).

**Cheap next measurement (done, `O2_BYTES.md`):** repeating first-template pages are 57% of this file **because hatnotes dominate**. Split:

- hatnote (`otheruses`, `spoiler`, `wiktionary`, …) repeating-class pages: **30.5% of file**
- schema (`infobox*` / `taxobox` / `coor*`) repeating-class pages: **13.5% of file**
- other repeating first-templates: 13.1%

Unmodified O2 (first `{{` of any kind) is **not** schema locality. It clumps unrelated articles that start with `{{otheruses`. **Kill unmodified O2 as a codec run.**

**Modified O2:** key = first infobox/taxobox/coor template, else empty, original index. Inverse still free via `<id>`. Schema-class pages are 13.5% of this prefix — not a rounding error, still match-model-risk, still no 3 MB fxcm. If a codec run is ever justified it is this key vs dump order on **10 MB**, never vs title-lex.

**Verdict:** unmodified first-template **killed** by the byte-mass split. Schema-only O2 remains the leftover ordering experiment.

### O3 — Stop paying 215,748 B; identity or O1∘O2 as prior; residual perm only if needed

**Not a new similarity sort.** Two legal variants:

- **O3a (inverse free):** encode pages in dump order, or in the deterministic order `(class, first_template, original_index)`. Delete STARLIT's `new_article_order`. Metadata = 0. Immediate **+215,748 B on S** if the archive does not grow by more than that.
- **O3b (metadata accounted):** if a later measurement shows some paid order still beats the prior in-regime, ship only the **inversion relative to O3a**, delta+xz, same format STARLIT already uses. Cost scales with disagreement, not with `n log n`. E3 already noted STARLIT is largely consecutive-id runs, so disagreement vs identity may already be the compressed 215 KB — a derived prior that captures schema+template blocks should shrink it, or show that the residual is not worth keeping.

**Why E10 does not kill this:** E10 never tested STARLIT's permutation. It tested title-lex, which on article bytes is *worse than identity*. STARLIT is block-preserving (E3), i.e. closer to identity than to title-lex. Paying 215 KB to perturb an order that DIC+fxcm26 already does not want perturbed is the live risk. Break-even: the paid order must beat identity by **>215,748 B on the enwik9 archive** (~0.2% of S), after DIC.

**Cheap next measurement (no fxcm, no 3 MB codec):** ingest STARLIT `nao` when present (not in this tree). Report run-length of consecutive original ids, Kendall-ish displacement vs identity vs `(class, first_template, index)`, and the same article-only overlap table. If STARLIT looks like title-lex (title Jaccard up, OOV/prefix down), it is dead without fxcm. If it looks like O2 (template/prefix up) or raises article OOV, then and only then is a full-pipeline compare justified — on 10 MB, not 3 MB.

**Verdict:** **survives E10 as accounting.** Highest expected value per hour if the campaign is still shipping or planning to ship a 215 KB perm. It is not an “ordering gain”; it is refusing to pay for a shuffle the real regime has not been shown to want.

## Does any idea survive E10's lesson?

E10's lesson, stated tightly: **grouping pages by title string similarity is redundant with DIC and slightly harmful once the CM is strong, because it rips up dump-order clumps.**

| idea | survives? |
|---|---|
| Title-lex, title-reversed, title-token clusters, TITLECAST-as-sort | **No.** Same mechanism. Clusters measured here: title overlap up, body OOV not. |
| Random | **No.** E3 −0.53% on testbed; no reason it would invert after DIC. |
| Greedy minhash of full content | **No.** Already worse than title-lex in E3 and would *pay* metadata. Forbidden to repeat. |
| Interleave redirects with their target articles (alias-bundle / first-hub) | **No** on this slice. Recreates title-lex interleave; article-only body/OOV drop or stay. |
| O1 schema-stable | **Yes as a constraint** (do not shuffle stubs through prose). **No as a %.** Redirect bytes are 0.27% here. |
| O2 lead-template (any `{{`) | **No.** Byte-mass gate: 30.5% of the file is repeating **hatnotes**. That is not Taxobox locality. |
| O2 schema-only (infobox/taxobox/coor) | **Provisionally yes**, 13.5% of file, opposite covariance from E10 still untested on this key. At most one 10 MB DIC+fxcm26 vs original. |
| O3 drop/residual STARLIT 215,748 B | **Yes as accounting.** Open fact: STARLIT's own order is untested in-regime. Identity is the E10-implied default. |

**Campaign recommendation:** treat original dump order as the incumbent permutation (inverse free, 0 B). Do not spend a 3 MB fxcm run on ordering. If one codec run is ever justified, it is **schema-only O2** (infobox/taxobox/coor, not hatnotes) composed with O1 vs original on **10 MB** DIC+fxcm26, with the 215,748 B STARLIT file counted in S for any arm that still ships a perm. Title-lex and unmodified first-template stay on the kill list.
