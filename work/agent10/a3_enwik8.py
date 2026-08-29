#!/usr/bin/env python3
"""A3 cheap falsification on local enwik8: not A2 lex, not LSTM hyperparams.

Measures dump-level reversible aliases, WRT-residual tokens after
english.dic, cross-article objects cmix-lex does not reorder, and hybrid
parsed-wiki fields (wikitable columns, infobox-by-key, coords, File:).

No fxcm. No 3 MB DIC pipeline. Not a record.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import math
import re
import sys
import time
import zlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\vivi\hutter")
SRC = ROOT / "data" / "enwik8"
DIC = ROOT / "locked" / "english.dic"
OUT_JSON = ROOT / "work" / "agent10" / "a3_enwik8.json"

PAGE_RE = re.compile(rb"<page>(.*?)</page>", re.DOTALL)
TITLE_RE = re.compile(rb"<title>(.*?)</title>", re.DOTALL)
TEXT_RE = re.compile(rb"<text[^>]*>(.*?)</text>", re.DOTALL)
REDIR_RE = re.compile(rb"#\s*REDIRECT\s*\[\[([^\]|#]+)", re.I)
FILE_RE = re.compile(rb"\[\[(?:File|Image|file|image):([^\]|#]+)", re.I)
ISBN_RE = re.compile(rb"ISBN[ \t]*([0-9][0-9\- ]{8,16}[0-9Xx])")
PMID_RE = re.compile(rb"PMID[ \t]*([0-9]{4,9})")
COORD_RE = re.compile(rb"\{\{\s*[Cc]oord\s*\|[^}]{0,400}\}\}")
DEFAULTSORT_RE = re.compile(rb"\{\{\s*(?:DEFAULTSORT|defaultsort):([^}]+)\}\}")
COMMENT_RE = re.compile(rb"<!--.*?-->", re.DOTALL)
SELFPIPE_RE = re.compile(rb"\[\[([^\]|#]{1,200})\|(\1)\]\]")
BR_RE = re.compile(rb"<br\s*/?\s*>", re.I)
NBSP_RE = re.compile(rb"&nbsp;|&#160;|&#xA0;", re.I)
AMP_NUM_RE = re.compile(rb"&#(\d{2,5});")
STUB_RE = re.compile(rb"\{\{\s*([^{}|]{0,60}stub)\s*\}\}", re.I)
NAV_NAME_RE = re.compile(
    rb"\{\{\s*((?:navbox|succession(?:[ _]box)?|sidebar)[^{}|]{0,80})",
    re.I,
)


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


def extra_counter_bytes(counter: Counter) -> tuple[int, int, int]:
    n = sum(counter.values())
    uniq = len(counter)
    extra = 0
    for k, c in counter.items():
        if c > 1:
            extra += len(k) * (c - 1)
    return n, uniq, extra


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


def wrt_cover(text: bytes, dic: set[bytes], longest: int) -> dict:
    """Greedy longest-match on a-z runs. Proxy for cmix WRT, not bit-exact."""
    n = len(text)
    i = 0
    letter_bytes = 0
    covered = 0
    leftover = Counter()
    leftover_bytes = 0
    hits = 0
    while i < n:
        c = text[i]
        if 97 <= c <= 122 or 65 <= c <= 90:
            j = i
            while j < n and (97 <= text[j] <= 122 or 65 <= text[j] <= 90):
                j += 1
            run = text[i:j].lower()
            letter_bytes += len(run)
            p = 0
            rl = len(run)
            while p < rl:
                matched = False
                lim = longest if (rl - p) > longest else (rl - p)
                for L in range(lim, 0, -1):
                    w = run[p : p + L]
                    if w in dic:
                        covered += L
                        hits += 1
                        p += L
                        matched = True
                        break
                if not matched:
                    leftover[run[p : p + 1]]  # noqa: keep 1-char skip
                    # take maximal leftover token
                    q = p + 1
                    while q < rl:
                        ok = False
                        lim2 = longest if (rl - q) > longest else (rl - q)
                        for L in range(lim2, 0, -1):
                            if run[q : p + (q - p) + L] in dic:
                                ok = True
                                break
                        # simpler: consume until a dic word can start
                        q += 1
                        if ok:
                            break
                    tok = run[p:]
                    leftover[tok] += 1
                    leftover_bytes += len(tok)
                    break
            i = j
        else:
            i += 1
    return {
        "letter_bytes": letter_bytes,
        "covered": covered,
        "hits": hits,
        "leftover_bytes": leftover_bytes,
        "leftover_types": len(leftover),
        "leftover_extra": extra_counter_bytes(leftover)[2],
        "leftover_top": leftover.most_common(15),
    }


def wrt_cover_fast(text: bytes, dic: set[bytes], longest: int) -> dict:
    """Per a-z run: longest prefix match, then whole-run leftover if none."""
    n = len(text)
    i = 0
    letter_bytes = 0
    covered = 0
    leftover: Counter = Counter()
    leftover_bytes = 0
    hits = 0
    while i < n:
        c = text[i]
        if 65 <= c <= 90 or 97 <= c <= 122:
            j = i + 1
            while j < n and (65 <= text[j] <= 90 or 97 <= text[j] <= 122):
                j += 1
            run = text[i:j].lower()
            letter_bytes += len(run)
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
                    hits += 1
                    p += found
                else:
                    leftover[run[p : p + 1]] += 1
                    leftover_bytes += 1
                    p += 1
            i = j
        else:
            i += 1
    ntok, uniq, extra = extra_counter_bytes(leftover)
    return {
        "letter_bytes": letter_bytes,
        "covered": covered,
        "cover_frac": (covered / letter_bytes) if letter_bytes else 0.0,
        "hits": hits,
        "leftover_bytes": leftover_bytes,
        "leftover_tokens": ntok,
        "leftover_types": uniq,
        "leftover_extra": extra,
        "leftover_top": [[w.decode("latin1", "replace"), c] for w, c in leftover.most_common(20)],
    }


def brace_templates(text: bytes, want) -> list[bytes]:
    """want(name_lower: bytes) -> bool. Brace-match {{...}}."""
    out: list[bytes] = []
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
        if not want(name):
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


def extract_wikitables(text: bytes) -> list[bytes]:
    out: list[bytes] = []
    n = len(text)
    i = 0
    while True:
        j = text.find(b"{|", i)
        if j < 0:
            break
        p = j + 2
        end = -1
        while p < n - 1:
            if text[p] == 123 and text[p + 1] == 124:  # nested {|
                # still search for |}
                p += 2
                continue
            if text[p] == 124 and text[p + 1] == 125:  # |}
                end = p + 2
                break
            p += 1
        if end < 0:
            i = j + 2
            continue
        out.append(text[j:end])
        i = end
    return out


def table_columns(blob: bytes) -> bytes | None:
    """Approximate column-major concat. Returns None if too irregular."""
    body = blob[2:]
    if body.endswith(b"|}"):
        body = body[:-2]
    rows = [r for r in re.split(rb"\|-", body) if r.strip()]
    if len(rows) < 3:
        return None
    parsed: list[list[bytes]] = []
    for row in rows[:80]:
        # cells: || or leading |
        cells = re.split(rb"\|\||\n\|", row)
        cells = [c.strip() for c in cells if c.strip() and not c.strip().startswith(b"+")]
        if cells:
            parsed.append(cells[:20])
    if len(parsed) < 3:
        return None
    width = max(len(r) for r in parsed)
    if width < 2:
        return None
    cols: list[bytes] = []
    for c in range(width):
        col = []
        for r in parsed:
            col.append(r[c] if c < len(r) else b"")
        cols.append(b"\n".join(col))
    return b"\n\n".join(cols)


def infobox_pairs(blob: bytes) -> list[tuple[bytes, bytes]]:
    body = blob[2:-2] if blob.startswith(b"{{") and blob.endswith(b"}}") else blob
    parts: list[bytes] = []
    depth = 0
    start = 0
    i = 0
    n = len(body)
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
    pairs: list[tuple[bytes, bytes]] = []
    for part in parts[1:]:
        eq = part.find(b"=")
        if eq < 0:
            continue
        key = part[:eq].strip().lower().split(b"\n", 1)[0].strip()
        val = part[eq + 1 :].strip()
        if key and val:
            pairs.append((key, val))
    return pairs


def ranking(label: str, orig: bytes, alt: bytes) -> dict:
    z_o, z_l = zlib9(orig), zlib9(alt)
    x_o, x_l = lzma6(orig), lzma6(alt)
    return {
        "label": label,
        "raw_orig": len(orig),
        "raw_alt": len(alt),
        "zlib9_orig": z_o,
        "zlib9_alt": z_l,
        "zlib9_delta": z_o - z_l,
        "lzma6_orig": x_o,
        "lzma6_alt": x_l,
        "lzma6_delta": x_o - x_l,
    }


def main() -> None:
    t0 = time.time()
    if not SRC.exists() or not DIC.exists():
        print("MISSING", SRC, DIC)
        sys.exit(1)
    digest = md5_file(SRC)
    raw = SRC.read_bytes()
    file_n = len(raw)
    dic, longest = load_dic(DIC)

    # Dump-level aliases on the whole file (cheap, includes XML).
    selfpipes = list(SELFPIPE_RE.finditer(raw))
    selfpipe_save = sum(1 + len(m.group(1)) for m in selfpipes)  # drop |X
    br_n = len(BR_RE.findall(raw))
    nbsp_n = len(NBSP_RE.findall(raw))
    comments = COMMENT_RE.findall(raw)
    comment_bytes = sum(len(c) for c in comments)
    comment_inner = sum(max(0, len(c) - 7) for c in comments)
    amp_nums = AMP_NUM_RE.findall(raw)
    # numeric entity vs utf-8: save roughly len('&#NNN;')-utf8len; bound as 4*n
    amp_num_save_bound = 0
    for m in amp_nums:
        try:
            cp = int(m)
        except ValueError:
            continue
        ent_len = 3 + len(str(cp).encode())  # &# + digits + ;
        if cp < 128:
            amp_num_save_bound += max(0, ent_len - 1)
        elif cp < 0x800:
            amp_num_save_bound += max(0, ent_len - 2)
        else:
            amp_num_save_bound += max(0, ent_len - 3)

    pages = list(PAGE_RE.finditer(raw))
    file_titles: list[bytes] = []
    nav_blobs: list[bytes] = []
    stub_names: list[bytes] = []
    defaultsorts: list[bytes] = []
    coords: list[bytes] = []
    isbns: list[bytes] = []
    pmids: list[bytes] = []
    tables: list[bytes] = []
    ibox_blobs: list[bytes] = []
    ibox_by_key: dict[bytes, list[bytes]] = defaultdict(list)
    ibox_pairs_dump: list[bytes] = []
    redir_n = 0
    redir_text = 0
    text_bytes = 0
    table_bytes = 0
    ibox_bytes = 0
    n_text = 0

    def want_ibox(name: bytes) -> bool:
        return (
            name == b"infobox"
            or name.startswith(b"infobox ")
            or name.startswith(b"taxobox")
            or name.startswith(b"geobox")
        )

    def want_nav(name: bytes) -> bool:
        return (
            name.startswith(b"navbox")
            or name.startswith(b"succession")
            or name.startswith(b"sidebar")
        )

    for m in pages:
        blob = m.group(1)
        tm = TITLE_RE.search(blob)
        xm = TEXT_RE.search(blob)
        if not tm or not xm:
            continue
        title = tm.group(1)
        text = xm.group(1)
        n_text += 1
        text_bytes += len(text)
        if REDIR_RE.search(text.lstrip()) or text.lstrip().lower().startswith(b"#redirect"):
            redir_n += 1
            redir_text += len(text)
        for fm in FILE_RE.finditer(text):
            file_titles.append(fm.group(1).strip().lower())
        for sm in STUB_RE.finditer(text):
            stub_names.append(sm.group(1).strip().lower())
        for dm in DEFAULTSORT_RE.finditer(text):
            defaultsorts.append(dm.group(1).strip())
        coords.extend(COORD_RE.findall(text))
        for im in ISBN_RE.finditer(text):
            isbns.append(re.sub(rb"[^0-9Xx]", b"", im.group(1)).upper())
        pmids.extend(PMID_RE.findall(text))
        tbs = extract_wikitables(text)
        tables.extend(tbs)
        table_bytes += sum(len(t) for t in tbs)
        nav_blobs.extend(brace_templates(text, want_nav))
        ibs = brace_templates(text, want_ibox)
        ibox_blobs.extend(ibs)
        ibox_bytes += sum(len(b) for b in ibs)
        for ib in ibs:
            for k, v in infobox_pairs(ib):
                if len(v) >= 2:
                    ibox_by_key[k].append(v)
                    ibox_pairs_dump.append(k + b"=" + v)

    wrt = wrt_cover_fast(raw, dic, longest)

    file_n2, file_u, file_extra = extra_counter_bytes(Counter(file_titles))
    nav_n, nav_u, nav_extra = extra_counter_bytes(Counter(nav_blobs))
    stub_n, stub_u, stub_extra = extra_counter_bytes(Counter(stub_names))
    ds_n, ds_u, ds_extra = extra_counter_bytes(Counter(defaultsorts))
    co_n, co_u, co_extra = extra_counter_bytes(Counter(coords))
    isbn_n, isbn_u, isbn_extra = extra_counter_bytes(Counter(isbns))
    pmid_n, pmid_u, pmid_extra = extra_counter_bytes(Counter(pmids))
    tb_n, tb_u, tb_extra = extra_counter_bytes(Counter(tables))
    comment_n, comment_u, comment_extra = extra_counter_bytes(Counter(comments))

    # Hybrid: infobox values grouped by key vs dump-order pairs.
    keys_sorted = sorted(ibox_by_key.keys(), key=lambda k: -sum(len(v) for v in ibox_by_key[k]))
    col_parts = []
    for k in keys_sorted:
        col_parts.append(k + b"\n" + b"\n".join(ibox_by_key[k]))
    ibox_col = b"\n\n".join(col_parts)
    ibox_dump = b"\n".join(ibox_pairs_dump)
    rank_ibox = ranking("infobox_values_by_key", ibox_dump, ibox_col)

    # Wikitables: original concat vs column-major where parseable.
    tab_orig = b"".join(t + b"\n" for t in tables)
    col_ok = []
    col_fail = 0
    for t in tables:
        c = table_columns(t)
        if c is None:
            col_fail += 1
            col_ok.append(t)
        else:
            col_ok.append(c)
    tab_col = b"".join(t + b"\n" for t in col_ok)
    rank_tab = ranking("wikitable_columns", tab_orig, tab_col)

    # File titles: dump-order vs sorted unique+payload (bag, not reversible).
    file_dump = b"\n".join(file_titles)
    file_sorted = b"\n".join(sorted(file_titles))
    rank_file = ranking("file_titles_sort", file_dump, file_sorted)

    # Coord dump vs sort.
    coord_dump = b"\n".join(coords)
    coord_sorted = b"\n".join(sorted(coords))
    rank_coord = ranking("coord_sort", coord_dump, coord_sorted)

    # Navboxes dump vs sort exact blobs.
    nav_dump = b"".join(b + b"\n" for b in nav_blobs)
    nav_sorted = b"".join(b + b"\n" for b in sorted(nav_blobs))
    rank_nav = ranking("navbox_sort", nav_dump, nav_sorted)

    # Alias rewrite of <text> only: self-pipe + br collapse + nbsp->utf8.
    def alias_rewrite(t: bytes) -> bytes:
        t2 = SELFPIPE_RE.sub(rb"[[\1]]", t)
        t2 = BR_RE.sub(b"<br>", t2)
        t2 = NBSP_RE.sub(b"\xc2\xa0", t2)
        return t2

    # Sample alias on concatenated texts would need a second pass; bound with
    # whole-file rewrite (includes XML, slightly optimistic).
    aliased = alias_rewrite(raw)
    alias_raw_save = file_n - len(aliased)
    rank_alias = ranking("whole_dump_alias", raw, aliased)

    # Comments stripped (not reversible without a side stream).
    no_comments = COMMENT_RE.sub(b"", raw)
    rank_comment = ranking("strip_comments_irreversible", raw, no_comments)

    results = {
        "md5": digest,
        "file_bytes": file_n,
        "pages_with_text": n_text,
        "text_bytes": text_bytes,
        "dic_words": len(dic),
        "dic_longest": longest,
        "elapsed_s": round(time.time() - t0, 2),
        "aliases": {
            "selfpipe_n": len(selfpipes),
            "selfpipe_save_bytes": selfpipe_save,
            "br_n": br_n,
            "nbsp_entity_n": nbsp_n,
            "nbsp_save_if_utf8": nbsp_n * 4,  # &nbsp; 6 vs C2 A0
            "amp_numeric_n": len(amp_nums),
            "amp_numeric_save_bound": amp_num_save_bound,
            "alias_raw_save": alias_raw_save,
            "comment_n": len(comments),
            "comment_bytes": comment_bytes,
            "comment_inner": comment_inner,
            "comment_extra": comment_extra,
        },
        "wrt_residual": wrt,
        "cross_article": {
            "redirects": {"n": redir_n, "text_bytes": redir_text},
            "file_titles": {"n": file_n2, "unique": file_u, "extra": file_extra},
            "nav_templates": {"n": nav_n, "unique": nav_u, "extra": nav_extra},
            "stubs": {"n": stub_n, "unique": stub_u, "extra": stub_extra},
            "defaultsort": {"n": ds_n, "unique": ds_u, "extra": ds_extra},
            "coord": {"n": co_n, "unique": co_u, "extra": co_extra},
            "isbn": {"n": isbn_n, "unique": isbn_u, "extra": isbn_extra},
            "pmid": {"n": pmid_n, "unique": pmid_u, "extra": pmid_extra},
            "wikitables": {
                "n": tb_n,
                "unique": tb_u,
                "extra": tb_extra,
                "bytes": table_bytes,
                "col_fail": col_fail,
            },
            "infobox": {
                "n": len(ibox_blobs),
                "bytes": ibox_bytes,
                "field_keys": len(ibox_by_key),
                "field_pairs": len(ibox_pairs_dump),
            },
        },
        "rankings": {
            "alias": rank_alias,
            "comments": rank_comment,
            "infobox_by_key": rank_ibox,
            "wikitable_columns": rank_tab,
            "file_titles": rank_file,
            "coord": rank_coord,
            "navbox": rank_nav,
        },
    }
    OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({k: results[k] for k in ("md5", "file_bytes", "elapsed_s", "aliases")}, indent=2))
    print("wrt", {k: wrt[k] for k in wrt if k != "leftover_top"})
    print("cross", results["cross_article"])
    print("rank alias", rank_alias)
    print("rank ibox", rank_ibox)
    print("rank tab", rank_tab)
    print("rank file", rank_file)
    print("rank coord", rank_coord)
    print("rank nav", rank_nav)
    print("rank comments", rank_comment)
    print("wrote", OUT_JSON)


if __name__ == "__main__":
    main()
