#!/usr/bin/env python3
"""PHDA9-lite tail split on enwik8 prefixes (20 / 30 / 100 MB).

Faithful to the *specified* parts of encode_txt_wit (delta page-id,
packed timestamp, stripped contributor), plus a lang/interwiki stream.
Not a byte-identical PHDA9/WRT run. Purpose: 10-30 MB protocol scale
curve for a second lex region, without cmix and without 3 MB fxcm.
"""
from __future__ import annotations

import json
import lzma
import math
import re
import zlib
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\vivi\hutter")
SRC = ROOT / "data" / "enwik8"
OUT_JSON = ROOT / "work" / "agent10" / "phda9_lite.json"

PAGE_RE = re.compile(rb"<page>(.*?)</page>", re.DOTALL)
TITLE_RE = re.compile(rb"<title>(.*?)</title>", re.DOTALL)
PAGE_ID_RE = re.compile(rb"<id>(\d+)</id>")
TS_RE = re.compile(rb"<timestamp>([^<]+)</timestamp>")
USER_RE = re.compile(rb"<username>(.*?)</username>", re.DOTALL)
IP_RE = re.compile(rb"<ip>(.*?)</ip>", re.DOTALL)
TEXT_RE = re.compile(rb"<text[^>]*>(.*?)</text>", re.DOTALL)
IW_LINE_RE = re.compile(
    rb"^\[\[([a-z]{2,3}|simple):([^\]]+)\]\]\s*$", re.I | re.M
)
LINK_FA_RE = re.compile(rb"\{\{\s*Link FA\|[^}]+\}\}", re.I)

PREFIXES = (20_000_000, 30_000_000, 100_000_000)


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


def lehmer_side(n: int) -> int:
    if n < 2:
        return 0
    return int(n * math.log2(n) / 8.0)


def pack_timestamp(ts: bytes) -> bytes:
    """PHDA9: timestamp>%02d%d:%d\\n with year-2001, month*31+day-32, hms."""
    raw = ts.decode("ascii", "replace").strip()
    try:
        dt = datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return b"timestamp>??\n"
    y = dt.year - 2001
    d = dt.month * 31 + dt.day - 32
    hms = dt.hour * 3600 + dt.minute * 60 + dt.second
    return f"timestamp>{y:02d}{d}:{hms}\n".encode("ascii")


def extract_lang(text: bytes) -> bytes:
    """Trailing interwiki + Link FA — proxy for henttail lang stream."""
    parts: list[bytes] = []
    for m in IW_LINE_RE.finditer(text):
        parts.append(m.group(0).strip())
    for m in LINK_FA_RE.finditer(text):
        parts.append(m.group(0).strip())
    return b"\n".join(parts)


def rank(orig: bytes, lex: bytes) -> dict:
    zo, zl = zlib9(orig), zlib9(lex)
    xo, xl = lzma6(orig), lzma6(lex)
    return {
        "raw": len(orig),
        "zlib9_orig": zo,
        "zlib9_lex": zl,
        "zlib9_delta": zo - zl,
        "lzma6_orig": xo,
        "lzma6_lex": xl,
        "lzma6_delta": xo - xl,
    }


def run_prefix(raw: bytes, nbytes: int) -> dict:
    chunk = raw[:nbytes]
    # Drop a truncated last page.
    pages = list(PAGE_RE.finditer(chunk))
    last_id = 0
    numeric_blocks: list[bytes] = []
    contrib_blocks: list[bytes] = []
    header_blocks: list[bytes] = []
    lang_blocks: list[bytes] = []
    n = 0
    for m in pages:
        blob = m.group(1)
        if not TITLE_RE.search(blob):
            continue
        im = PAGE_ID_RE.search(blob)
        if not im:
            continue
        cur = int(im.group(1))
        delta = cur - last_id
        last_id = cur
        tsm = TS_RE.search(blob)
        packed_ts = pack_timestamp(tsm.group(1)) if tsm else b""
        um = USER_RE.search(blob)
        ipm = IP_RE.search(blob)
        if um:
            who = b"username>" + um.group(1) + b"\n"
        elif ipm:
            who = b"ip>" + ipm.group(1) + b"\n"
        else:
            who = b""
        numeric = f">{delta}\n".encode("ascii") + packed_ts
        contrib = who
        numeric_blocks.append(numeric)
        contrib_blocks.append(contrib)
        header_blocks.append(numeric + contrib)
        xm = TEXT_RE.search(blob)
        lang_blocks.append(extract_lang(xm.group(1)) if xm else b"")
        n += 1

    def lex_join(blocks: list[bytes], keys: list[bytes]) -> tuple[bytes, bytes]:
        orig = b"".join(blocks)
        paired = list(zip(keys, blocks))
        lex = b"".join(b for _, b in sorted(paired, key=lambda x: x[0]))
        return orig, lex

    out: dict = {
        "prefix_bytes": nbytes,
        "complete_pages": n,
        "numeric_raw": sum(len(b) for b in numeric_blocks),
        "contrib_raw": sum(len(b) for b in contrib_blocks),
        "header_raw": sum(len(b) for b in header_blocks),
        "lang_raw": sum(len(b) for b in lang_blocks),
        "pages_with_lang": sum(1 for b in lang_blocks if b),
        "side_est": lehmer_side(n),
    }
    # r0 analog: lex numeric (should be weak / harmful — deltas)
    o, l = lex_join(numeric_blocks, numeric_blocks)
    out["numeric_lex"] = rank(o, l)
    # r1 analog: lex contributor payloads
    o, l = lex_join(contrib_blocks, contrib_blocks)
    out["contrib_lex"] = rank(o, l)
    # full header lex (what payload_lex roughly did)
    o, l = lex_join(header_blocks, contrib_blocks)
    out["header_lex_by_contrib"] = rank(o, l)
    # r2 analog: lex lang blocks
    keyed = [(b, b) for b in lang_blocks if b]
    if keyed:
        orig = b"\n".join(b for _, b in keyed) + b"\n"
        lex = b"\n".join(b for _, b in sorted(keyed)) + b"\n"
        out["lang_lex"] = rank(orig, lex)
        out["lang_blocks"] = len(keyed)
        out["lang_side_est"] = lehmer_side(len(keyed))
    else:
        out["lang_lex"] = rank(b"", b"")
        out["lang_blocks"] = 0
        out["lang_side_est"] = 0
    return out


def main() -> None:
    raw = SRC.read_bytes()
    rows = [run_prefix(raw, n) for n in PREFIXES]
    # Scale hints: 20->30, 30->100, and implied enwik9 x10 from 100 MB.
    def ratio(a: dict, b: dict, key: str) -> float | None:
        va, vb = a[key]["lzma6_delta"], b[key]["lzma6_delta"]
        if va == 0:
            return None
        return round(vb / va, 3)

    scale = {
        "pages_20_to_30": round(rows[1]["complete_pages"] / max(1, rows[0]["complete_pages"]), 3),
        "pages_30_to_100": round(rows[2]["complete_pages"] / max(1, rows[1]["complete_pages"]), 3),
        "contrib_lzma_20_to_30": ratio(rows[0], rows[1], "contrib_lex"),
        "contrib_lzma_30_to_100": ratio(rows[1], rows[2], "contrib_lex"),
        "lang_lzma_20_to_30": ratio(rows[0], rows[1], "lang_lex"),
        "lang_lzma_30_to_100": ratio(rows[1], rows[2], "lang_lex"),
        "numeric_lzma_30_to_100": ratio(rows[1], rows[2], "numeric_lex"),
    }
    # Linear enwik9 projection from 100 MB lzma delta * 10, minus 0.5*side.
    r100 = rows[2]
    proj = {}
    for name in ("numeric_lex", "contrib_lex", "header_lex_by_contrib", "lang_lex"):
        d = r100[name]["lzma6_delta"]
        z = r100[name]["zlib9_delta"]
        side = r100["side_est"] if name != "lang_lex" else r100["lang_side_est"]
        proj[name] = {
            "lzma_x10": d * 10,
            "zlib_x10": z * 10,
            "side_x20_articles": side * 20,
            "net_lzma_x10_minus_half_side20": d * 10 - (side * 20) // 2,
        }
    payload = {"rows": rows, "scale": scale, "enwik9_proj": proj}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("WROTE", OUT_JSON)
    for r in rows:
        print(
            "P",
            r["prefix_bytes"],
            "pages",
            r["complete_pages"],
            "num",
            r["numeric_lex"]["lzma6_delta"],
            "contrib",
            r["contrib_lex"]["lzma6_delta"],
            "lang",
            r["lang_lex"]["lzma6_delta"],
            "hdr",
            r["header_raw"],
            "langb",
            r["lang_raw"],
        )
    print("scale", scale)
    print("proj", proj)


if __name__ == "__main__":
    main()
