# Hutter Prize research

Two numbers that must not be mixed:

1. **Official prize record (enwik9, S = compressor + archive9):** **110,793,128** bytes (fx2-cmix). Next paid gate: **S < 109,685,197**. Source: http://prize.hutter1.net/ (verified 2026-08-29).
2. **Internal 3 MB screen (enwik8 prefix → DIC → fxcm26):** **517,996** bytes, config 92c/3L/blocks=4/initMul=0.5, MD5 `a52a41bd426904afcc48d1b9a99c8f1d`. This is a local floor for experiments, not the world record.

The search target is a legal full-scale result that can contest (1). Beating (2) is only the lab gate for an idea.

See `work/agent10/PRIZE.md` for the gap analysis (this tree is fxcm+LSTM, not the fx2-cmix ensemble).

## Locked fallback (immutable)

Sources, checksums, and provenance: `locked/`. Never overwrite. Experiments live under `work/`.

Linux reproduce: `locked/BUILD.sh` then `locked/VERIFY.sh`. `english.dic` must be in the working directory.

## Layout

| Path | Contents |
|---|---|
| `locked/` | Frozen 517,996 candidate |
| `work/src/` | Live experiment copies |
| `work/agent1` … `agent10` | Isolated notes and screens |
| `log/` | `RESEARCH_LOG.md`, `EXPERIMENTS.md`, `ledger.jsonl` |
| `tools/` | Standalone LSTM probe and scripts |
| `data/` | Small DIC prefixes; **not** enwik8/enwik9 |

## Invariants

Exact roundtrip for any candidate. Standalone LSTM bpb is ranking only. Full-scale hours must come from a measured pipeline, not Windows wall time. MinGW archives are not the Linux lock until compared on the same compiler.

## License

fxcm, cmix dictionary, and LSTM layer: GPL (Kaido Orav / kaitz, Byron Knoll). See source file headers.
