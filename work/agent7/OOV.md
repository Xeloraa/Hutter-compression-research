# OOV copy oracle (raw 3 MB prefix)

- raw_bytes=3000000 alpha_tokens=427892 dic_words=44515
- oov_tokens=39447 oov_repeats=27008 copy_wins=15578
- spell_bits=1408920 mix_bits=1039482 save=369438 (**1.539% of file bits** vs 8-bit spelling)
- **3-byte preceding prefix match on repeats: 8,544 / 27,008 (31.6%)**

## Interpretation

Kill rule was: if ≥80% of repeats already have a matching byte prefix, MatchModel2 owns it. **31.6% ≠ 80%.** About two-thirds of OOV repeats occur in a *new* 3-byte context. That is the pointer-vs-match gap.

Still not an archive size: 1.54% is vs 8-bit spelling. fxcm already compresses those bytes. The question for a later pipeline is whether a causal OOV index beats match+LSTM on the **68% unmatched-prefix** repeats.

Do not wire 3 MB until a DIC-stream version of this oracle exists (OOV after english.dic, not raw letters).
