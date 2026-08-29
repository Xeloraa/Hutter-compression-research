# DIC-stream OOV copy oracle + MatchModel2-faithful overlap.
# Residual is a-z runs in enwik8.3m.dic (what fxcm actually sees).
# MatchModel2 shortest hash is LEN1=5 (not 3). See fxcm26_slots.cpp LEN1/LEN2/LEN3.
import math
from collections import Counter, defaultdict, OrderedDict
from pathlib import Path

ROOT = Path(r"C:\Users\vivi\hutter")
STREAM = ROOT / "data" / "enwik8.3m.dic"
RAW = ROOT / "data" / "enwik8.3m"
DIC = ROOT / "work" / "english.dic"
if not DIC.exists():
    DIC = ROOT / "english.dic"
OUT = ROOT / "work" / "agent7" / "DIC_OOV.md"

K_ESCAPE = 0x0C
LENS = (3, 5, 7, 9)


def gamma_bits(n):
    if n < 1:
        n = 1
    b = n.bit_length()
    return 2 * b - 1


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
    """Advance over escape and dict-code; return new i (no-op if ascii)."""
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
    """Maximal a-z runs. Returns list of (start, end, word)."""
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


class LRU:
    def __init__(self, k):
        self.k = k
        self.d = OrderedDict()

    def probe(self, w):
        if w not in self.d:
            return None
        rank = 0
        for key in reversed(self.d):
            rank += 1
            if key == w:
                return rank
        return None

    def touch(self, w):
        if w in self.d:
            self.d.move_to_end(w)
        else:
            if len(self.d) >= self.k:
                self.d.popitem(last=False)
            self.d[w] = 1


def ppm3_bits_on_mask(stream, mask):
    """Order-3 KT-smoothed bits on residual letters; context is the full stream."""
    cnt = defaultdict(Counter)
    tot = Counter()
    bits = 0.0
    n_scored = 0
    ctx = 0
    for i, b in enumerate(stream):
        if mask[i]:
            t = tot[ctx]
            p = (cnt[ctx][b] + 0.5) / (t + 128.0) if t else 1.0 / 256.0
            bits += -math.log2(max(p, 1e-12))
            n_scored += 1
        cnt[ctx][b] += 1
        tot[ctx] += 1
        ctx = ((ctx << 8) | b) & 0xFFFFFF
    return bits, n_scored


def main():
    stream = STREAM.read_bytes()
    raw_n = RAW.stat().st_size if RAW.exists() else 3000000
    dic_words = load_dic_words(DIC)
    runs = letter_runs(stream)
    file_bits = 8 * len(stream)
    raw_bits = 8 * raw_n

    # residual letter bytes
    mask = bytearray(len(stream))
    letter_bytes = 0
    for a, b, w in runs:
        for i in range(a, b):
            mask[i] = 1
        letter_bytes += b - a

    in_dic_runs = sum(1 for _, _, w in runs if w in dic_words)
    oov_runs = [(a, b, w) for a, b, w in runs if w not in dic_words]
    # substring leftovers: a-z run that is a prefix/suffix of a dic word is still
    # "in dic" as a whole run only if the exact run is a dic word. Leftovers stay OOV.

    spell = 0.0
    mix_g = 0.0
    last = {}
    prev_starts = defaultdict(list)
    copy_wins = 0
    oov_n = len(oov_runs)
    oov_rep = 0
    save_on_wins = 0.0
    gap_tok = []
    gap_byte = []
    overlap = {L: [0, 0] for L in LENS}  # hits, n on repeats
    any_overlap = {L: [0, 0] for L in LENS}
    len_hist = Counter()
    # LRU index (modified coding, not gamma of file gap)
    lru_stats = {}
    for K in (64, 256, 1024, 4096):
        lru_stats[K] = {"bits": 0.0, "hits": 0, "wins_vs_spell": 0}

    lrus = {K: LRU(K) for K in lru_stats}

    for idx, (a, b, w) in enumerate(oov_runs):
        slen = 8 * (b - a)
        spell += slen
        len_hist[b - a] += 1
        if w not in last:
            mix_g += slen
            for K, lr in lrus.items():
                lru_stats[K]["bits"] += slen
                lr.touch(w)
        else:
            oov_rep += 1
            prev_i, prev_a = last[w]
            gtok = idx - prev_i
            gbyte = a - prev_a
            gap_tok.append(gtok)
            gap_byte.append(gbyte)
            p = 1 + gamma_bits(gtok)
            if p < slen:
                mix_g += p
                copy_wins += 1
                save_on_wins += slen - p
            else:
                mix_g += slen
            for L in LENS:
                overlap[L][1] += 1
                if prefix_equal(stream, prev_a, a, L):
                    overlap[L][0] += 1
                any_overlap[L][1] += 1
                if any_prev_prefix(stream, prev_starts[w], a, L):
                    any_overlap[L][0] += 1
            for K, lr in lrus.items():
                rank = lr.probe(w)
                if rank is not None:
                    cost = 1 + gamma_bits(rank)
                    lru_stats[K]["hits"] += 1
                else:
                    cost = slen
                if cost < slen:
                    lru_stats[K]["bits"] += cost
                    lru_stats[K]["wins_vs_spell"] += 1
                else:
                    lru_stats[K]["bits"] += slen
                lr.touch(w)
        last[w] = (idx, a)
        prev_starts[w].append(a)

    save_g = spell - mix_g
    # leftover after excluding last-occ LEN=5 prefix matches (MatchModel2 shortest)
    last = {}
    leftover_spell = 0.0
    leftover_mix = 0.0
    leftover_n = 0
    leftover_wins = 0
    for idx, (a, b, w) in enumerate(oov_runs):
        slen = 8 * (b - a)
        if w not in last:
            last[w] = (idx, a)
            continue
        prev_i, prev_a = last[w]
        matched5 = prefix_equal(stream, prev_a, a, 5)
        last[w] = (idx, a)
        if matched5:
            continue
        leftover_n += 1
        leftover_spell += slen
        p = 1 + gamma_bits(idx - prev_i)
        if p < slen:
            leftover_mix += p
            leftover_wins += 1
        else:
            leftover_mix += slen

    ppm_bits, n_scored = ppm3_bits_on_mask(stream, mask)
    # PPM vs pointer: not a joint code; reports CM-like cost of residual letters.

    def pct(h, n):
        return 100.0 * h / n if n else 0.0

    def med(xs):
        if not xs:
            return 0
        ys = sorted(xs)
        return ys[len(ys) // 2]

    lines = []
    lines.append("# DIC-stream OOV copy oracle")
    lines.append("")
    lines.append("Pipeline input: `data/enwik8.3m.dic`. Residual OOV = maximal `a-z` runs whose exact string is **not** an `english.dic` word (substring leftovers stay OOV).")
    lines.append("")
    lines.append("MatchModel2 (`fxcm26_slots.cpp`): shortest candidate hash is **LEN1=5**, then 7 and 9. The raw-text E38 test used a 3-byte prefix and **overstated** match overlap.")
    lines.append("")
    lines.append("## Stream")
    lines.append(f"- dic_bytes={len(stream)} residual_letter_bytes={letter_bytes} ({100*letter_bytes/len(stream):.2f}% of DIC file)")
    lines.append(f"- letter_runs={len(runs)} exact_dic_word_runs={in_dic_runs} oov_runs={oov_n} oov_repeats={oov_rep}")
    lines.append(f"- oov_types={len({w for _,_,w in oov_runs})} in_dic_run_types={len({w for _,_,w in runs if w in dic_words})}")
    lines.append("")
    lines.append("## Copy vs 8-bit spelling of residual OOV runs")
    lines.append(f"- spell_bits={spell:.0f} mix_gamma_bits={mix_g:.0f} save={save_g:.0f}")
    lines.append(f"- save vs DIC-file bits: {100*save_g/file_bits:.3f}% ({save_g/8:.0f} bytes-equivalent)")
    lines.append(f"- save vs raw 3MB bits: {100*save_g/raw_bits:.3f}%")
    lines.append(f"- copy_wins={copy_wins} save_on_wins={save_on_wins:.0f}")
    if gap_tok:
        lines.append(f"- gap_tokens median={med(gap_tok)} mean={sum(gap_tok)/len(gap_tok):.1f} p90={sorted(gap_tok)[int(0.9*len(gap_tok))]}")
        lines.append(f"- gap_bytes median={med(gap_byte)} mean={sum(gap_byte)/len(gap_byte):.1f} p90={sorted(gap_byte)[int(0.9*len(gap_byte))]}")
    lines.append("- length histogram (run bytes, top): " + ", ".join(
        f"{k}:{v}" for k, v in len_hist.most_common(12)))
    lines.append("")
    lines.append("## MatchModel2 prefix overlap on OOV repeats")
    lines.append("| L | last-occ prefix | any prior occ prefix |")
    lines.append("|---:|---:|---:|")
    for L in LENS:
        h, n = overlap[L]
        h2, n2 = any_overlap[L]
        lines.append(f"| {L} | {h}/{n} ({pct(h,n):.1f}%) | {h2}/{n2} ({pct(h2,n2):.1f}%) |")
    lines.append("")
    lines.append("LEN=3 is **not** a MatchModel2 candidate length. LEN=5 is the honest kill test.")
    lines.append("")
    lines.append("## Leftover after removing last-occ LEN=5 matches")
    lines.append(f"- unmatched_repeats={leftover_n} leftover_spell={leftover_spell:.0f} leftover_mix={leftover_mix:.0f} leftover_save={leftover_spell-leftover_mix:.0f} wins={leftover_wins}")
    lines.append(f"- leftover save vs DIC-file bits: {100*(leftover_spell-leftover_mix)/file_bits:.3f}%")
    lines.append("")
    lines.append("## Modified coding: LRU rank (γ(rank)), not γ(file-gap)")
    for K, st in lru_stats.items():
        save = spell - st["bits"]
        lines.append(f"- LRU K={K} bits={st['bits']:.0f} save={save:.0f} ({100*save/file_bits:.3f}% DIC-file) hits={st['hits']} wins_vs_spell={st['wins_vs_spell']}")
    lines.append("")
    lines.append("## Order-3 KT on residual letter bytes (full-stream context)")
    lines.append(f"- ppm3_bits={ppm_bits:.0f} on {n_scored} residual letters ({ppm_bits/max(n_scored,1):.3f} bpb)")
    lines.append(f"- vs 8-bit: save {8*n_scored - ppm_bits:.0f} bits ({100*(8*n_scored-ppm_bits)/file_bits:.3f}% DIC-file)")
    lines.append(f"- pointer-gamma vs ppm3 (not a joint code): mix_gamma={mix_g:.0f} vs ppm3={ppm_bits:.0f} (ppm scores ALL residual letters including first occurrences)")
    # Restrict PPM comparison: first occ must be spelled; pointer only on repeats.
    # ppm includes first occ so it should be compared to spell on all oov letters.
    lines.append(f"- 8-bit all residual OOV letters={spell:.0f}; PPM is a tighter *baseline for spelling*, not for identity pointers.")
    lines.append("")
    lines.append("## Verdict gate")
    lines.append("Kill if leftover after LEN=5 last-occ match is <0.15% of DIC-file bits, or if LEN=5 any-prior overlap ≥80%.")
    lines.append("Survive (ceiling only) if leftover is large **and** LEN=5 overlap stays well below 80%. Still not a pipeline result: CMs also model letter n-grams; PPM4 is that check.")
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
