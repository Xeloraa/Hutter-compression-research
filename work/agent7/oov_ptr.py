# Reversible OOV pointer on the DIC stream (len>=6, not in english.dic).
# Spec for a later C++ stage between dicprep and fxcm.
# MARK=0x05; MARK 0x00 = literal 0x05; MARK + uleb(rank>=1) = copy.
import math
from collections import OrderedDict
from pathlib import Path

ROOT = Path(r"C:\Users\vivi\hutter")
STREAM = ROOT / "data" / "enwik8.3m.dic"
DIC = ROOT / "work" / "english.dic"
if not DIC.exists():
    DIC = ROOT / "english.dic"
OUT_DIR = ROOT / "work" / "agent7"
MARK = 5
MIN_LEN = 6
K_ESCAPE = 0x0C


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


def skip_code(s, i):
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


def uleb_enc(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def uleb_dec(data, i):
    n = 0
    shift = 0
    while True:
        if i >= len(data):
            raise ValueError("uleb eof")
        b = data[i]
        i += 1
        n |= (b & 0x7F) << shift
        if b < 0x80:
            return n, i
        shift += 7


def lru_rank(lru, w):
    if w not in lru:
        return None
    rank = 0
    for key in reversed(lru):
        rank += 1
        if key == w:
            return rank
    return None


def lru_touch(lru, w, cap=None):
    if w in lru:
        lru.move_to_end(w)
    else:
        if cap and len(lru) >= cap:
            lru.popitem(last=False)
        lru[w] = 1


def encode(stream, dic_words, min_len=MIN_LEN, cap=None):
    out = bytearray()
    lru = OrderedDict()
    copies = 0
    first = 0
    i, n = 0, len(stream)
    while i < n:
        c = stream[i]
        if 97 <= c <= 122:
            j = i
            while j < n and 97 <= stream[j] <= 122:
                j += 1
            w = stream[i:j].decode("ascii")
            if (j - i) >= min_len and w not in dic_words:
                rank = lru_rank(lru, w)
                if rank is not None:
                    out.append(MARK)
                    out.extend(uleb_enc(rank))
                    lru_touch(lru, w, cap)
                    copies += 1
                    i = j
                    continue
                out.extend(stream[i:j])
                lru_touch(lru, w, cap)
                first += 1
                i = j
                continue
            out.extend(stream[i:j])
            i = j
            continue
        if c == MARK:
            out.append(MARK)
            out.append(0)
            i += 1
            continue
        if c >= 0x80 or c == K_ESCAPE:
            j = skip_code(stream, i)
            out.extend(stream[i:j])
            i = j
            continue
        out.append(c)
        i += 1
    return bytes(out), copies, first


def decode(data, dic_words, min_len=MIN_LEN, cap=None):
    out = bytearray()
    lru = OrderedDict()
    i, n = 0, len(data)
    while i < n:
        c = data[i]
        if c == MARK:
            if i + 1 >= n:
                raise ValueError("truncated MARK")
            if data[i + 1] == 0:
                out.append(MARK)
                i += 2
                continue
            rank, i = uleb_dec(data, i + 1)
            # map rank to word (1 = most recent)
            if rank < 1 or rank > len(lru):
                raise ValueError(f"bad rank {rank} size {len(lru)}")
            w = None
            r = 0
            for key in reversed(lru):
                r += 1
                if r == rank:
                    w = key
                    break
            out.extend(w.encode("ascii"))
            lru_touch(lru, w, cap)
            continue
        if 97 <= c <= 122:
            j = i
            while j < n and 97 <= data[j] <= 122:
                j += 1
            w = data[i:j].decode("ascii")
            out.extend(data[i:j])
            if (j - i) >= min_len and w not in dic_words:
                lru_touch(lru, w, cap)
            i = j
            continue
        if c >= 0x80 or c == K_ESCAPE:
            j = skip_code(data, i)
            out.extend(data[i:j])
            i = j
            continue
        out.append(c)
        i += 1
    return bytes(out)


def main():
    stream = STREAM.read_bytes()
    dic_words = load_dic_words(DIC)
    n_mark = stream.count(bytes([MARK]))
    lines = [f"input={len(stream)} MARK=0x{MARK:02x} already_present={n_mark} min_len={MIN_LEN}"]
    results = []
    for cap in (None, 256, 1024, 4096):
        enc, copies, first = encode(stream, dic_words, cap=cap)
        dec = decode(enc, dic_words, cap=cap)
        ok = dec == stream
        delta = len(stream) - len(enc)
        tag = "unbounded" if cap is None else f"K={cap}"
        lines.append(
            f"{tag} enc={len(enc)} delta={delta} copies={copies} first={first} roundtrip={'EXACT' if ok else 'FAIL'}"
        )
        results.append((tag, ok, delta, copies))
        if not ok:
            # first mismatch
            for k, (a, b) in enumerate(zip(stream, dec)):
                if a != b:
                    lines.append(f"  mismatch at {k} orig={a} dec={b}")
                    break
            if len(dec) != len(stream):
                lines.append(f"  len orig={len(stream)} dec={len(dec)}")
    text = "\n".join(lines) + "\n"
    (OUT_DIR / "OOV_PTR.md").write_text("# Reversible OOV pointer prototype\n\n" + text, encoding="utf-8")
    print(text)
    best = [r for r in results if r[1]]
    if best:
        tag, _, delta, copies = max(best, key=lambda x: x[2])
        lines2 = [
            f"Best exact transform: {tag} saves {delta} bytes of DIC input ({100*delta/len(stream):.3f}%).",
            "This is not an fxcm archive. Pipeline next: C++ stage, then DIC->ptr->fxcm vs DIC->fxcm.",
            "Kill if archive gain <100 B after same-compiler control.",
        ]
        with (OUT_DIR / "OOV_PTR.md").open("a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(lines2) + "\n")


if __name__ == "__main__":
    main()
