# Campaign strategy (reset 2026-08-29, A-list after A2/A3/A4)

**Win condition:** verified **S = compressor + archive9 on enwik9** under
official rules that beats the paid record (today **110,793,128**) and then
the moving 1% gate (**109,685,197**).

**Not the win condition:** any 3 MB DIC→fxcm26 number, including 517,996.

## Classification

- **A** — could remove megabytes on enwik9 or unlock a new mechanism of that weight.
- **B** — cheap test that characterizes or kills an A idea.
- **C** — local micro-opt. Run only if it credibly feeds A.

Prefer A. Reject C.

## Ranked A-list (A2/A3/A4 dead)

| rank | item | expected enwik9 ΔS | next measurement | class |
|---|---|---|---|---|
| **1** | **A1** tree head **with** `SetInput`, freeze stock 170c/1L/h=128, inside **cmix-lex** | 0 (neutral) or **50–300 KB** (not 1.1 MB); or archive grows | Linux 10–30 MB full-stack A/B (`A1_PATCH.md`) | **A** (only live A) |
| 2 | **A5** typed body streams (URL + wiki-markup vs prose) — PHDA9 does not split the body | unknown; URL mass 2.43 MB on enwik8 but 97.6% unique | cheap zlib/lzma of split vs original (`A4.md` “Next A”) | **A question, not run** |
| 3 | A2 leftover: post-WRT tail D99 autopsy (regime 2 bytes we have not seen) | unknown; raw analogs already died | Linux `cmix -s` dump, no 43 h compress | **B** |
| — | A4 title-index `[[Target]]` → in-band page varint | 50–150 KB after overlap (zlib kept 25 KB / 967 KB raw) | done (`A4.md`) | **killed as A** |
| — | A3 dump aliases / second WRT / File: / navbox / table columns / infobox-by-key | tens of KB | done (`A3.md`) | **killed as A** |
| — | A2 second payload_lex region | tens of KB or net-neg | done (`A2.md`) | **killed as A** |
| — | Forget-bias / mixer slots / OOV pointer / 3 MB width | bytes on 517,996 | stopped | **C — do not run** |

A1 cannot close the next 1.1 MB gate alone. It is the only remaining
mechanism that sits **inside the stack that holds S** and is not a
replay of payload_lex or an LSTM **hyperparam** sweep.

## Closed — do not reopen

- E30e Class C: MinGW 517905 EXACT, −190 vs MinGW 518095. Forget-bias **STOPPED**.
- E41 OOV pointer **DEAD** (zlib/lzma lose on pointer stream).
- A2 PHDA9/payload-lex **not** a leftover MB. cmix-lex took regime-1 D99/D86a.
- A3 **not** a leftover MB. Self-pipe 8 KB; WRT leftover is 1-letter crumbs
  (95.3% letter-cover); fair table columns +10 KB lzma; infobox-by-key +3.5 KB.
- A4 **not** a leftover MB. 112,935 / 805,646 article links resolve on
  enwik8 (14%); 95% of those titles are fully in `english.dic`. Whole-file
  zlib **+25,266** on a **967,199** raw cut. Span lzma **+17,264**.
  Shuffled page-ids match live. Dangling extra copies (4.86 MB) are the
  A2 link-list mass. Lead-bold 96 KB is match-owned.

## Parked G5 — lastCW as LSTM `input_symbol` (supporting / C)

Not A4. Not mixer slots (E19 already died at **+0.024%** putting lastCW
*buckets* into mixer inputs). The cmix LSTM still one-hots the DIC byte
(`Perceive(c0&255)`). Setting `input_symbol = 128 + (lastCW % 128)` on
`c≥0x80` is G5: a different *channel*, same unused identity.

Do **not** spend a 3 MB fxcm pipeline on this. Agent7 lastCW identity vs
unigram already died (mass is frequent words `worcxt` owns). A reopen
requires an oracle that lastCW-as-input removes **≥0.4% of FILE bits**
versus fxcm word models, with a shuffled-lastCW control that does *not*
match live. We do not have that oracle. Treat as **Class C / supporting**
until someone does. Then stop; do not implement on a hope.

## Work now

Linux **A1** A/B per `A1_PATCH.md`. This machine has no WSL — spec only.

If A1 is in flight elsewhere: the next cheap filter is **A5** (typed body
streams), not another 3 MB `cmp` and not a lastCW LSTM patch.

Do not start E32, E35, E36, E41, width sweeps, or another 3 MB `cmp`.
Do not drop in `BtLstm` aux=0 92c/3L.
