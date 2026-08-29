# Agent 7 Idea 1 — lastCW recency oracle (no fxcm).
# Walks DIC bytes the same way Dictionary::AddToBuffer reconstructs codes.
import math
from pathlib import Path

DIC_PATH = Path(r"C:\Users\vivi\hutter\work\english.dic")
STREAM = Path(r"C:\Users\vivi\hutter\data\enwik8.3m.dic")
OUT = Path(r"C:\Users\vivi\hutter\work\agent7\identity_oracle.txt")

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
        if c == 0x0C:  # escape
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

def gamma_bits(n):
    # Elias gamma for n>=1
    if n < 1:
        n = 1
    b = n.bit_length()
    return 2 * b - 1

def unigram_bits(ids):
    from collections import Counter
    c = Counter(ids)
    n = len(ids)
    bits = 0.0
    for k, cnt in c.items():
        p = cnt / n
        bits += -cnt * math.log2(p)
    return bits

def pointer_oracle(ids):
    last = {}
    bits = 0.0
    first = 0
    second = 0
    V = 1 + max(ids) if ids else 1
    logV = math.log2(V)
    for i, w in enumerate(ids):
        if w not in last:
            bits += 1 + logV  # escape + uniform id
            first += 1
        else:
            gap = i - last[w]
            bits += 1 + gamma_bits(gap)  # flag + gamma
            second += 1
        last[w] = i
    return bits, first, second

def mixed_oracle(ids):
    from collections import Counter
    c = Counter(ids)
    n = len(ids)
    logp = {w: math.log2(n / cnt) for w, cnt in c.items()}
    last = {}
    bits_uni = 0.0
    bits_mix = 0.0
    wins = 0
    rare_save = 0.0
    rare_n = 0
    far_rare_save = 0.0
    far_rare_n = 0
    for i, w in enumerate(ids):
        u = logp[w]
        bits_uni += u
        if w not in last:
            bits_mix += u
        else:
            gap = i - last[w]
            p = 1 + gamma_bits(gap)
            if p < u:
                bits_mix += p
                wins += 1
                if c[w] <= 5:
                    rare_save += u - p
                    rare_n += 1
                    if gap > 256:
                        far_rare_save += u - p
                        far_rare_n += 1
            else:
                bits_mix += u
                if c[w] <= 5 and gap > 256:
                    far_rare_n += 1
        last[w] = i
    return bits_uni, bits_mix, wins, rare_save, rare_n, far_rare_save, far_rare_n

def freq_split(ids):
    from collections import Counter
    c = Counter(ids)
    last = {}
    buckets = {1: [0, 0, 0.0, 0.0],  # n, second, uni, mix
               5: [0, 0, 0.0, 0.0],
               20: [0, 0, 0.0, 0.0],
               10**9: [0, 0, 0.0, 0.0]}
    n = len(ids)
    logp = {w: math.log2(n / cnt) for w, cnt in c.items()}
    def bucket(cnt):
        if cnt == 1: return 1
        if cnt <= 5: return 5
        if cnt <= 20: return 20
        return 10**9
    for i, w in enumerate(ids):
        b = bucket(c[w])
        u = logp[w]
        buckets[b][0] += 1
        buckets[b][2] += u
        if w in last:
            buckets[b][1] += 1
            p = 1 + gamma_bits(i - last[w])
            buckets[b][3] += min(u, p)
        else:
            buckets[b][3] += u
        last[w] = i
    return buckets

def cache_k(ids, K):
    last = {}
    bits = 0.0
    hits = 0
    n = len(ids)
    from collections import Counter
    c = Counter(ids)
    logp = {w: math.log2(n / cnt) for w, cnt in c.items()}
    for i, w in enumerate(ids):
        if w in last and (i - last[w]) <= K:
            bits += 1 + gamma_bits(i - last[w])
            hits += 1
        else:
            bits += 1 + logp[w]
        last[w] = i
    return bits, hits

def main():
    byte_to_id, vocab = load_byte_to_id(DIC_PATH)
    stream = STREAM.read_bytes()
    ids = extract_ids(stream, byte_to_id)
    u = unigram_bits(ids)
    po, first, second = pointer_oracle(ids)
    uni, mix, wins, rare_save, rare_n, far_rare_save, far_rare_n = mixed_oracle(ids)
    lines = []
    lines.append(f"dic_bytes={len(stream)} vocab={vocab} tokens={len(ids)} first={first} second={second}")
    lines.append(f"unigram_bits={u:.0f} bpt={u/len(ids):.4f}")
    lines.append(f"unbounded_pointer_ALWAYS={po:.0f} bpt={po/len(ids):.4f} vs_uni={u-po:.0f}")
    lines.append(f"MIX min(uni,gamma) bits={mix:.0f} bpt={mix/len(ids):.4f} save={uni-mix:.0f} ({100*(uni-mix)/uni:.2f}% of unigram) pointer_wins={wins}")
    lines.append(f"rare<=5 pointer_wins n={rare_n} save_bits={rare_save:.0f}")
    lines.append(f"rare<=5 AND gap>256 pointer_wins n={far_rare_n} save_bits={far_rare_save:.0f}")
    buckets = freq_split(ids)
    for k, (nt, sec, ub, mb) in buckets.items():
        name = {1: "hapax", 5: "cnt2-5", 20: "cnt6-20", 10**9: "cnt>20"}[k]
        lines.append(f"bucket {name} n={nt} second={sec} uni_bpt={ub/nt if nt else 0:.3f} mix_bpt={mb/nt if nt else 0:.3f} save={ub-mb:.0f}")
    for K in (64, 256, 1024, 4096, 16384, 65536):
        b, hits = cache_k(ids, K)
        lines.append(f"K={K} FORCE-pointer-if-in-K bits={b:.0f} bpt={b/len(ids):.4f} hits={hits} hitrate={hits/len(ids):.3f} vs_uni={u-b:.0f}")
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
