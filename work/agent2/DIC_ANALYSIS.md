# DIC 3MB stream (enwik8.3m.dic, 1,814,514 B)

Measured 2026-08-29. Not a pipeline result.

| class | bytes | % |
|---|---:|---:|
| ≥128 (dict codes / UTF8-like) | 726,143 | **40.02** |
| ASCII printable 32–126 | 1,018,301 | 56.12 |
| <32 (mostly newline/form-feed) | 70,070 | 3.86 |

High-byte **runs**: n=416,684, mean **1.74**, median 2, max **4**.
Low-byte runs: mean 2.61, median 1, max 214 (prose).

Codes are 2–3 byte tokens, not long high-byte regions. The LSTM sees a stream that flips regime every couple of bytes. ForgetBias=1 (keep cell state) mixes “in a codeword” with “in ASCII” on the next token. That is the mechanism for E30’s standalone ranking (smaller forget bias better), and why a **boundary reset** (E37) is the non-blunt version.

Top bytes: space 400k, `@` (64, FIRSTUPPER) 94k, `]`/`[` 62k, newline 34k, then high bytes 194/223/183.

Do not re-run title-order (E10). Redirects dominate the raw 3MB prefix (agent 3: 215/384 pages) but DIC already collapses repeated words across articles.
