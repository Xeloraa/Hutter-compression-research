# Obtaining the development corpus

The official **enwik8** dump is not stored in this repository (100 MB).

1. Download enwik8 from the Hutter Prize / Large Text Compression Benchmark sources.
2. Verify MD5: `a1fa5ffddb56f4953e226637dabbb36a`
3. Place it at `data/enwik8`.
4. Prefixes used in this campaign:
   - `enwik8.3m` — first 3,000,000 bytes (real-pipeline slice)
   - After DIC: `enwik8.3m.dic` is 1,814,514 bytes

Standalone LSTM screens use `data/dic200k.bin` and `data/dic400k.bin` (checked in). Those are prefixes of the DIC-encoded 3 MB slice, not the raw dump.
