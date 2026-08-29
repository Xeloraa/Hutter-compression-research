#!/usr/bin/env python3
"""Fair A3 follow-up: same bytes, only layout. No markup deletion."""
from __future__ import annotations

import json
import lzma
import re
import zlib
from collections import defaultdict
from pathlib import Path

SRC = Path(r"C:\Users\vivi\hutter\data\enwik8")
OUT = Path(r"C:\Users\vivi\hutter\work\agent10\a3_fair.json")
PAGE_RE = re.compile(rb"<page>(.*?)</page>", re.DOTALL)
TEXT_RE = re.compile(rb"<text[^>]*>(.*?)</text>", re.DOTALL)


def zlib9(d: bytes) -> int:
    return len(zlib.compress(d, 9)) if d else 0


def lzma6(d: bytes) -> int:
    if not d:
        return 0
    return len(
        lzma.compress(
            d,
            format=lzma.FORMAT_XZ,
            filters=[{"id": lzma.FILTER_LZMA2, "preset": 6}],
        )
    )


def extract_wikitables(text: bytes) -> list[bytes]:
    out = []
    n = len(text)
    i = 0
    while True:
        j = text.find(b"{|", i)
        if j < 0:
            break
        p = j + 2
        end = -1
        while p < n - 1:
            if text[p] == 124 and text[p + 1] == 125:
                end = p + 2
                break
            p += 1
        if end < 0:
            i = j + 2
            continue
        out.append(text[j:end])
        i = end
    return out


def cells_of(blob: bytes) -> list[list[bytes]] | None:
    body = blob[2:]
    if body.endswith(b"|}"):
        body = body[:-2]
    rows = [r for r in re.split(rb"\|-", body) if r.strip()]
    if len(rows) < 3:
        return None
    parsed = []
    for row in rows[:80]:
        cells = re.split(rb"\|\||\n\|", row)
        cells = [c.strip() for c in cells if c.strip() and not c.strip().startswith(b"+")]
        if cells:
            parsed.append(cells[:20])
    if len(parsed) < 3:
        return None
    width = max(len(r) for r in parsed)
    if width < 2:
        return None
    return parsed


def brace_ibox(text: bytes) -> list[bytes]:
    out = []
    n = len(text)
    i = 0
    while True:
        j = text.find(b"{{", i)
        if j < 0:
            break
        k = j + 2
        while k < n and text[k] in b" \t":
            k += 1
        name_end = k
        while name_end < n and text[name_end] not in b"|{}\n":
            name_end += 1
        name = text[k:name_end].strip().lower().replace(b"_", b" ")
        if not (
            name == b"infobox"
            or name.startswith(b"infobox ")
            or name.startswith(b"taxobox")
            or name.startswith(b"geobox")
        ):
            i = j + 2
            continue
        depth = 1
        p = j + 2
        end = -1
        while p < n - 1:
            if text[p] == 123 and text[p + 1] == 123:
                depth += 1
                p += 2
                continue
            if text[p] == 125 and text[p + 1] == 125:
                depth -= 1
                p += 2
                if depth == 0:
                    end = p
                    break
                continue
            p += 1
        if end < 0:
            i = j + 2
            continue
        out.append(text[j:end])
        i = end
    return out


def ibox_vals(blob: bytes) -> list[tuple[bytes, bytes]]:
    body = blob[2:-2] if blob.startswith(b"{{") and blob.endswith(b"}}") else blob
    parts, depth, start, i, n = [], 0, 0, 0, len(body)
    while i < n:
        if i < n - 1 and body[i] == 123 and body[i + 1] == 123:
            depth += 1
            i += 2
            continue
        if i < n - 1 and body[i] == 125 and body[i + 1] == 125:
            depth = max(0, depth - 1)
            i += 2
            continue
        if body[i] == 124 and depth == 0:
            parts.append(body[start:i])
            start = i + 1
        i += 1
    parts.append(body[start:])
    pairs = []
    for part in parts[1:]:
        eq = part.find(b"=")
        if eq < 0:
            continue
        key = part[:eq].strip().lower().split(b"\n", 1)[0].strip()
        val = part[eq + 1 :].strip()
        if key and val:
            pairs.append((key, val))
    return pairs


def rank(label, a, b):
    return {
        "label": label,
        "raw": len(a),
        "same_bytes": len(a) == len(b),
        "zlib9_delta": zlib9(a) - zlib9(b),
        "lzma6_delta": lzma6(a) - lzma6(b),
        "zlib9_orig": zlib9(a),
        "lzma6_orig": lzma6(a),
    }


def main() -> None:
    raw = SRC.read_bytes()
    row_cells, col_cells = [], []
    n_tab = 0
    by_key = defaultdict(list)
    dump_vals = []
    for m in PAGE_RE.finditer(raw):
        xm = TEXT_RE.search(m.group(1))
        if not xm:
            continue
        text = xm.group(1)
        for t in extract_wikitables(text):
            parsed = cells_of(t)
            if not parsed:
                continue
            n_tab += 1
            width = max(len(r) for r in parsed)
            rows_pad = [r + [b""] * (width - len(r)) for r in parsed]
            row_cells.append(b"\n".join(b"\t".join(r) for r in rows_pad))
            cols = []
            for c in range(width):
                cols.append(b"\n".join(r[c] for r in rows_pad))
            col_cells.append(b"\n\n".join(cols))
        for ib in brace_ibox(text):
            for k, v in ibox_vals(ib):
                dump_vals.append(v)
                by_key[k].append(v)
    row_b = b"\n\n".join(row_cells)
    col_b = b"\n\n".join(col_cells)
    # same cell bytes: pad empties equally
    dump_v = b"\n".join(dump_vals)
    col_v = b"\n".join(v for k in sorted(by_key) for v in by_key[k])
    out = {
        "tables_parsed": n_tab,
        "table_fair": rank("table_cells_row_vs_col", row_b, col_b),
        "ibox_fair": rank("ibox_values_dump_vs_bykey", dump_v, col_v),
        "table_raw_row": len(row_b),
        "table_raw_col": len(col_b),
        "ibox_raw": len(dump_v),
        "ibox_col_raw": len(col_v),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
