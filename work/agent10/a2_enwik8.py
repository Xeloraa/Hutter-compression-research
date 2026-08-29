#!/usr/bin/env python3
"""A2 cheap falsification on local enwik8 (100 MB official prefix).

No fxcm. No 3 MB DIC pipeline. Measures leftover structured reuse that
cmix-lex payload_lex did NOT take: they lex-sorted only regime 1 of the
post-WRT PHDA9 tail (D99/D86a per-article header blocks). PHDA9 itself
only extracts revision headers + a lang stream; infoboxes, categories,
and link lists stay in the main body.

Generic-compressor ranking is the E41 kill filter: if zlib9 and lzma6
both refuse a lex/reorder of a candidate stream, do not spend a
full-stack cmix-lex A/B on it.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import re
import sys
import time
import zlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\vivi\hutter")
SRC = ROOT / "data" / "enwik8"
OUT_MD = ROOT / "work" / "agent10" / "A2.md"
OUT_JSON = ROOT / "work" / "agent10" / "a2_enwik8.json"

PAGE_RE = re.compile(rb"<page>(.*?)</page>", re.DOTALL)
TITLE_RE = re.compile(rb"<title>(.*?)</title>", re.DOTALL)
TEXT_RE = re.compile(rb"<text[^>]*>(.*?)</text>", re.DOTALL)
USER_RE = re.compile(rb"<username>(.*?)</username>", re.DOTALL)
IP_RE = re.compile(rb"<ip>(.*?)</ip>", re.DOTALL)
TS_RE = re.compile(rb"<timestamp>(.*?)</timestamp>")
NS_RE = re.compile(rb"<ns>(.*?)</ns>")
CAT_RE = re.compile(rb"\[\[(?:Category|category):([^\]]+)\]\]")
# Interwiki-ish [[xx:Title]] / [[xxx:Title]], excluding common namespaces.
IW_RE = re.compile(
    rb"\[\[([a-z]{2,3}):([^\]]{1,200})\]\]"
)
LINK_RE = re.compile(rb"\[\[([^\]|#]{1,200})(?:\|[^\]]*)?\]\]")
REDIR_RE = re.compile(rb"#\s*REDIRECT\s*\[\[([^\]|#]+)", re.I)
CITE_RE = re.compile(rb"\{\{\s*(cite\s+[a-z]+|citation)[^}]*\}\}", re.I)

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
}

# 2006-era interwiki language codes (not exhaustive; false positives go here).
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

INFOBOX_NAMES = (b"infobox", b"taxobox", b"geobox", b"chembox", b"speciesbox")


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extra_dup_bytes(items: list[bytes]) -> tuple[int, int, int]:
    """Return (n, unique, extra_bytes of copies after first)."""
    seen: dict[bytes, int] = {}
    extra = 0
    for it in items:
        h = hashlib.md5(it).digest()
        if h in seen:
            extra += len(it)
        else:
            seen[h] = 1
    return len(items), len(seen), extra


def extra_counter_bytes(counter: Counter) -> tuple[int, int, int]:
    n = sum(counter.values())
    uniq = len(counter)
    extra = 0
    for k, c in counter.items():
        if c > 1:
            extra += len(k) * (c - 1)
    return n, uniq, extra


def zlib9(data: bytes) -> int:
    if not data:
        return 0
    return len(zlib.compress(data, 9))


def lzma6(data: bytes) -> int:
    if not data:
        return 0
    flt = lzma.FILTER_LZMA2
    return len(
        lzma.compress(
            data,
            format=lzma.FORMAT_XZ,
            filters=[{"id": flt, "preset": 6}],
        )
    )


def lehmer_side_est(n: int) -> int:
    """Rough uncompressed Lehmer-rank side bytes: n * log2(n) / 8."""
    if n < 2:
        return 0
    import math

    return int(n * math.log2(n) / 8.0)


def find_named_templates(text: bytes, name_prefixes: tuple[bytes, ...]) -> list[bytes]:
    """Brace-match {{Name ...}} where Name starts with one of the prefixes."""
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
        hit = False
        for p in name_prefixes:
            if name == p or name.startswith(p + b" ") or name.startswith(p + b"_"):
                hit = True
                break
        if not hit:
            i = j + 2
            continue
        depth = 1
        p = j + 2
        end = -1
        while p < n - 1:
            if text[p] == 123 and text[p + 1] == 123:  # {{
                depth += 1
                p += 2
                continue
            if text[p] == 125 and text[p + 1] == 125:  # }}
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


def infobox_skeleton_and_values(blob: bytes) -> tuple[bytes, bytes, list[tuple[bytes, bytes]]]:
    """Split |key=value lines. Nested braces inside values are kept raw."""
    body = blob[2:-2] if blob.startswith(b"{{") and blob.endswith(b"}}") else blob
    keys: list[bytes] = []
    vals: list[bytes] = []
    pairs: list[tuple[bytes, bytes]] = []
    # Split on | at depth 0 of {{ }}.
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
    for part in parts[1:]:  # skip template name
        eq = part.find(b"=")
        if eq < 0:
            continue
        key = part[:eq].strip().lower()
        val = part[eq + 1 :].strip()
        if not key or b"\n" in key:
            key = key.split(b"\n", 1)[0].strip()
        if not key:
            continue
        keys.append(key)
        vals.append(val)
        pairs.append((key, val))
    skel = b"|".join(keys)
    payload = b"\n".join(vals)
    return skel, payload, pairs


def page_class(title: bytes, text: bytes) -> str:
    t = text.lstrip()
    if REDIR_RE.match(t) or t.lower().startswith(b"#redirect"):
        return "redirect"
    tl = title.lower()
    if b"(disambiguation)" in tl:
        return "disambig"
    if tl.startswith(b"list of ") or tl.startswith(b"lists of "):
        return "list"
    if b"{{" in t[:2500] and re.search(rb"\{\{\s*infobox", t[:4000], re.I):
        return "infobox"
    return "article"


def join_blocks(blocks: list[bytes]) -> bytes:
    return b"".join(b + b"\n" for b in blocks)


def ranking(label: str, orig: bytes, lex: bytes) -> dict:
    z_o, z_l = zlib9(orig), zlib9(lex)
    x_o, x_l = lzma6(orig), lzma6(lex)
    return {
        "label": label,
        "raw_orig": len(orig),
        "raw_lex": len(lex),
        "zlib9_orig": z_o,
        "zlib9_lex": z_l,
        "zlib9_delta": z_o - z_l,
        "lzma6_orig": x_o,
        "lzma6_lex": x_l,
        "lzma6_delta": x_o - x_l,
        "both_gain": (z_o - z_l) > 0 and (x_o - x_l) > 0,
        "both_lose": (z_o - z_l) < 0 and (x_o - x_l) < 0,
    }


def main() -> None:
    t0 = time.time()
    if not SRC.exists():
        print("MISSING", SRC)
        sys.exit(1)
    digest = md5_file(SRC)
    raw = SRC.read_bytes()
    file_n = len(raw)
    pages = list(PAGE_RE.finditer(raw))

    bodies: list[bytes] = []
    long_lines: list[bytes] = []
    body_line_n = 0
    classes: Counter = Counter()
    class_bytes: Counter = Counter()

    cat_tokens: list[bytes] = []  # exact [[Category:...]] strings
    cat_sets: list[bytes] = []  # per-page sorted unique category titles
    cat_set_blocks: list[bytes] = []  # per-page concatenated category lines (orig order)
    iw_tokens: list[bytes] = []
    iw_blocks: list[bytes] = []
    user_tokens: list[bytes] = []
    ip_tokens: list[bytes] = []
    ts_tokens: list[bytes] = []
    link_targets: list[bytes] = []  # internal wiki titles, not cat/file
    exact_links: list[bytes] = []  # full [[...]] including pipe text
    infobox_blobs: list[bytes] = []
    infobox_skels: list[bytes] = []
    infobox_vals: list[bytes] = []
    infobox_field_vals: list[bytes] = []
    cite_blobs: list[bytes] = []
    redir_targets: list[bytes] = []
    header_blocks: list[bytes] = []  # PHDA9-like: ns + username + timestamp analog

    n_text = 0
    n_ns = 0
    n_user = 0
    infobox_page_bytes = 0
    cat_page_bytes = 0
    pages_with_cat = 0
    pages_with_iw = 0
    pages_with_ibox = 0

    for m in pages:
        blob = m.group(1)
        tm = TITLE_RE.search(blob)
        xm = TEXT_RE.search(blob)
        if not tm or not xm:
            continue
        title = tm.group(1)
        text = xm.group(1)
        n_text += 1
        cls = page_class(title, text)
        classes[cls] += 1
        class_bytes[cls] += len(text)
        bodies.append(text)

        um = USER_RE.search(blob)
        im = IP_RE.search(blob)
        tsm = TS_RE.search(blob)
        nsm = NS_RE.search(blob)
        user = um.group(1) if um else b""
        ip = im.group(1) if im else b""
        ts = tsm.group(1) if tsm else b""
        ns = nsm.group(1) if nsm else b""
        if user:
            user_tokens.append(user)
            n_user += 1
        if ip:
            ip_tokens.append(ip)
        if ts:
            ts_tokens.append(ts)
        if nsm:
            n_ns += 1
        # Cheap PHDA9-header analog: contributor identity + ns (not the article body).
        header_blocks.append(ns + b"\t" + user + b"\t" + ip + b"\t" + ts)

        if cls == "redirect":
            rm = REDIR_RE.search(text)
            if rm:
                redir_targets.append(rm.group(1).strip())

        for line in text.split(b"\n"):
            s = line.strip()
            if len(s) >= 24 and not s.startswith(b"<"):
                long_lines.append(s)
                body_line_n += 1

        cats = CAT_RE.findall(text)
        if cats:
            pages_with_cat += 1
            titles = []
            lines = []
            for c in cats:
                tok = c.strip()
                # drop sort key after |
                if b"|" in tok:
                    tok = tok.split(b"|", 1)[0].strip()
                cat_tokens.append(tok.lower())
                titles.append(tok.lower())
                lines.append(tok.lower())
            cat_sets.append(b"\n".join(sorted(set(titles))))
            cat_set_blocks.append(b"\n".join(lines))
            cat_page_bytes += sum(len(x) + 2 for x in lines)

        iws = []
        for lang, rest in IW_RE.findall(text):
            if lang in NS_SKIP or lang not in LANG_OK:
                continue
            # skip if it looks like a namespace we already excluded
            iws.append(lang + b":" + rest.split(b"|", 1)[0].strip())
        if iws:
            pages_with_iw += 1
            iw_tokens.extend(iws)
            iw_blocks.append(b"\n".join(iws))

        for tgt in LINK_RE.findall(text):
            low = tgt.strip().lower()
            if b":" in low:
                ns0 = low.split(b":", 1)[0]
                if ns0 in NS_SKIP or ns0 in LANG_OK:
                    continue
            if low.startswith(b"category:"):
                continue
            link_targets.append(low)

        for lm in re.finditer(rb"\[\[[^\]]{3,200}\]\]", text):
            s = lm.group(0)
            inner = s[2:-2]
            if inner.lower().startswith(b"category:"):
                continue
            exact_links.append(s)

        boxes = find_named_templates(text, INFOBOX_NAMES)
        if boxes:
            pages_with_ibox += 1
            infobox_page_bytes += sum(len(b) for b in boxes)
            for box in boxes:
                infobox_blobs.append(box)
                skel, payload, pairs = infobox_skeleton_and_values(box)
                if skel:
                    infobox_skels.append(skel)
                if payload:
                    infobox_vals.append(payload)
                for _k, v in pairs:
                    if len(v) >= 8:
                        infobox_field_vals.append(v)

        for cm in CITE_RE.finditer(text):
            cite_blobs.append(cm.group(0).strip())

    # --- exact dups ---
    n_body, u_body, extra_body = extra_dup_bytes(bodies)
    n_line, u_line, extra_line = extra_dup_bytes(long_lines)
    n_ibox, u_ibox, extra_ibox = extra_dup_bytes(infobox_blobs)
    n_cite, u_cite, extra_cite = extra_dup_bytes(cite_blobs)
    n_cat, u_cat, extra_cat = extra_counter_bytes(Counter(cat_tokens))
    n_iw, u_iw, extra_iw = extra_counter_bytes(Counter(iw_tokens))
    n_user_t, u_user, extra_user = extra_counter_bytes(Counter(user_tokens))
    n_ip, u_ip, extra_ip = extra_counter_bytes(Counter(ip_tokens))
    n_link, u_link, extra_link = extra_counter_bytes(Counter(link_targets))
    n_elink, u_elink, extra_elink = extra_counter_bytes(Counter(exact_links))
    n_skel, u_skel, extra_skel = extra_dup_bytes(infobox_skels)
    n_fval, u_fval, extra_fval = extra_counter_bytes(Counter(infobox_field_vals))
    n_redir, u_redir, extra_redir = extra_counter_bytes(Counter(redir_targets))
    n_hdr, u_hdr, extra_hdr = extra_dup_bytes(header_blocks)

    # Near-dup infobox: same skeleton, extra payload bytes on DF>=2 skeletons
    skel_payloads: dict[bytes, list[bytes]] = defaultdict(list)
    for box in infobox_blobs:
        skel, payload, _ = infobox_skeleton_and_values(box)
        if skel:
            skel_payloads[skel].append(payload)
    near_ibox_pages = 0
    near_ibox_payload = 0
    for skel, pays in skel_payloads.items():
        if len(pays) >= 2:
            near_ibox_pages += len(pays)
            near_ibox_payload += sum(len(p) for p in pays)

    # --- lex ranking (payload_lex analog) ---
    ranks: list[dict] = []

    if cat_set_blocks:
        keyed = list(zip(cat_sets, cat_set_blocks))
        orig = join_blocks([b for _, b in keyed])
        lex = join_blocks([b for _, b in sorted(keyed, key=lambda x: x[0])])
        r = ranking("category_lists_per_page", orig, lex)
        r["n_blocks"] = len(keyed)
        r["side_est"] = lehmer_side_est(len(keyed))
        ranks.append(r)

    if iw_blocks:
        keyed = [(b, b) for b in iw_blocks]
        orig = join_blocks([b for _, b in keyed])
        lex = join_blocks([b for _, b in sorted(keyed, key=lambda x: x[0])])
        r = ranking("interwiki_lists_per_page", orig, lex)
        r["n_blocks"] = len(keyed)
        r["side_est"] = lehmer_side_est(len(keyed))
        ranks.append(r)

    if infobox_blobs:
        keyed = []
        for box in infobox_blobs:
            skel, payload, _ = infobox_skeleton_and_values(box)
            keyed.append((skel + b"\0" + payload, box))
        orig = join_blocks([b for _, b in keyed])
        lex = join_blocks([b for _, b in sorted(keyed, key=lambda x: x[0])])
        r = ranking("infobox_blobs_payload_lex", orig, lex)
        r["n_blocks"] = len(keyed)
        r["side_est"] = lehmer_side_est(len(keyed))
        ranks.append(r)

    if header_blocks:
        keyed = list(enumerate(header_blocks))
        orig = join_blocks([b for _, b in keyed])
        # Sort by username then ip then timestamp — analog of D86a-visible + payload.
        lex = join_blocks(
            [b for _, b in sorted(keyed, key=lambda x: (x[1].split(b"\t")[1], x[1]))]
        )
        r = ranking("revision_header_contributor_lex", orig, lex)
        r["n_blocks"] = len(keyed)
        r["side_est"] = lehmer_side_est(len(keyed))
        ranks.append(r)

    if cite_blobs:
        keyed = [(b, b) for b in cite_blobs]
        orig = join_blocks([b for _, b in keyed])
        lex = join_blocks([b for _, b in sorted(keyed)])
        r = ranking("cite_templates_lex", orig, lex)
        r["n_blocks"] = len(keyed)
        r["side_est"] = lehmer_side_est(len(keyed))
        ranks.append(r)

    # Link-list per article (internal titles, sorted unique) — graph reuse.
    # Rebuild per-page from bodies would be a second pass; approximate with
    # a dump-order vs sorted-token stream of all internal targets.
    if link_targets:
        orig = b"\n".join(link_targets)
        lex = b"\n".join(sorted(link_targets))
        r = ranking("internal_link_targets_global_sort", orig, lex)
        r["n_blocks"] = len(link_targets)
        r["side_est"] = lehmer_side_est(n_text)  # would be per-page perm if extracted
        ranks.append(r)

    # Global category token sort (not per-page) — upper bound if we dumped a
    # single category stream.
    if cat_tokens:
        orig = b"\n".join(cat_tokens)
        lex = b"\n".join(sorted(cat_tokens))
        r = ranking("category_tokens_global_sort", orig, lex)
        r["n_blocks"] = len(cat_tokens)
        r["side_est"] = 0  # no perm if we just emit a sorted bag (not reversible without counts+map)
        ranks.append(r)

    elapsed = time.time() - t0

    summary = {
        "file": str(SRC),
        "md5": digest,
        "bytes": file_n,
        "complete_pages": n_text,
        "elapsed_s": round(elapsed, 2),
        "classes": dict(classes),
        "class_bytes": dict(class_bytes),
        "dups": {
            "page_bodies": {"n": n_body, "unique": u_body, "extra": extra_body},
            "long_lines_ge24": {"n": n_line, "unique": u_line, "extra": extra_line},
            "infobox_exact": {"n": n_ibox, "unique": u_ibox, "extra": extra_ibox},
            "cite_exact": {"n": n_cite, "unique": u_cite, "extra": extra_cite},
            "category_titles": {"n": n_cat, "unique": u_cat, "extra": extra_cat},
            "interwiki": {"n": n_iw, "unique": u_iw, "extra": extra_iw},
            "usernames": {"n": n_user_t, "unique": u_user, "extra": extra_user},
            "ips": {"n": n_ip, "unique": u_ip, "extra": extra_ip},
            "internal_link_titles": {"n": n_link, "unique": u_link, "extra": extra_link},
            "exact_wikilink_spans": {"n": n_elink, "unique": u_elink, "extra": extra_elink},
            "infobox_skeletons": {"n": n_skel, "unique": u_skel, "extra": extra_skel},
            "infobox_field_values_ge8": {"n": n_fval, "unique": u_fval, "extra": extra_fval},
            "redirect_targets": {"n": n_redir, "unique": u_redir, "extra": extra_redir},
            "revision_headers": {"n": n_hdr, "unique": u_hdr, "extra": extra_hdr},
        },
        "coverage": {
            "pages_with_category": pages_with_cat,
            "pages_with_interwiki": pages_with_iw,
            "pages_with_infobox_template": pages_with_ibox,
            "infobox_embedded_bytes": infobox_page_bytes,
            "category_embedded_bytes": cat_page_bytes,
            "near_dup_infobox_same_skeleton_n": near_ibox_pages,
            "near_dup_infobox_payload_bytes": near_ibox_payload,
            "ns_present": n_ns,
            "username_present": n_user,
        },
        "ranks": ranks,
        "notes": {
            "enwik9_articles_cmix_lex": 243425,
            "enwik9_tail_bytes": 45332670,
            "enwik9_r1_start": 13599801,
            "enwik9_r2_start": 30372888,
        },
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("WROTE", OUT_JSON)
    print("pages", n_text, "bytes", file_n, "s", round(elapsed, 2))
    print("extra_body", extra_body, "extra_line", extra_line)
    print("extra_cat", extra_cat, "extra_ibox", extra_ibox, "extra_user", extra_user)
    for r in ranks:
        print(
            r["label"],
            "zlib",
            r["zlib9_delta"],
            "lzma",
            r["lzma6_delta"],
            "raw",
            r["raw_orig"],
        )


if __name__ == "__main__":
    main()
