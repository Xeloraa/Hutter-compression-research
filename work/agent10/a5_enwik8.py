#!/usr/bin/env python3
"""A5 cheap falsification: typed body streams (URL / wiki-markup / prose).

Hypothesis. PHDA9 splits revision headers and a lang tail. The article
body stays a mixture of English, wiki punctuation, and URLs. Splitting or
tagging those types might expose homogeneity cmix-lex / fxcm_v26 does
not already get (v26 already sets HTLINK / template / table contexts).

Not A2 (payload_lex of per-page lists). Not A3 (aliases / columns).
Not A4 (title-index pointers). Not a 3 MB fxcm run.

Kill: expected enwik9 |ΔS| tens of KB after type-map metadata, WRT/DIC,
match windows, and fxcm type-context overlap.
"""
from __future__ import annotations

import gc
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
OUT_JSON = ROOT / "work" / "agent10" / "a5_enwik8.json"

PAGE_RE = re.compile(rb"<page>(.*?)</page>", re.DOTALL)
TEXT_RE = re.compile(rb"<text[^>]*>(.*?)</text>", re.DOTALL)
URL_RE = re.compile(rb"(?:https?|ftp)://[^\s\[\]<>\"']+", re.I)
HTML_RE = re.compile(rb"</?[A-Za-z][!A-Za-z0-9:_-][^>]{0,200}>")
WWW_RE = re.compile(rb"(?<![A-Za-z0-9])www\.[^\s\[\]<>\"']+", re.I)

PUNCT_SET = set(b"[]{}|=")  # A4.md byte-class
T_PROSE, T_URL, T_MARKUP = 0, 1, 2
MARK_URL, MARK_MK = 0x01, 0x02


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


def lcg_shuffle(n: int, seed: int = 1) -> list[int]:
    idx = list(range(n))
    for i in range(n - 1, 0, -1):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        j = seed % (i + 1)
        idx[i], idx[j] = idx[j], idx[i]
    return idx


def extra_spans(spans: list[bytes]) -> dict:
    c: Counter[bytes] = Counter(spans)
    n = sum(c.values())
    uniq = len(c)
    extra = 0
    for k, v in c.items():
        if v > 1:
            extra += len(k) * (v - 1)
    return {"n": n, "unique": uniq, "extra_copy_bytes": extra, "uniq_frac": (uniq / n if n else 0)}


def extra_from_ranges(body: bytes, spans: list[tuple[int, int]]) -> dict:
    """Uniqueness without retaining every span copy. Long spans keyed by md5+len."""
    c: Counter[tuple] = Counter()
    n = 0
    for a, b in spans:
        n += 1
        L = b - a
        if L <= 40:
            c[(0, body[a:b])] += 1
        else:
            c[(L, hashlib.md5(body[a:b]).digest())] += 1
    extra = 0
    for key, v in c.items():
        if v < 2:
            continue
        L = len(key[1]) if key[0] == 0 else key[0]
        extra += L * (v - 1)
    return {"n": n, "unique": len(c), "extra_copy_bytes": extra, "uniq_frac": (len(c) / n if n else 0)}


class CompCache:
    def __init__(self) -> None:
        self._z: dict[int, int] = {}
        self._x: dict[int, int] = {}

    def zlib(self, data: bytes) -> int:
        k = id(data)
        if k not in self._z:
            self._z[k] = zlib9(data)
        return self._z[k]

    def lzma(self, data: bytes) -> int:
        k = id(data)
        if k not in self._x:
            print(f"  lzma6 {len(data):,} B", flush=True)
            self._x[k] = lzma6(data)
        return self._x[k]


def ranking(label: str, orig: bytes, alt: bytes, cache: CompCache, do_lzma: bool) -> dict:
    z_o, z_l = cache.zlib(orig), cache.zlib(alt)
    row = {
        "label": label,
        "raw_orig": len(orig),
        "raw_alt": len(alt),
        "raw_delta": len(orig) - len(alt),
        "zlib9_orig": z_o,
        "zlib9_alt": z_l,
        "zlib9_delta": z_o - z_l,
    }
    if do_lzma:
        x_o, x_l = cache.lzma(orig), cache.lzma(alt)
        row["lzma6_orig"] = x_o
        row["lzma6_alt"] = x_l
        row["lzma6_delta"] = x_o - x_l
    return row


def sizes(label: str, data: bytes, cache: CompCache, do_lzma: bool) -> dict:
    row = {"label": label, "raw": len(data), "zlib9": cache.zlib(data)}
    if do_lzma:
        row["lzma6"] = cache.lzma(data)
    return row


def strip_url_trail(u: bytes) -> bytes:
    while u and u[-1] in b".,;:)]}'\"":
        u = u[:-1]
    return u


def find_nested(text: bytes, open_b: bytes, close_b: bytes) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    n = len(text)
    ol, cl = len(open_b), len(close_b)
    i = 0
    while True:
        j = text.find(open_b, i)
        if j < 0:
            break
        depth = 1
        p = j + ol
        while p < n and depth:
            a = text.find(open_b, p)
            b = text.find(close_b, p)
            if b < 0:
                p = n
                break
            if a >= 0 and a < b:
                depth += 1
                p = a + ol
            else:
                depth -= 1
                p = b + cl
        if depth == 0:
            spans.append((j, p))
            i = p
        else:
            i = j + ol
    return spans


def find_wikilinks(text: bytes) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    i = 0
    n = len(text)
    while True:
        j = text.find(b"[[", i)
        if j < 0:
            break
        k = text.find(b"]]", j + 2)
        if k < 0:
            break
        inner = text[j + 2 : k]
        if b"[[" in inner or (k - j) > 420 or not inner:
            i = j + 2
            continue
        spans.append((j, k + 2))
        i = k + 2
    return spans


def url_host(u: bytes) -> bytes:
    p = u.find(b"://")
    rest = u[p + 3 :] if p >= 0 else u
    slash = rest.find(b"/")
    host = rest[:slash] if slash >= 0 else rest
    hashp = host.find(b"#")
    if hashp >= 0:
        host = host[:hashp]
    return host.lower()


def paint(n: int, *groups: list[tuple[int, int]]) -> bytearray:
    types = bytearray(n)
    for spans in groups:
        for a, b in spans:
            if 0 <= a < b <= n:
                types[a:b] = b"\x02" * (b - a)
    return types


def collect_runs(body: bytes, types: bytearray) -> list[list[tuple[int, int]]]:
    runs: list[list[tuple[int, int]]] = [[], [], []]
    i = 0
    n = len(body)
    while i < n:
        t = types[i]
        j = i + 1
        while j < n and types[j] == t:
            j += 1
        runs[t].append((i, j))
        i = j
    return runs


def join_runs(body: bytes, runs: list[tuple[int, int]]) -> bytes:
    if not runs:
        return b""
    out = bytearray()
    for a, b in runs:
        out.extend(body[a:b])
    return bytes(out)


def join_runs_shuffled(body: bytes, runs: list[tuple[int, int]], seed: int) -> bytes:
    if not runs:
        return b""
    order = lcg_shuffle(len(runs), seed)
    out = bytearray()
    for i in order:
        a, b = runs[i]
        out.extend(body[a:b])
    return bytes(out)


def type_rle(types: bytearray) -> bytes:
    out = bytearray()
    i = 0
    n = len(types)
    while i < n:
        t = types[i]
        j = i + 1
        while j < n and types[j] == t:
            j += 1
        out.append(t)
        out.extend(uleb(j - i))
        i = j
    return bytes(out)


def extract_tail(body: bytes, types: bytearray) -> tuple[bytes, bytes, bytes]:
    marked = bytearray()
    url_side = bytearray()
    mk_side = bytearray()
    i = 0
    n = len(body)
    while i < n:
        t = types[i]
        j = i + 1
        while j < n and types[j] == t:
            j += 1
        if t == T_PROSE:
            marked.extend(body[i:j])
        else:
            span = body[i:j]
            if t == T_URL:
                marked.append(MARK_URL)
                url_side.extend(uleb(len(span)))
                url_side.extend(span)
            else:
                marked.append(MARK_MK)
                mk_side.extend(uleb(len(span)))
                mk_side.extend(span)
        i = j
    return bytes(marked), bytes(url_side), bytes(mk_side)


def tagged_inorder(body: bytes, types: bytearray) -> bytes:
    out = bytearray()
    i = 0
    n = len(body)
    while i < n:
        t = types[i]
        j = i + 1
        while j < n and types[j] == t:
            j += 1
        out.append(0x10 | t)
        out.extend(uleb(j - i))
        out.extend(body[i:j])
        i = j
    return bytes(out)


def punct_split(body: bytes) -> tuple[bytes, bytes, bytes]:
    punct = bytearray()
    rest = bytearray()
    rle = bytearray()
    i = 0
    n = len(body)
    while i < n:
        is_p = body[i] in PUNCT_SET
        j = i + 1
        while j < n and (body[j] in PUNCT_SET) == is_p:
            j += 1
        chunk = body[i:j]
        if is_p:
            punct.extend(chunk)
            rle.append(1)
        else:
            rest.extend(chunk)
            rle.append(0)
        rle.extend(uleb(j - i))
        i = j
    return bytes(punct), bytes(rest), bytes(rle)


def letter_stats(data: bytes, dic: set[bytes], longest: int) -> dict:
    n = len(data)
    i = 0
    letters = 0
    covered = 0
    leftover = 0
    other = 0
    dic_words = 0
    while i < n:
        c = data[i]
        if 65 <= c <= 90 or 97 <= c <= 122:
            j = i + 1
            while j < n and (65 <= data[j] <= 90 or 97 <= data[j] <= 122):
                j += 1
            run = data[i:j].lower()
            letters += len(run)
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
                    covered += found
                    dic_words += 1
                    p += found
                else:
                    leftover += 1
                    p += 1
            i = j
        else:
            other += 1
            i += 1
    return {
        "raw": n,
        "letters": letters,
        "other": other,
        "dic_covered": covered,
        "leftover_letters": leftover,
        "dic_words": dic_words,
        "letter_frac": (letters / n if n else 0),
        "cover_frac_of_letters": (covered / letters if letters else 0),
    }


def wrt_proxy(data: bytes, dic: set[bytes], longest: int, codes: dict[bytes, bytes]) -> bytes:
    """Optimistic WRT: 2 B/dic-word (stable id) + leftover letters + other as-is."""
    out = bytearray()
    n = len(data)
    i = 0
    while i < n:
        c = data[i]
        if 65 <= c <= 90 or 97 <= c <= 122:
            j = i + 1
            while j < n and (65 <= data[j] <= 90 or 97 <= data[j] <= 122):
                j += 1
            run = data[i:j].lower()
            p = 0
            rl = len(run)
            while p < rl:
                lim = longest if (rl - p) > longest else (rl - p)
                found = 0
                for L in range(lim, 0, -1):
                    w = run[p : p + L]
                    if w in dic:
                        found = L
                        if w not in codes:
                            k = len(codes)
                            codes[w] = bytes([0x80 | ((k >> 8) & 0x7F), k & 0xFF])
                        out.extend(codes[w])
                        break
                if found:
                    p += found
                else:
                    out.append(run[p])
                    p += 1
            i = j
        else:
            out.append(c)
            i += 1
    return bytes(out)


def residue_nonletters(data: bytes) -> bytes:
    return bytes(b for b in data if not (65 <= b <= 90 or 97 <= b <= 122))


def prefix_extra(spans: list[bytes], k: int) -> dict:
    c: Counter[bytes] = Counter()
    used = 0
    for s in spans:
        if len(s) >= k:
            c[s[:k]] += 1
            used += 1
    extra = sum(k * (v - 1) for v in c.values() if v > 1)
    return {"n_long_enough": used, "unique_prefixes": len(c), "extra_copy_bytes": extra}


def host_extra(urls: list[bytes]) -> dict:
    hosts: Counter[bytes] = Counter()
    pref: Counter[bytes] = Counter()
    for u in urls:
        h = url_host(u)
        hosts[h] += 1
        p = u.find(b"://")
        scheme = u[: p + 3] if p >= 0 else b""
        pref[scheme + h + b"/"] += 1
    h_extra = sum(len(k) * (v - 1) for k, v in hosts.items() if v > 1)
    p_extra = sum(len(k) * (v - 1) for k, v in pref.items() if v > 1)
    top = hosts.most_common(8)
    return {
        "unique_hosts": len(hosts),
        "host_extra_bytes": h_extra,
        "scheme_host_slash_extra": p_extra,
        "top_hosts": [{"host": h.decode("utf-8", "replace"), "n": v} for h, v in top],
    }


def gap_bands(spans: list[tuple[int, int]]) -> dict:
    bands = {
        "first": 0,
        "gap_le_32k": 0,
        "gap_32k_8m": 0,
        "gap_gt_8m": 0,
    }
    b_bytes = {k: 0 for k in bands}
    prev_end = None
    for a, b in spans:
        L = b - a
        if prev_end is None:
            bands["first"] += 1
            b_bytes["first"] += L
        else:
            gap = a - prev_end
            if gap <= 32_768:
                bands["gap_le_32k"] += 1
                b_bytes["gap_le_32k"] += L
            elif gap <= 8_388_608:
                bands["gap_32k_8m"] += 1
                b_bytes["gap_32k_8m"] += L
            else:
                bands["gap_gt_8m"] += 1
                b_bytes["gap_gt_8m"] += L
        prev_end = b
    return {"n": bands, "bytes": b_bytes}


def byte_shuffle(data: bytes, seed: int = 1) -> bytes:
    a = bytearray(data)
    n = len(a)
    for i in range(n - 1, 0, -1):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        j = seed % (i + 1)
        a[i], a[j] = a[j], a[i]
    return bytes(a)


def pack_rank(
    label: str,
    raw_orig: int,
    raw_alt: int,
    z_orig: int,
    z_alt: int,
    x_orig: int | None = None,
    x_alt: int | None = None,
) -> dict:
    row = {
        "label": label,
        "raw_orig": raw_orig,
        "raw_alt": raw_alt,
        "raw_delta": raw_orig - raw_alt,
        "zlib9_orig": z_orig,
        "zlib9_alt": z_alt,
        "zlib9_delta": z_orig - z_alt,
    }
    if x_orig is not None and x_alt is not None:
        row["lzma6_orig"] = x_orig
        row["lzma6_alt"] = x_alt
        row["lzma6_delta"] = x_orig - x_alt
    return row


def analyze(path: Path, dic: set[bytes], longest: int, do_lzma: bool) -> dict:
    t0 = time.time()
    raw = path.read_bytes()
    file_n = len(raw)
    digest = hashlib.md5(raw).hexdigest()

    texts: list[bytes] = []
    for m in PAGE_RE.finditer(raw):
        blob = m.group(1)
        xm = TEXT_RE.search(blob)
        if not xm:
            continue
        texts.append(xm.group(1))
    n_pages = len(texts)
    text_bytes = sum(len(t) for t in texts)
    del raw
    bodies = b"\n".join(texts)
    del texts
    gc.collect()

    url_spans: list[tuple[int, int]] = []
    url_strs: list[bytes] = []
    for m in URL_RE.finditer(bodies):
        a, b = m.start(), m.end()
        u = strip_url_trail(bodies[a:b])
        b = a + len(u)
        if b - a < 8:
            continue
        url_spans.append((a, b))
        url_strs.append(u)

    www_n = www_b = 0
    for m in WWW_RE.finditer(bodies):
        s = m.group(0)
        if s.lower().startswith(b"http"):
            continue
        www_n += 1
        www_b += len(s)

    tables = find_nested(bodies, b"{|", b"|}")
    templates = find_nested(bodies, b"{{", b"}}")
    links = find_wikilinks(bodies)
    html = [(m.start(), m.end()) for m in HTML_RE.finditer(bodies)]

    types = paint(len(bodies), tables, templates, links, html)
    for a, b in url_spans:
        types[a:b] = b"\x01" * (b - a)

    runs = collect_runs(bodies, types)
    url_cat = join_runs(bodies, runs[T_URL])
    mk_cat = join_runs(bodies, runs[T_MARKUP])
    prose_cat = join_runs(bodies, runs[T_PROSE])
    n_runs = sum(len(r) for r in runs)
    rle = type_rle(types)
    cache = CompCache()
    skip_tagged = len(bodies) > 10_000_000

    url_objs = extra_spans(url_strs)
    link_objs = extra_from_ranges(bodies, links)
    tpl_objs = extra_from_ranges(bodies, templates)
    tbl_objs = extra_from_ranges(bodies, tables)
    print(
        f"  bodies={len(bodies):,} url={len(url_cat):,} markup={len(mk_cat):,} "
        f"prose={len(prose_cat):,} urls={len(url_strs):,} links={len(links):,} "
        f"tpl={len(templates):,} tables={len(tables):,} runs={n_runs:,}",
        flush=True,
    )

    ranks: dict = {}
    streams: dict = {}

    marked, url_side, mk_side = extract_tail(bodies, types)
    extract_payload = marked + url_side + mk_side
    streams["extract_marked_body"] = {"label": "marked_prose_with_1B_holes", "raw": len(marked), "zlib9": zlib9(marked)}
    streams["extract_url_side"] = {"label": "url_length_prefixed_side", "raw": len(url_side), "zlib9": zlib9(url_side)}
    streams["extract_markup_side"] = {"label": "markup_length_prefixed_side", "raw": len(mk_side), "zlib9": zlib9(mk_side)}
    ranks["extract_to_tail"] = ranking(
        "phda9_analog_extract_url_markup_tails",
        bodies,
        extract_payload,
        cache,
        do_lzma and abs(zlib9(bodies) - zlib9(extract_payload)) >= 40_000,
    )
    del marked, url_side, mk_side, extract_payload
    gc.collect()

    if not skip_tagged:
        tagged = tagged_inorder(bodies, types)
        ranks["tagged_inorder"] = ranking(
            "inorder_type_tags_plus_payload", bodies, tagged, cache, False
        )
        del tagged
        gc.collect()

    punct, rest, punct_rle = punct_split(bodies)
    punct_payload = punct + rest + punct_rle
    punct_n = len(punct)
    streams["punct"] = {"label": "punct_[]{}|=", "raw": punct_n, "zlib9": zlib9(punct)}
    streams["punct_rle"] = {"label": "punct_rle", "raw": len(punct_rle), "zlib9": zlib9(punct_rle)}
    ranks["punct_byteclass"] = ranking(
        "punct_[]{}|=_plus_rest_plus_rle",
        bodies,
        punct_payload,
        cache,
        do_lzma and abs(zlib9(bodies) - zlib9(punct_payload)) >= 40_000,
    )
    del punct, rest, punct_rle, punct_payload
    gc.collect()

    del types
    gc.collect()

    z_mixed = cache.zlib(bodies)
    z_url = cache.zlib(url_cat)
    z_mk = cache.zlib(mk_cat)
    z_pr = cache.zlib(prose_cat)
    z_rle = cache.zlib(rle)
    z_sum = z_url + z_mk + z_pr + z_rle
    indep = {
        "zlib9_mixed": z_mixed,
        "zlib9_url": z_url,
        "zlib9_markup": z_mk,
        "zlib9_prose": z_pr,
        "zlib9_rle": z_rle,
        "zlib9_sum_typed_plus_rle": z_sum,
        "zlib9_delta_indep": z_mixed - z_sum,
    }
    if do_lzma:
        x_mixed = cache.lzma(bodies)
        x_url = cache.lzma(url_cat)
        x_mk = cache.lzma(mk_cat)
        x_pr = cache.lzma(prose_cat)
        x_rle = cache.lzma(rle)
        x_sum = x_url + x_mk + x_pr + x_rle
        indep.update(
            {
                "lzma6_mixed": x_mixed,
                "lzma6_url": x_url,
                "lzma6_markup": x_mk,
                "lzma6_prose": x_pr,
                "lzma6_rle": x_rle,
                "lzma6_sum_typed_plus_rle": x_sum,
                "lzma6_delta_indep": x_mixed - x_sum,
            }
        )
    else:
        x_mixed = None

    split_payload = url_cat + mk_cat + prose_cat + rle
    ranks["concat_plus_rle"] = ranking(
        "concat_typed_streams_plus_type_rle", bodies, split_payload, cache, do_lzma
    )
    z_split = cache.zlib(split_payload)
    x_split = cache.lzma(split_payload) if do_lzma else None
    del split_payload
    gc.collect()

    shuf_url = join_runs_shuffled(bodies, runs[T_URL], 1) if runs[T_URL] else b""
    ranks["url_live_vs_shuf"] = ranking(
        "url_concat_live_vs_span_shuffle", url_cat, shuf_url, cache, do_lzma
    )
    del shuf_url
    shuf_mk = join_runs_shuffled(bodies, runs[T_MARKUP], 2) if runs[T_MARKUP] else b""
    ranks["markup_live_vs_shuf"] = ranking(
        "markup_concat_live_vs_span_shuffle", mk_cat, shuf_mk, cache, do_lzma
    )
    del shuf_mk
    shuf_prose = join_runs_shuffled(bodies, runs[T_PROSE], 3) if runs[T_PROSE] else b""
    ranks["prose_live_vs_shuf"] = ranking(
        "prose_concat_live_vs_span_shuffle", prose_cat, shuf_prose, cache, do_lzma
    )
    del shuf_prose
    gc.collect()

    shuf_split = (
        join_runs_shuffled(bodies, runs[T_URL], 1)
        + join_runs_shuffled(bodies, runs[T_MARKUP], 2)
        + join_runs_shuffled(bodies, runs[T_PROSE], 3)
        + rle
    )
    z_shuf = zlib9(shuf_split)
    x_shuf = lzma6(shuf_split) if do_lzma else None
    ranks["span_shuffle_split"] = pack_rank(
        "typed_concat_live_vs_span_shuffle",
        len(url_cat) + len(mk_cat) + len(prose_cat) + len(rle),
        len(shuf_split),
        z_split,
        z_shuf,
        x_split,
        x_shuf,
    )
    del shuf_split
    gc.collect()

    codes: dict[bytes, bytes] = {}
    wrt_mixed = wrt_proxy(bodies, dic, longest, codes)
    wrt_split = (
        wrt_proxy(url_cat, dic, longest, codes)
        + wrt_proxy(mk_cat, dic, longest, codes)
        + wrt_proxy(prose_cat, dic, longest, codes)
    )
    ranks["wrt_proxy_split"] = ranking(
        "wrt_proxy_mixed_vs_typed_concat", wrt_mixed, wrt_split, cache, False
    )
    del wrt_mixed, wrt_split
    gc.collect()

    res_mixed = residue_nonletters(bodies)
    res_split = (
        residue_nonletters(url_cat)
        + residue_nonletters(mk_cat)
        + residue_nonletters(prose_cat)
    )
    ranks["nonletter_residue"] = ranking(
        "nonletter_mixed_vs_typed_concat",
        res_mixed,
        res_split,
        cache,
        do_lzma and abs(zlib9(res_mixed) - zlib9(res_split)) >= 20_000,
    )
    del res_mixed, res_split
    gc.collect()

    if len(url_cat) <= 4_000_000:
        url_bshuf = byte_shuffle(url_cat, 9)
        ranks["url_live_vs_byte_shuffle"] = ranking(
            "url_concat_live_vs_byte_shuffle", url_cat, url_bshuf, cache, False
        )
        del url_bshuf

    streams["url"] = sizes("url_concat", url_cat, cache, do_lzma)
    streams["markup"] = sizes("markup_concat", mk_cat, cache, do_lzma)
    streams["prose"] = sizes("prose_concat", prose_cat, cache, do_lzma)
    streams["type_rle"] = sizes("type_rle", rle, cache, do_lzma)

    census = {
        "pages": n_pages,
        "body_bytes": len(bodies),
        "xml_shell_est": file_n - text_bytes,
        "n_type_runs": n_runs,
        "n_url_runs": len(runs[T_URL]),
        "n_markup_runs": len(runs[T_MARKUP]),
        "n_prose_runs": len(runs[T_PROSE]),
        "mass": {
            "url": len(url_cat),
            "markup": len(mk_cat),
            "prose": len(prose_cat),
            "punct_byteclass": punct_n,
            "url_frac": len(url_cat) / len(bodies) if bodies else 0,
            "markup_frac": len(mk_cat) / len(bodies) if bodies else 0,
            "prose_frac": len(prose_cat) / len(bodies) if bodies else 0,
        },
        "spans": {
            "url": url_objs,
            "wikilink": link_objs,
            "template": tpl_objs,
            "table": tbl_objs,
            "html_tags": {"n": len(html), "bytes": sum(b - a for a, b in html)},
            "www_no_scheme": {"n": www_n, "bytes": www_b},
        },
        "url_prefix": {
            "p16": prefix_extra(url_strs, 16),
            "p24": prefix_extra(url_strs, 24),
            "p32": prefix_extra(url_strs, 32),
            "host": host_extra(url_strs),
        },
        "url_gaps": gap_bands(url_spans),
        "markup_span_counts": {
            "tables": len(tables),
            "templates": len(templates),
            "wikilinks": len(links),
            "html_tags": len(html),
        },
        "letter": {
            "url": letter_stats(url_cat, dic, longest),
            "markup": letter_stats(mk_cat, dic, longest),
            "prose": letter_stats(prose_cat, dic, longest),
            "bodies": letter_stats(bodies, dic, longest),
        },
        "skip_tagged": skip_tagged,
    }

    return {
        "path": str(path),
        "md5": digest,
        "file_bytes": file_n,
        "elapsed_s": round(time.time() - t0, 2),
        "census": census,
        "independent": indep,
        "streams": streams,
        "rankings": ranks,
    }


def main() -> None:
    if not DIC.exists():
        print("MISSING dic", DIC)
        sys.exit(1)
    dic, longest = load_dic(DIC)
    jobs: list[tuple[Path, bool]] = []
    p8 = ROOT / "data" / "enwik8"
    if p8.exists():
        jobs.append((p8, True))
    if not jobs:
        print("MISSING dumps")
        sys.exit(1)
    out = {"dic_words": len(dic), "dic_longest": longest, "slices": []}
    for path, do_lzma in jobs:
        print("analyze", path, "lzma", do_lzma, flush=True)
        r = analyze(path, dic, longest, do_lzma=do_lzma)
        out["slices"].append(r)
        print(
            json.dumps(
                {
                    "path": r["path"],
                    "file_bytes": r["file_bytes"],
                    "elapsed_s": r["elapsed_s"],
                    "mass": r["census"]["mass"],
                    "spans": r["census"]["spans"],
                    "independent": r["independent"],
                },
                indent=2,
            ),
            flush=True,
        )
        print("ranks", json.dumps(r["rankings"], indent=2), flush=True)
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote", OUT_JSON)


if __name__ == "__main__":
    main()
