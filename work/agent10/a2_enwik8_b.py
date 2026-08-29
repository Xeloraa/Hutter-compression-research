#!/usr/bin/env python3
"""A2 follow-up: honest per-page link-list lex + long-line anatomy.

Global-sort of all wikilink titles is not a reversible payload_lex analog
(side data would be a permutation of ~800k tokens). Per-page lists are.
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
SRC = ROOT / "data" / "enwik8"
OUT = ROOT / "work" / "agent10" / "a2_enwik8_b.json"

PAGE_RE = re.compile(rb"<page>(.*?)</page>", re.DOTALL)
TEXT_RE = re.compile(rb"<text[^>]*>(.*?)</text>", re.DOTALL)
LINK_RE = re.compile(rb"\[\[([^\]|#]{1,200})(?:\|[^\]]*)?\]\]")

NS_SKIP = {
    b"file", b"image", b"category", b"wikipedia", b"template", b"help",
    b"portal", b"mediawiki", b"special", b"talk", b"user", b"wp", b"wt",
    b"cat", b"media", b"module",
}


def zlib9(data: bytes) -> int:
    return len(zlib.compress(data, 9)) if data else 0


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


def join_blocks(blocks: list[bytes]) -> bytes:
    return b"".join(b + b"\n" for b in blocks)


def main() -> None:
    t0 = time.time()
    raw = SRC.read_bytes()
    link_blocks: list[bytes] = []
    line_counter: Counter = Counter()
    xmlish = 0
    for m in PAGE_RE.finditer(raw):
        xm = TEXT_RE.search(m.group(1))
        if not xm:
            continue
        text = xm.group(1)
        titles: list[bytes] = []
        for tgt in LINK_RE.findall(text):
            low = tgt.strip().lower()
            if b":" in low:
                ns0 = low.split(b":", 1)[0]
                if ns0 in NS_SKIP:
                    continue
            if low.startswith(b"category:"):
                continue
            titles.append(low)
        if titles:
            # payload_lex analog: block = dump-order titles, sort key = the block
            link_blocks.append(b"\n".join(titles))
        for line in text.split(b"\n"):
            s = line.strip()
            if len(s) < 24:
                continue
            if s.startswith(b"<"):
                xmlish += 1
                continue
            line_counter[s] += 1

    orig = join_blocks(link_blocks)
    lex = join_blocks(sorted(link_blocks))
    z_o, z_l = zlib9(orig), zlib9(lex)
    x_o, x_l = lzma6(orig), lzma6(lex)

    extra_by_band = {"24-39": 0, "40-79": 0, "80-159": 0, "160+": 0}
    n_by_band = {"24-39": 0, "40-79": 0, "80-159": 0, "160+": 0}
    extra_total = 0
    top = []
    for s, c in line_counter.items():
        n = c
        extra = len(s) * (c - 1) if c > 1 else 0
        extra_total += extra
        L = len(s)
        if L < 40:
            band = "24-39"
        elif L < 80:
            band = "40-79"
        elif L < 160:
            band = "80-159"
        else:
            band = "160+"
        extra_by_band[band] += extra
        n_by_band[band] += n
        if extra:
            top.append((extra, c, L, s[:120]))
    top.sort(reverse=True)
    top20 = [
        {
            "extra": e,
            "count": c,
            "len": L,
            "preview": s.decode("utf-8", "replace"),
        }
        for e, c, L, s in top[:20]
    ]

    # Template-ish vs prose among duplicated lines (first extra-bearing).
    tmpl_extra = 0
    cat_extra = 0
    other_extra = 0
    for s, c in line_counter.items():
        if c < 2:
            continue
        extra = len(s) * (c - 1)
        st = s.lstrip()
        if st.startswith(b"{{") or st.startswith(b"*{{") or st.startswith(b"|"):
            tmpl_extra += extra
        elif st.lower().startswith(b"[[category:"):
            cat_extra += extra
        else:
            other_extra += extra

    out = {
        "elapsed_s": round(time.time() - t0, 2),
        "link_list_pages": len(link_blocks),
        "link_list_raw": len(orig),
        "zlib9_orig": z_o,
        "zlib9_lex": z_l,
        "zlib9_delta": z_o - z_l,
        "lzma6_orig": x_o,
        "lzma6_lex": x_l,
        "lzma6_delta": x_o - x_l,
        "long_line_extra_total": extra_total,
        "long_line_extra_by_band": extra_by_band,
        "long_line_n_by_band": n_by_band,
        "dup_line_extra_templateish": tmpl_extra,
        "dup_line_extra_category": cat_extra,
        "dup_line_extra_other": other_extra,
        "xmlish_skipped": xmlish,
        "top20_dup_lines": top20,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("WROTE", OUT)
    print(
        "link_lists",
        len(link_blocks),
        "zlib",
        z_o - z_l,
        "lzma",
        x_o - x_l,
        "raw",
        len(orig),
    )
    print("line_extra", extra_total, "tmpl", tmpl_extra, "cat", cat_extra, "other", other_extra)
    print("bands", extra_by_band)


if __name__ == "__main__":
    main()
