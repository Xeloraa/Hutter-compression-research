# Leftover OOV save by run length, and after any-prior LEN=5 match.
# Reuses the same letter-run walk as dic_oov_oracle.py. No PPM.
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\vivi\hutter")
STREAM = ROOT / "data" / "enwik8.3m.dic"
DIC = ROOT / "work" / "english.dic"
if not DIC.exists():
    DIC = ROOT / "english.dic"
OUT = ROOT / "work" / "agent7" / "DIC_OOV_LEFTOVER.md"
K_ESCAPE = 0x0C


def gamma_bits(n):
    if n < 1:
        n = 1
    return 2 * n.bit_length() - 1


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


def skip_codes_and_escapes(s, i):
    n = len(s)
    c = s[i]
    if c == K_ESCAPE:
        return min(i + 2, n)
    if c >= 0x80:
        i += 1
        if c > 0xCF and i < n:
            c2 = s[i]
            i += 1
            if c2 > 0xCF and i < n:
                i += 1
        return i
    return i + 1


def letter_runs(stream):
    runs = []
    i, n = 0, len(stream)
    while i < n:
        c = stream[i]
        if 97 <= c <= 122:
            j = i
            while j < n and 97 <= stream[j] <= 122:
                j += 1
            runs.append((i, j, stream[i:j].decode("ascii")))
            i = j
        else:
            i = skip_codes_and_escapes(stream, i) if c >= 0x80 or c == K_ESCAPE else i + 1
    return runs


def prefix_equal(stream, a, b, L):
    if a < L or b < L:
        return False
    return stream[a - L : a] == stream[b - L : b]


def any_prev_prefix(stream, prev_starts, cur, L):
    for p in prev_starts:
        if prefix_equal(stream, p, cur, L):
            return True
    return False


def main():
    stream = STREAM.read_bytes()
    dic_words = load_dic_words(DIC)
    oov = [(a, b, w) for a, b, w in letter_runs(stream) if w not in dic_words]
    file_bits = 8 * len(stream)
    last = {}
    prev_starts = defaultdict(list)
    by_len_all = defaultdict(lambda: [0.0, 0.0, 0])  # spell, mix, n_rep
    by_len_l5 = defaultdict(lambda: [0.0, 0.0, 0])  # leftover last-occ L=5
    by_len_any5 = defaultdict(lambda: [0.0, 0.0, 0])
    for idx, (a, b, w) in enumerate(oov):
        slen = 8 * (b - a)
        Lrun = b - a
        if w in last:
            prev_i, prev_a = last[w]
            p = 1 + gamma_bits(idx - prev_i)
            mix = p if p < slen else slen
            by_len_all[Lrun][0] += slen
            by_len_all[Lrun][1] += mix
            by_len_all[Lrun][2] += 1
            if not prefix_equal(stream, prev_a, a, 5):
                by_len_l5[Lrun][0] += slen
                by_len_l5[Lrun][1] += mix
                by_len_l5[Lrun][2] += 1
            if not any_prev_prefix(stream, prev_starts[w], a, 5):
                by_len_any5[Lrun][0] += slen
                by_len_any5[Lrun][1] += mix
                by_len_any5[Lrun][2] += 1
        last[w] = (idx, a)
        prev_starts[w].append(a)

    def dump(title, d):
        lines = [title, "| run_len | n_repeats | leftover_save_bits | % DIC-file |", "|---:|---:|---:|---:|"]
        tot_s = tot_n = 0.0
        tot_r = 0
        for L in sorted(d):
            spell, mix, n = d[L]
            save = spell - mix
            tot_s += save
            tot_n += n
            tot_r += n
            lines.append(f"| {L} | {n} | {save:.0f} | {100*save/file_bits:.3f} |")
        lines.append(f"| **all** | {tot_r} | {tot_s:.0f} | {100*tot_s/file_bits:.3f} |")
        # bins
        def band(lo, hi):
            s = n = 0
            for L, (sp, mx, nn) in d.items():
                if lo <= L <= hi:
                    s += sp - mx
                    n += nn
            return n, s
        for lo, hi, name in ((1, 2, "len 1-2"), (3, 5, "len 3-5"), (6, 99, "len >=6")):
            n, s = band(lo, hi)
            lines.append(f"- {name}: n={n} save={s:.0f} ({100*s/file_bits:.3f}% DIC-file)")
        return lines, tot_s

    lines = ["# DIC OOV leftover by run length", ""]
    a, s_all = dump("## All OOV repeats (copy vs 8-bit)", by_len_all)
    lines += a + [""]
    b, s_l5 = dump("## After dropping last-occ LEN=5 prefix matches", by_len_l5)
    lines += b + [""]
    c, s_a5 = dump("## After dropping any-prior LEN=5 prefix matches (tighter MatchModel overlap)", by_len_any5)
    lines += c + [""]
    lines.append("len 1-2 leftovers are substring crumbs after DIC; a pointer on 8-16 bit spellings is not a name expert.")
    lines.append("len >=6 unmatched by LEN=5 is the identity residual worth a later mixer expert.")
    lines.append(f"Summary leftover save: all={s_all:.0f} last5={s_l5:.0f} any5={s_a5:.0f} bits.")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
