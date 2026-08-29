# Fast lastCW LRU: O(1) membership, cost 1+log2(|cache|). No OrderedDict rank walk.
import math
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(r"C:\Users\vivi\hutter")
DIC_PATH = ROOT / "work" / "english.dic"
if not DIC_PATH.exists():
    DIC_PATH = ROOT / "english.dic"
STREAM = ROOT / "data" / "enwik8.3m.dic"
OUT = ROOT / "work" / "agent7" / "RARE_LRU.md"

K_BOUNDARY1 = 80
K_BOUNDARY2 = 80 + 3840
K_BOUNDARY3 = 80 + 3840 + 40960


def load_byte_to_id(dic_path):
    data = dic_path.read_bytes()
    byte_to_id = {}
    line = []
    line_count = 0
    for c in data:
        if 97 <= c <= 122:
            line.append(c)
        elif line:
            if line_count < K_BOUNDARY1:
                b = 0x80 + line_count
            elif line_count < K_BOUNDARY2:
                n = line_count - K_BOUNDARY1
                b = 0xD0 + (n // 80)
                b += (0x80 + (n % 80)) << 8
            elif line_count < K_BOUNDARY3:
                n = line_count - K_BOUNDARY2
                b = 0xF0 + ((n // 80) // 32)
                b += (0xD0 + ((n // 80) % 32)) << 8
                b += (0x80 + (n % 80)) << 16
            else:
                n = line_count - K_BOUNDARY3
                b = 0xD0 + ((n // 80) // 32)
                b += (0xD0 + ((n // 80) % 32)) << 8
                b += (0x80 + (n % 80)) << 16
            byte_to_id[b] = line_count
            line_count += 1
            line = []
    return byte_to_id, line_count


def extract_ids(stream, byte_to_id):
    ids = []
    i = 0
    n = len(stream)
    while i < n:
        c = stream[i]
        if c == 0x0C:
            i += 2
            continue
        if c >= 0x80:
            b = c
            i += 1
            if c > 0xCF and i < n:
                c2 = stream[i]
                b += c2 << 8
                i += 1
                if c2 > 0xCF and i < n:
                    b += stream[i] << 16
                    i += 1
            wid = byte_to_id.get(b)
            if wid is not None:
                ids.append(wid)
            continue
        i += 1
    return ids


def bucket(cnt):
    if cnt == 1:
        return "hapax"
    if cnt <= 5:
        return "cnt2-5"
    if cnt <= 20:
        return "cnt6-20"
    return "cnt>20"


def run(ids, logp, uni, K, rare_only, rare_T=5):
    lr = OrderedDict()
    last = {}
    freq = Counter(ids)
    bits = 0.0
    hits = 0
    save_by = Counter()
    far_rare_hits = 0
    far_rare_n = 0
    causal = Counter()
    for i, w in enumerate(ids):
        u = logp[w]
        gap = (i - last[w]) if w in last else None
        rare_far = freq[w] <= 5 and gap is not None and gap > 256
        if rare_far:
            far_rare_n += 1
        if w in lr:
            p = 1 + math.log2(max(len(lr), 1))
            if p < u:
                bits += p
                hits += 1
                save_by[bucket(freq[w])] += u - p
                if rare_far:
                    far_rare_hits += 1
            else:
                bits += u
        else:
            bits += u
        last[w] = i
        causal[w] += 1
        if rare_only:
            if causal[w] <= rare_T:
                if w in lr:
                    lr.move_to_end(w)
                else:
                    if len(lr) >= K:
                        lr.popitem(last=False)
                    lr[w] = 1
            elif w in lr:
                del lr[w]
        else:
            if w in lr:
                lr.move_to_end(w)
            else:
                if len(lr) >= K:
                    lr.popitem(last=False)
                lr[w] = 1
    return {
        "save": uni - bits,
        "hits": hits,
        "save_by": save_by,
        "far_rare_hits": far_rare_hits,
        "far_rare_n": far_rare_n,
    }


def main():
    byte_to_id, vocab = load_byte_to_id(DIC_PATH)
    stream = STREAM.read_bytes()
    ids = extract_ids(stream, byte_to_id)
    n = len(ids)
    freq = Counter(ids)
    logp = {w: math.log2(n / c) for w, c in freq.items()}
    uni = sum(logp[w] for w in ids)
    file_bits = 8 * len(stream)

    lines = [
        "# lastCW LRU-index oracle (modified Idea 1)",
        "",
        "gamma(file-gap) was killed. This recode uses LRU membership and cost 1+log2(|cache|), independent of file distance while the id remains in the cache.",
        "Rare-only: admit ids whose causal count so far is <=5; graduate-and-evict when count exceeds 5.",
        "",
        f"dic_bytes={len(stream)} tokens={n} vocab={vocab} unigram_bits={uni:.0f} ({100*uni/file_bits:.2f}% of DIC-file bits)",
        "",
        "## All-id LRU vs unigram (min of unigram and 1+log2 K)",
    ]
    for K in (64, 256, 1024, 4096, 16384, 65536):
        r = run(ids, logp, uni, K, rare_only=False)
        lines.append(
            f"- all K={K} save={r['save']:.0f} ({100*r['save']/uni:.2f}% uni, {100*r['save']/file_bits:.3f}% DIC-file) "
            f"hits={r['hits']} save>20={r['save_by']['cnt>20']:.0f} save2-5={r['save_by']['cnt2-5']:.0f} "
            f"far_rare_hits={r['far_rare_hits']}/{r['far_rare_n']}"
        )
    lines.append("")
    lines.append("## Rare-only LRU (causal count <=5)")
    for K in (256, 1024, 4096, 16384, 65536):
        r = run(ids, logp, uni, K, rare_only=True)
        lines.append(
            f"- rare K={K} save={r['save']:.0f} ({100*r['save']/uni:.2f}% uni, {100*r['save']/file_bits:.3f}% DIC-file) "
            f"hits={r['hits']} save2-5={r['save_by']['cnt2-5']:.0f} save6-20={r['save_by']['cnt6-20']:.0f} save>20={r['save_by']['cnt>20']:.0f} "
            f"far_rare_hits={r['far_rare_hits']}/{r['far_rare_n']}"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("If almost all LRU save is still cnt>20, membership recoding did not create a rare-identity expert.")
    lines.append("Survive as a rare expert only if rare-only save on cnt2-5 is a non-rounding slice of DIC-file bits and far_rare_hits is not ~0.")
    lines.append("Still vs a global unigram, not vs fxcm word hashes.")
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
