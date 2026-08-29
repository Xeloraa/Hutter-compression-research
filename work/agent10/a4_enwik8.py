#!/usr/bin/env python3
"""A4 cheap falsification: title-indexed wikilinks (not A1/A2/A3, not mixer).

Hypothesis. PHDA9 packs headers/entities/brackets and does not extract
wikilinks. cmix-lex payload_lex does not reorder them. fxcm_v26 *parses*
[[ ]] for context but still spends bits on the target *string*. The dump
already contains every ns0 <title>. Replacing a resolved [[Target]] with
a varint into that in-band title table is a deterministic wiki relation
with S1≈0 (no shipped title dict).

Not E41 (OOV letter-run pointers into a rare-token dict).
Not A2 (payload_lex of per-page lists).
Not A3 (aliases / table columns / second WRT crumbs).

Kill: enwik9 |ΔS| tens of KB after WRT + match-window overlap.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import re
import sys
import time
import zlib
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\vivi\hutter")
DIC = ROOT / "locked" / "english.dic"
OUT_JSON = ROOT / "work" / "agent10" / "a4_enwik8.json"

PAGE_RE = re.compile(rb"<page>(.*?)</page>", re.DOTALL)
TITLE_RE = re.compile(rb"<title>(.*?)</title>", re.DOTALL)
TEXT_RE = re.compile(rb"<text[^>]*>(.*?)</text>", re.DOTALL)
NUM_ENT_RE = re.compile(rb"&#(\d{1,6});")
HEX_ENT_RE = re.compile(rb"&#x([0-9A-Fa-f]{1,6});")

NS_SKIP = {
    b"file",
    b"image",
    b"category",
    b"wikipedia",
    b"template",
    b"help",
    b"portal",
    b"mediawiki",
    b"special",
    b"talk",
    b"user",
    b"wp",
    b"wt",
    b"cat",
    b"media",
    b"module",
    b"draft",
    b"timedtext",
    b"image talk",
    b"user talk",
    b"wikipedia talk",
    b"template talk",
    b"help talk",
    b"category talk",
    b"portal talk",
    b"mediawiki talk",
}

LANG_OK = {
    b"aa", b"ab", b"af", b"ak", b"als", b"am", b"an", b"ar", b"as", b"ast",
    b"az", b"ba", b"be", b"bg", b"bh", b"bi", b"bn", b"bo", b"br", b"bs",
    b"ca", b"ce", b"ch", b"co", b"cs", b"cv", b"cy", b"da", b"de", b"dv",
    b"el", b"en", b"eo", b"es", b"et", b"eu", b"fa", b"fi", b"fo", b"fr",
    b"fy", b"ga", b"gd", b"gl", b"gn", b"gu", b"gv", b"ha", b"he", b"hi",
    b"hr", b"ht", b"hu", b"hy", b"ia", b"id", b"ie", b"io", b"is", b"it",
    b"ja", b"jv", b"ka", b"kk", b"kl", b"km", b"kn", b"ko", b"ku", b"kw",
    b"ky", b"la", b"lb", b"li", b"ln", b"lo", b"lt", b"lv", b"mg", b"mi",
    b"mk", b"ml", b"mn", b"mr", b"ms", b"mt", b"my", b"na", b"nah", b"nap",
    b"nds", b"ne", b"nl", b"nn", b"no", b"nv", b"ny", b"oc", b"om", b"or",
    b"os", b"pa", b"pl", b"pms", b"ps", b"pt", b"qu", b"rm", b"ro", b"ru",
    b"rw", b"sa", b"scn", b"sco", b"sd", b"se", b"sh", b"si", b"simple",
    b"sk", b"sl", b"sm", b"sn", b"so", b"sq", b"sr", b"ss", b"st", b"su",
    b"sv", b"sw", b"ta", b"te", b"tg", b"th", b"ti", b"tk", b"tl", b"tn",
    b"to", b"tpi", b"tr", b"ts", b"tt", b"tw", b"ug", b"uk", b"ur", b"uz",
    b"vi", b"vo", b"wa", b"wo", b"xh", b"yi", b"yo", b"za", b"zh", b"zu",
}

MARK = b"\x01"


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def zlib9(data: bytes) -> int:
    if not data:
        return 0
    return len(zlib.compress(data, 9))


def lzma6(data: bytes) -> int:
    if not data:
        return 0
    return len(
        lzma.compress(
            data,
            format=lzma.FORMAT_XZ,
            filters=[{"id": lzma.FILTER_LZMA2, "preset": 6}],
        )
    )


def uleb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def html_unescape(s: bytes) -> bytes:
    s = (
        s.replace(b"&amp;", b"&")
        .replace(b"&lt;", b"<")
        .replace(b"&gt;", b">")
        .replace(b"&quot;", b'"')
        .replace(b"&apos;", b"'")
    )

    def num(m: re.Match[bytes]) -> bytes:
        try:
            cp = int(m.group(1))
        except ValueError:
            return m.group(0)
        if 0 < cp < 0x110000:
            try:
                return chr(cp).encode("utf-8")
            except (ValueError, UnicodeEncodeError):
                return m.group(0)
        return m.group(0)

    def hexm(m: re.Match[bytes]) -> bytes:
        try:
            cp = int(m.group(1), 16)
        except ValueError:
            return m.group(0)
        if 0 < cp < 0x110000:
            try:
                return chr(cp).encode("utf-8")
            except (ValueError, UnicodeEncodeError):
                return m.group(0)
        return m.group(0)

    s = NUM_ENT_RE.sub(num, s)
    s = HEX_ENT_RE.sub(hexm, s)
    return s


def norm_title(t: bytes) -> bytes:
    t = html_unescape(t).replace(b"_", b" ")
    t = re.sub(rb" {2,}", b" ", t).strip()
    return t


def first_letter_fold(t: bytes) -> bytes:
    if not t:
        return t
    c = t[0:1]
    if 65 <= t[0] <= 90:
        return c.lower() + t[1:]
    if 97 <= t[0] <= 122:
        return c.upper() + t[1:]
    return t


def load_dic(path: Path) -> tuple[set[bytes], int]:
    words: set[bytes] = set()
    longest = 0
    for line in path.read_bytes().splitlines():
        w = line.strip().lower()
        if not w or not w.isalpha():
            continue
        words.add(w)
        if len(w) > longest:
            longest = len(w)
    return words, longest


def wrt_len(s: bytes, dic: set[bytes], longest: int) -> tuple[int, int, int]:
    """Optimistic WRT length: 2 B/dic-word (vocab>128) + 1 B leftover letter + 1 B other.

    Returns (encoded_len, dic_words, leftover_letters).
    """
    n = len(s)
    i = 0
    enc = 0
    nwords = 0
    leftover = 0
    while i < n:
        c = s[i]
        if 65 <= c <= 90 or 97 <= c <= 122:
            j = i + 1
            while j < n and (65 <= s[j] <= 90 or 97 <= s[j] <= 122):
                j += 1
            run = s[i:j].lower()
            p = 0
            rl = len(run)
            while p < rl:
                lim = longest if (rl - p) > longest else (rl - p)
                found = 0
                for L in range(lim, 0, -1):
                    if run[p : p + L] in dic:
                        found = L
                        break
                if found:
                    enc += 2
                    nwords += 1
                    p += found
                else:
                    enc += 1
                    leftover += 1
                    p += 1
            i = j
        else:
            enc += 1
            i += 1
    return enc, nwords, leftover


def classify_target(target: bytes) -> tuple[str, bytes]:
    """Return (kind, lookup_title). kind in article/special/interwiki."""
    t = target
    if t.startswith(b":"):
        t = t[1:]
    t = norm_title(t)
    if not t:
        return "empty", t
    if b":" in t:
        ns, rest = t.split(b":", 1)
        nsl = ns.strip().lower()
        rest = rest.strip()
        if nsl in LANG_OK:
            return "interwiki", t
        if nsl in NS_SKIP:
            return "special", t
    return "article", t


def iter_wikilinks(text: bytes):
    i = 0
    n = len(text)
    while True:
        j = text.find(b"[[", i)
        if j < 0:
            return
        k = text.find(b"]]", j + 2)
        if k < 0:
            return
        inner = text[j + 2 : k]
        if b"[[" in inner or len(inner) > 400 or not inner:
            i = j + 2
            continue
        pipe = inner.find(b"|")
        if pipe >= 0:
            tgt, disp = inner[:pipe], inner[pipe + 1 :]
        else:
            tgt, disp = inner, b""
        hashp = tgt.find(b"#")
        if hashp >= 0:
            frag = tgt[hashp:]
            tgt = tgt[:hashp]
        else:
            frag = b""
        yield {
            "abs0": j,
            "abs1": k + 2,
            "inner0": j + 2,
            "tgt": tgt,
            "disp": disp,
            "frag": frag,
            "inner": inner,
        }
        i = k + 2


def ranking(label: str, orig: bytes, alt: bytes) -> dict:
    z_o, z_l = zlib9(orig), zlib9(alt)
    x_o, x_l = lzma6(orig), lzma6(alt)
    return {
        "label": label,
        "raw_orig": len(orig),
        "raw_alt": len(alt),
        "raw_delta": len(orig) - len(alt),
        "zlib9_orig": z_o,
        "zlib9_alt": z_l,
        "zlib9_delta": z_o - z_l,
        "lzma6_orig": x_o,
        "lzma6_alt": x_l,
        "lzma6_delta": x_o - x_l,
    }


def analyze(path: Path, dic: set[bytes], longest: int, whole_lzma: bool) -> dict:
    t0 = time.time()
    raw = path.read_bytes()
    file_n = len(raw)
    digest = hashlib.md5(raw).hexdigest()

    pages = list(PAGE_RE.finditer(raw))
    titles: list[bytes] = []
    title_off: list[int] = []
    lookup: dict[bytes, int] = {}
    page_meta: list[tuple[int, int, bytes, bytes, int]] = []

    for i, m in enumerate(pages):
        blob = m.group(1)
        blob_abs = m.start(1)
        tm = TITLE_RE.search(blob)
        xm = TEXT_RE.search(blob)
        if not tm or not xm:
            continue
        nt = norm_title(tm.group(1))
        titles.append(nt)
        title_off.append(blob_abs + tm.start(1))
        idx = len(titles) - 1
        if nt not in lookup:
            lookup[nt] = idx
        folded = first_letter_fold(nt)
        if folded not in lookup:
            lookup[folded] = idx
        text = xm.group(1)
        text_abs = blob_abs + xm.start(1)
        page_meta.append((idx, blob_abs, nt, text, text_abs))

    n_pages = len(titles)
    shuf = list(range(n_pages))
    seed = 1
    for i in range(n_pages - 1, 0, -1):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        j = seed % (i + 1)
        shuf[i], shuf[j] = shuf[j], shuf[i]

    def resolve(nt: bytes) -> int | None:
        if nt in lookup:
            return lookup[nt]
        f = first_letter_fold(nt)
        if f in lookup:
            return lookup[f]
        return None

    n_links = 0
    n_article = n_special = n_iw = 0
    n_resolved = n_causal = n_dangling = 0
    bytes_tgt_all = bytes_resolved = bytes_causal = bytes_dangling = 0
    bytes_special = bytes_iw = bytes_disp = bytes_frag = 0
    gap_bands = {
        "future": 0,
        "gap_le_8m": 0,
        "gap_8_32m": 0,
        "gap_32_64m": 0,
        "gap_gt_64m": 0,
    }
    gap_bytes = {k: 0 for k in gap_bands}
    wrt_enc_resolved = wrt_words = wrt_left = 0
    ptr_len_resolved = 0
    n_ptr_beats_wrt = ptr_save_vs_wrt = 0
    n_ptr_beats_raw = ptr_save_vs_raw = 0
    n_in_dict_only = n_has_oov = 0
    lead_bold_n = lead_bold_b = 0
    replacements = []
    span_orig_parts = []
    span_alt_parts = []
    resolved_raw_parts = []
    resolved_ptr_parts = []
    resolved_ptr_shuf_parts = []
    dangling_targets = []
    n_selfpipe = 0
    n_empty = 0

    for page_idx, blob_abs, nt_page, text, text_abs in page_meta:
        head = text[:400]
        bold = b"'''" + nt_page + b"'''"
        if bold in head or b"'''" + first_letter_fold(nt_page) + b"'''" in head:
            # case-insensitive lead bold
            pass
        hl = head.lower()
        if (b"'''" + nt_page.lower() + b"'''") in hl:
            lead_bold_n += 1
            lead_bold_b += 6 + len(nt_page)

        for lk in iter_wikilinks(text):
            n_links += 1
            tgt = lk["tgt"]
            disp = lk["disp"]
            frag = lk["frag"]
            bytes_disp += len(disp)
            bytes_frag += len(frag)
            bytes_tgt_all += len(tgt)
            if disp and norm_title(disp) == norm_title(tgt):
                n_selfpipe += 1
            kind, nt = classify_target(tgt)
            span_orig = raw[text_abs + lk["abs0"] : text_abs + lk["abs1"]]
            tgt_abs0 = text_abs + lk["abs0"] + 2
            tgt_abs1 = tgt_abs0 + len(tgt)

            if kind == "empty":
                n_empty += 1
                span_orig_parts.append(span_orig)
                span_alt_parts.append(span_orig)
                continue
            if kind == "special":
                n_special += 1
                bytes_special += len(tgt)
                span_orig_parts.append(span_orig)
                span_alt_parts.append(span_orig)
                continue
            if kind == "interwiki":
                n_iw += 1
                bytes_iw += len(tgt)
                span_orig_parts.append(span_orig)
                span_alt_parts.append(span_orig)
                continue

            n_article += 1
            idx = resolve(nt)
            if idx is None:
                n_dangling += 1
                bytes_dangling += len(tgt)
                dangling_targets.append(nt)
                span_orig_parts.append(span_orig)
                span_alt_parts.append(span_orig)
                continue

            n_resolved += 1
            bytes_resolved += len(tgt)
            ptr = MARK + uleb(idx)
            ptr_len_resolved += len(ptr)
            wlen, nw, left = wrt_len(tgt, dic, longest)
            wrt_enc_resolved += wlen
            wrt_words += nw
            wrt_left += left
            if left == 0 and nw > 0:
                n_in_dict_only += 1
            else:
                n_has_oov += 1
            if len(ptr) < wlen:
                n_ptr_beats_wrt += 1
                ptr_save_vs_wrt += wlen - len(ptr)
            if len(ptr) < len(tgt):
                n_ptr_beats_raw += 1
                ptr_save_vs_raw += len(tgt) - len(ptr)

            if idx < page_idx:
                n_causal += 1
                bytes_causal += len(tgt)
            gap = text_abs + lk["abs0"] - title_off[idx]
            if gap < 0:
                gap_bands["future"] += 1
                gap_bytes["future"] += len(tgt)
            elif gap <= 8_000_000:
                gap_bands["gap_le_8m"] += 1
                gap_bytes["gap_le_8m"] += len(tgt)
            elif gap <= 32_000_000:
                gap_bands["gap_8_32m"] += 1
                gap_bytes["gap_8_32m"] += len(tgt)
            elif gap <= 64_000_000:
                gap_bands["gap_32_64m"] += 1
                gap_bytes["gap_32_64m"] += len(tgt)
            else:
                gap_bands["gap_gt_64m"] += 1
                gap_bytes["gap_gt_64m"] += len(tgt)

            replacements.append((tgt_abs0, tgt_abs1, ptr))
            new_span = span_orig[:2] + ptr + span_orig[2 + len(tgt) :]
            span_orig_parts.append(span_orig)
            span_alt_parts.append(new_span)
            resolved_raw_parts.append(tgt + b"\n")
            resolved_ptr_parts.append(ptr + b"\n")
            resolved_ptr_shuf_parts.append(MARK + uleb(shuf[idx]) + b"\n")

    # stitch whole-file transform
    replacements.sort()
    out = bytearray()
    prev = 0
    overlap_bad = 0
    for a, b, nb in replacements:
        if a < prev:
            overlap_bad += 1
            continue
        out.extend(raw[prev:a])
        out.extend(nb)
        prev = b
    out.extend(raw[prev:])
    transformed = bytes(out)

    span_orig = b"".join(span_orig_parts)
    span_alt = b"".join(span_alt_parts)
    res_raw = b"".join(resolved_raw_parts)
    res_ptr = b"".join(resolved_ptr_parts)
    res_shuf = b"".join(resolved_ptr_shuf_parts)

    dang_c = Counter(dangling_targets)
    dang_n, dang_u = sum(dang_c.values()), len(dang_c)
    dang_extra = sum(len(k) * (c - 1) for k, c in dang_c.items() if c > 1)

    ranks = {
        "link_spans": ranking("link_spans_resolved_targets_only_in_place", span_orig, span_alt),
        "resolved_targets": ranking("resolved_target_strings_vs_uleb", res_raw, res_ptr),
        "resolved_vs_shuffle": ranking("resolved_uleb_live_vs_shuffled_ids", res_ptr, res_shuf),
        "whole_zlib": {
            "label": "whole_file_title_index",
            "raw_orig": file_n,
            "raw_alt": len(transformed),
            "raw_delta": file_n - len(transformed),
            "zlib9_orig": zlib9(raw),
            "zlib9_alt": zlib9(transformed),
        },
    }
    ranks["whole_zlib"]["zlib9_delta"] = (
        ranks["whole_zlib"]["zlib9_orig"] - ranks["whole_zlib"]["zlib9_alt"]
    )
    if whole_lzma:
        ranks["whole_lzma"] = ranking("whole_file_title_index", raw, transformed)

    return {
        "path": str(path),
        "md5": digest,
        "file_bytes": file_n,
        "pages": n_pages,
        "elapsed_s": round(time.time() - t0, 2),
        "overlap_bad": overlap_bad,
        "links": {
            "n": n_links,
            "article": n_article,
            "special": n_special,
            "interwiki": n_iw,
            "empty": n_empty,
            "selfpipe": n_selfpipe,
            "resolved": n_resolved,
            "causal": n_causal,
            "dangling": n_dangling,
        },
        "target_bytes": {
            "all": bytes_tgt_all,
            "resolved": bytes_resolved,
            "causal": bytes_causal,
            "dangling": bytes_dangling,
            "special": bytes_special,
            "interwiki": bytes_iw,
            "disp": bytes_disp,
            "frag": bytes_frag,
        },
        "dangling_types": {"n": dang_n, "unique": dang_u, "extra_copy_bytes": dang_extra},
        "gap": {"n": gap_bands, "bytes": gap_bytes},
        "wrt_on_resolved": {
            "enc_len_2B_per_word": wrt_enc_resolved,
            "dic_words": wrt_words,
            "leftover_letters": wrt_left,
            "ptr_len": ptr_len_resolved,
            "n_ptr_beats_wrt": n_ptr_beats_wrt,
            "save_vs_wrt": ptr_save_vs_wrt,
            "n_ptr_beats_raw": n_ptr_beats_raw,
            "save_vs_raw": ptr_save_vs_raw,
            "n_fully_in_dict": n_in_dict_only,
            "n_has_oov_or_punct": n_has_oov,
        },
        "lead_bold": {"n": lead_bold_n, "bytes_incl_quotes": lead_bold_b},
        "rankings": ranks,
    }


def main() -> None:
    if not DIC.exists():
        print("MISSING dic", DIC)
        sys.exit(1)
    dic, longest = load_dic(DIC)
    jobs = []
    p3 = ROOT / "data" / "enwik8.3m"
    p8 = ROOT / "data" / "enwik8"
    if p3.exists():
        jobs.append((p3, False))
    if p8.exists():
        jobs.append((p8, False))
    if not jobs:
        print("MISSING dumps")
        sys.exit(1)
    out = {
        "dic_words": len(dic),
        "dic_longest": longest,
        "mark": "0x01+uleb(page_index)",
        "slices": [],
    }
    for path, do_lzma in jobs:
        print("analyze", path, flush=True)
        r = analyze(path, dic, longest, whole_lzma=do_lzma)
        out["slices"].append(r)
        print(json.dumps({k: r[k] for k in ("path", "file_bytes", "pages", "elapsed_s", "links", "target_bytes", "gap", "wrt_on_resolved", "lead_bold")}, indent=2))
        print("ranks", json.dumps(r["rankings"], indent=2), flush=True)
    # If enwik8 whole zlib Δ >= 80 KB, add whole-file lzma on that slice only.
    for i, r in enumerate(out["slices"]):
        if r["file_bytes"] >= 90_000_000:
            zdelta = r["rankings"]["whole_zlib"]["zlib9_delta"]
            print("enwik8 zlib delta", zdelta, flush=True)
            if zdelta >= 80_000 and "whole_lzma" not in r["rankings"]:
                print("running whole-file lzma6 (zlib Δ>=80KB)", flush=True)
                raw = Path(r["path"]).read_bytes()
                # rebuild transform from stored raw_alt size check: re-run analyze with lzma
                r2 = analyze(Path(r["path"]), dic, longest, whole_lzma=True)
                out["slices"][i] = r2
                print("whole lzma", r2["rankings"].get("whole_lzma"), flush=True)
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote", OUT_JSON)


if __name__ == "__main__":
    main()
