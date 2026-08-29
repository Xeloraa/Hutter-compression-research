# Causal OOV copy oracle on raw enwik8.3m (not DIC). No fxcm.
import math
import re
from pathlib import Path

RAW = Path(r"C:\Users\vivi\hutter\data\enwik8.3m")
DIC = Path(r"C:\Users\vivi\hutter\work\english.dic")
if not DIC.exists():
    DIC = Path(r"C:\Users\vivi\hutter\english.dic")
OUT = Path(r"C:\Users\vivi\hutter\work\agent7\OOV.md")

def load_dic_words(p):
    words = set()
    buf = []
    for c in p.read_bytes():
        if 97 <= c <= 122:
            buf.append(chr(c))
        elif buf:
            words.add("".join(buf))
            buf = []
    if buf:
        words.add("".join(buf))
    return words

def gamma_bits(n):
    if n < 1:
        n = 1
    b = n.bit_length()
    return 2 * b - 1

def main():
    dic = load_dic_words(DIC)
    text = RAW.read_bytes().decode("latin-1")
    toks = list(re.finditer(r"[A-Za-z]+", text))
    last = {}
    spell_bits = 0.0
    mix_bits = 0.0
    oov_n = 0
    oov_second = 0
    oov_copy_wins = 0
    oov_save = 0.0
    for i, m in enumerate(toks):
        w = m.group().lower()
        if w in dic:
            continue
        oov_n += 1
        slen = 8 * len(m.group())
        spell_bits += slen
        if w not in last:
            mix_bits += slen
        else:
            oov_second += 1
            gap = i - last[w]
            p = 1 + gamma_bits(gap)
            if p < slen:
                mix_bits += p
                oov_copy_wins += 1
                oov_save += slen - p
            else:
                mix_bits += slen
        last[w] = i
    prefix_hits = 0
    prefix_n = 0
    last_pos = {}
    for i, m in enumerate(toks):
        w = m.group().lower()
        if w in dic:
            continue
        if w in last_pos:
            prev = last_pos[w]
            a0, a1 = max(0, prev - 3), prev
            b0, b1 = max(0, m.start() - 3), m.start()
            prefix_n += 1
            if text[a0:a1] == text[b0:b1] and (a1 - a0) == 3:
                prefix_hits += 1
        last_pos[w] = m.start()
    file_bits = 8 * len(text)
    save = spell_bits - mix_bits
    frac = 100 * prefix_hits / prefix_n if prefix_n else 0
    lines = [
        f"raw_bytes={len(text)} alpha_tokens={len(toks)} dic_words={len(dic)}",
        f"oov_tokens={oov_n} oov_repeats={oov_second} copy_wins={oov_copy_wins}",
        f"spell_bits={spell_bits:.0f} mix_bits={mix_bits:.0f} save={save:.0f} ({100*save/file_bits:.3f}% of file bits)",
        f"save_on_wins={oov_save:.0f}",
        f"repeat_3byte_prefix_match={prefix_hits}/{prefix_n} ({frac:.1f}%)",
    ]
    OUT.write_text("# OOV copy oracle\n\n" + "\n".join(f"- {x}" for x in lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
