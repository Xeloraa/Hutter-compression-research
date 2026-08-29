#!/usr/bin/env python3
"""Page-level ordering diagnostics on enwik8.3m (complete pages only). No fxcm."""
from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\vivi\hutter")
SRC = ROOT / "data" / "enwik8.3m"
DIC = ROOT / "work" / "english.dic"
OUT_DIR = ROOT / "work" / "agent3"

PAGE_RE = re.compile(rb"<page>(.*?)</page>", re.DOTALL)
TITLE_RE = re.compile(rb"<title>(.*?)</title>", re.DOTALL)
ID_RE = re.compile(rb"<id>(\d+)</id>")
TEXT_RE = re.compile(rb"<text[^>]*>(.*?)</text>", re.DOTALL)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9']+|\[\[[^\]]+\]\]|\{\{[^}|]+")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9']+")
TEMPLATE_RE = re.compile(r"\{\{\s*([^}|{\n]+)")
LINK_RE = re.compile(r"\[\[([^\]|#]+)")
REDIR_RE = re.compile(r"#\s*redirect\s*\[\[([^\]|#]+)", re.I)

STOP = {
    "a", "an", "the", "of", "and", "or", "in", "on", "for", "to", "from",
    "by", "with", "at", "as", "is", "was", "are", "be", "it", "its", "this",
    "that", "list", "disambiguation", "wikipedia", "template", "category",
    "image", "file", "redirect", "r", "see", "also", "references",
}


def load_dic(path: Path) -> set[str]:
    words = set()
    raw = path.read_bytes()
    for line in raw.splitlines():
        w = line.strip().lower()
        if w:
            words.add(w.decode("ascii", "ignore"))
    return words


def norm_title(s: str) -> str:
    s = s.replace("_", " ").strip()
    return re.sub(r"\s+", " ", s)


def page_class(title: str, text: str) -> str:
    t = text.lstrip()
    if REDIR_RE.match(t) or t.lower().startswith("#redirect"):
        return "redirect"
    tl = title.lower()
    if "(disambiguation)" in tl or "{{disambig" in t.lower()[:800]:
        return "disambig"
    if tl.startswith("list of ") or tl.startswith("lists of "):
        return "list"
    if "{{" in t[:1200] and re.search(r"\{\{\s*infobox", t[:2000], re.I):
        return "infobox"
    return "article"


def first_template(text: str) -> str:
    m = TEMPLATE_RE.search(text)
    if not m:
        return ""
    name = m.group(1).strip().lower()
    name = re.sub(r"\s+", " ", name)
    # drop leading namespace-ish noise
    return name[:80]


def redir_target(text: str) -> str:
    m = REDIR_RE.search(text)
    if not m:
        return ""
    return norm_title(m.group(1))


def first_link(text: str, title: str) -> str:
    for m in LINK_RE.finditer(text):
        tgt = norm_title(m.group(1))
        if tgt.lower() != title.lower() and not tgt.lower().startswith("category:"):
            return tgt
    return ""


def tokens(s: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(s)]


def token_set(s: str) -> set[str]:
    return {w for w in tokens(s) if len(w) > 1}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def prefix_sim(a: str, b: str, n: int = 96) -> float:
    aa, bb = a[:n], b[:n]
    if not aa and not bb:
        return 1.0
    m = min(len(aa), len(bb))
    if m == 0:
        return 0.0
    same = sum(1 for i in range(m) if aa[i] == bb[i])
    return same / max(len(aa), len(bb), 1)


def mean(xs: list[float]) -> float:
    return float(sum(xs) / len(xs)) if xs else 0.0


def run_length_stats(labels: list[str]) -> dict:
    if not labels:
        return {"n_runs": 0, "mean_run": 0.0, "max_run": 0, "frac_in_run_ge2": 0.0}
    runs = []
    cur, n = labels[0], 1
    for x in labels[1:]:
        if x == cur:
            n += 1
        else:
            runs.append(n)
            cur, n = x, 1
    runs.append(n)
    ge2 = sum(r for r in runs if r >= 2)
    return {
        "n_runs": len(runs),
        "mean_run": round(mean([float(r) for r in runs]), 3),
        "max_run": max(runs),
        "frac_in_run_ge2": round(ge2 / len(labels), 4),
    }


def adjacent_metrics(pages: list[dict], order: list[int], dic: set[str]) -> dict:
    n = len(order)
    jac_all, jac_dic, jac_oov, jac_title, pref = [], [], [], [], []
    same_class = same_tgt = same_tpl = 0
    title_repeat = 0
    for i in range(n - 1):
        a, b = pages[order[i]], pages[order[i + 1]]
        ja = jaccard(a["tok"], b["tok"])
        jd = jaccard(a["tok_dic"], b["tok_dic"])
        jo = jaccard(a["tok_oov"], b["tok_oov"])
        jt = jaccard(a["title_tok"], b["title_tok"])
        jac_all.append(ja)
        jac_dic.append(jd)
        jac_oov.append(jo)
        jac_title.append(jt)
        pref.append(prefix_sim(a["text"], b["text"]))
        if a["cls"] == b["cls"]:
            same_class += 1
        if a["target"] and a["target"] == b["target"]:
            same_tgt += 1
        if a["tpl"] and a["tpl"] == b["tpl"]:
            same_tpl += 1
        if a["title_tok"] & b["title_tok"]:
            title_repeat += 1
    pairs = max(n - 1, 1)
    return {
        "mean_jaccard_body": round(mean(jac_all), 5),
        "mean_jaccard_in_dic": round(mean(jac_dic), 5),
        "mean_jaccard_oov": round(mean(jac_oov), 5),
        "mean_jaccard_title": round(mean(jac_title), 5),
        "mean_prefix96": round(mean(pref), 5),
        "frac_same_class": round(same_class / pairs, 4),
        "frac_same_redir_target": round(same_tgt / pairs, 4),
        "frac_same_template": round(same_tpl / pairs, 4),
        "frac_adj_shared_title_token": round(title_repeat / pairs, 4),
        "median_jaccard_body": round(float(statistics.median(jac_all)), 5) if jac_all else 0.0,
        "class_runs": run_length_stats([pages[i]["cls"] for i in order]),
        "redir_target_runs": run_length_stats(
            [pages[i]["target"] or f"__self_{pages[i]['id']}" for i in order]
        ),
        "template_runs": run_length_stats([pages[i]["tpl"] or f"__none_{pages[i]['id']}" for i in order]),
    }


def displacement(order: list[int]) -> dict:
    """How far pages move vs original index; block-preserving proxy."""
    n = len(order)
    pos = [0] * n
    for new_i, old_i in enumerate(order):
        pos[old_i] = new_i
    dist = [abs(pos[i] - i) for i in range(n)]
    # consecutive original ids that remain consecutive in new order
    keep = 0
    inv = {old: new for new, old in enumerate(order)}
    for i in range(n - 1):
        if inv[i + 1] == inv[i] + 1:
            keep += 1
    return {
        "mean_abs_index_shift": round(mean([float(d) for d in dist]), 2),
        "median_abs_index_shift": int(statistics.median(dist)) if dist else 0,
        "max_abs_index_shift": max(dist) if dist else 0,
        "frac_original_adjacencies_kept": round(keep / max(n - 1, 1), 4),
    }


def title_components(pages: list[dict]) -> list[int]:
    """Union-find on titles sharing a rare-ish content token (not lex sort)."""
    n = len(pages)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    bucket: dict[str, list[int]] = defaultdict(list)
    df = Counter()
    for i, p in enumerate(pages):
        for tok in p["title_tok"]:
            if tok in STOP or len(tok) < 4:
                continue
            df[tok] += 1
    # connect titles that share a token appearing in 2..12 titles (not global stop)
    for i, p in enumerate(pages):
        for tok in p["title_tok"]:
            if tok in STOP or len(tok) < 4:
                continue
            if 2 <= df[tok] <= 12:
                bucket[tok].append(i)
    for idxs in bucket.values():
        for j in range(1, len(idxs)):
            union(idxs[0], idxs[j])
    root_to_members: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        root_to_members[find(i)].append(i)
    # order: components by min original index (block-leaning), members by original index
    comps = sorted(root_to_members.values(), key=lambda m: (min(m), -len(m)))
    order = []
    for m in comps:
        order.extend(sorted(m))
    return order, {
        "n_components": len(comps),
        "n_nontrivial": sum(1 for m in comps if len(m) > 1),
        "largest": max(len(m) for m in comps),
        "mean_size": round(mean([float(len(m)) for m in comps]), 3),
        "pages_in_nontrivial": sum(len(m) for m in comps if len(m) > 1),
    }


def order_schema(pages: list[dict]) -> list[int]:
    rank = {"redirect": 0, "disambig": 1, "list": 2, "infobox": 3, "article": 4}
    return sorted(range(len(pages)), key=lambda i: (rank.get(pages[i]["cls"], 9), i))


def order_alias(pages: list[dict]) -> list[int]:
    """Bundle by redirect target; park bundle at target article's original index if present."""
    title_pos = {p["title_n"].lower(): i for i, p in enumerate(pages)}
    bundle_key = []
    for i, p in enumerate(pages):
        if p["cls"] == "redirect" and p["target"]:
            tgt = p["target"].lower()
            home = title_pos.get(tgt, i)
            bundle_key.append((home, 1 if p["cls"] == "redirect" else 0, i))
        else:
            bundle_key.append((i, 0, i))
    return [i for _, __, i in sorted(bundle_key)]


def order_template(pages: list[dict]) -> list[int]:
    return sorted(
        range(len(pages)),
        key=lambda i: (pages[i]["tpl"] == "", pages[i]["tpl"], i),
    )


def order_title_lex(pages: list[dict]) -> list[int]:
    return sorted(range(len(pages)), key=lambda i: pages[i]["title"].lower())


def order_hub(pages: list[dict]) -> list[int]:
    """Stable sort by first non-self wikilink; empty hubs keep original index."""
    return sorted(
        range(len(pages)),
        key=lambda i: (pages[i]["hub"] == "", pages[i]["hub"].lower(), i),
    )


def order_redir_target_within_schema(pages: list[dict]) -> list[int]:
    """Schema partition; redirects sorted by target, everything else original."""
    rank = {"redirect": 0, "disambig": 1, "list": 2, "infobox": 3, "article": 4}

    def key(i: int):
        p = pages[i]
        r = rank.get(p["cls"], 9)
        if p["cls"] == "redirect":
            return (r, p["target"].lower(), i)
        return (r, i)

    return sorted(range(len(pages)), key=key)


def main() -> None:
    raw = SRC.read_bytes()
    dic = load_dic(DIC)
    pages = []
    for m in PAGE_RE.finditer(raw):
        body = m.group(1)
        tm = TITLE_RE.search(body)
        im = ID_RE.search(body)
        xm = TEXT_RE.search(body)
        if not tm or not im:
            continue
        title = tm.group(1).decode("utf-8", "replace")
        pid = int(im.group(1))
        text = xm.group(1).decode("utf-8", "replace") if xm else ""
        # mediawiki XML entities that matter for markup detection
        text_plain = (
            text.replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&amp;", "&")
        )
        cls = page_class(title, text_plain)
        tok = token_set(text_plain)
        tok_dic = {t for t in tok if t in dic}
        tok_oov = tok - tok_dic
        title_tok = token_set(title)
        pages.append(
            {
                "title": title,
                "title_n": norm_title(title),
                "id": pid,
                "cls": cls,
                "target": redir_target(text_plain),
                "tpl": first_template(text_plain),
                "hub": first_link(text_plain, title),
                "tok": tok,
                "tok_dic": tok_dic,
                "tok_oov": tok_oov,
                "title_tok": title_tok,
                "text": text_plain,
                "nbytes": len(text_plain.encode("utf-8", "replace")),
            }
        )

    n = len(pages)
    ids = [p["id"] for p in pages]
    id_sorted = ids == sorted(ids)
    class_counts = Counter(p["cls"] for p in pages)
    redirs = [p for p in pages if p["cls"] == "redirect"]
    tgt_n = Counter(p["target"] for p in redirs if p["target"])
    tpl_n = Counter(p["tpl"] for p in pages if p["tpl"])
    multi_tgt = sum(1 for c in tgt_n.values() if c >= 2)
    pages_in_multi_tgt = sum(c for c in tgt_n.values() if c >= 2)

    cluster_order, cluster_info = title_components(pages)
    orders = {
        "original": list(range(n)),
        "title_lex_KILLED": order_title_lex(pages),
        "schema_stable": order_schema(pages),
        "alias_bundle": order_alias(pages),
        "first_template_stable": order_template(pages),
        "first_hub_stable": order_hub(pages),
        "schema_then_redir_target": order_redir_target_within_schema(pages),
        "title_token_clusters": cluster_order,
    }

    results = {}
    for name, order in orders.items():
        results[name] = {
            **adjacent_metrics(pages, order, dic),
            **displacement(order),
        }

    # examples for the writeup
    def titles_of(order: list[int], k: int = 12) -> list[str]:
        return [f"{pages[i]['cls']}:{pages[i]['title']}" for i in order[:k]]

    # redirect-run in original
    orig_cls = [p["cls"] for p in pages]
    redir_run = 0
    best = 0
    for c in orig_cls:
        if c == "redirect":
            redir_run += 1
            best = max(best, redir_run)
        else:
            redir_run = 0

    # Byte mass and article-only (non-redirect) locality — Jaccard on tiny
    # redirect pages is inflated by shared boilerplate and is not a bit budget.
    byte_mass = Counter()
    for p in pages:
        byte_mass[p["cls"]] += p["nbytes"]
    article_idx = [i for i, p in enumerate(pages) if p["cls"] != "redirect"]

    def restrict_order(full_order: list[int], keep: list[int]) -> list[int]:
        kset = set(keep)
        return [i for i in full_order if i in kset]

    article_pages = [pages[i] for i in article_idx]
    # remap: metrics function indexes into the list it is given
    art_results = {}
    keep = article_idx
    for name, order in orders.items():
        sub = restrict_order(order, keep)
        # build a view list in original page numbering by passing `pages` + sub
        art_results[name] = adjacent_metrics(pages, sub, dic)

    report = {
        "corpus": str(SRC),
        "file_bytes": len(raw),
        "complete_pages": n,
        "ids_strictly_ascending": id_sorted and n == len(set(ids)),
        "id_min": min(ids) if ids else None,
        "id_max": max(ids) if ids else None,
        "class_counts": dict(class_counts),
        "n_redirects": class_counts["redirect"],
        "n_redirect_targets": len(tgt_n),
        "targets_with_ge2_redirects": multi_tgt,
        "redirects_in_multi_target_bundles": pages_in_multi_tgt,
        "top_redirect_targets": tgt_n.most_common(8),
        "n_distinct_first_templates": len(tpl_n),
        "top_templates": tpl_n.most_common(12),
        "pages_with_template": sum(1 for p in pages if p["tpl"]),
        "mean_page_bytes": round(mean([float(p["nbytes"]) for p in pages]), 1),
        "median_page_bytes": int(statistics.median(p["nbytes"] for p in pages)) if pages else 0,
        "mean_redir_bytes": round(mean([float(p["nbytes"]) for p in redirs]), 1) if redirs else 0,
        "mean_article_bytes": round(
            mean([float(p["nbytes"]) for p in pages if p["cls"] == "article"]), 1
        ),
        "byte_mass_by_class": dict(byte_mass),
        "byte_mass_redirect_frac": round(
            byte_mass["redirect"] / max(sum(byte_mass.values()), 1), 4
        ),
        "n_nonredirect": len(article_idx),
        "article_only_orders": art_results,
        "original_max_redirect_run": best,
        "title_cluster": cluster_info,
        "orders": results,
        "head_original": titles_of(orders["original"]),
        "head_schema": titles_of(orders["schema_stable"]),
        "head_alias": titles_of(orders["alias_bundle"]),
        "head_template": titles_of(orders["first_template_stable"]),
        "head_titlelex": titles_of(orders["title_lex_KILLED"]),
        "note": (
            "Jaccard overlap is a locality proxy only. It is not a compression "
            "gain. E10 killed title-lex on DIC+fxcm26; in-dic Jaccard is the "
            "quantity DIC already globalizes."
        ),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "page_stats.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    # short tsv for humans
    lines = [
        "order\tjac_body\tjac_dic\tjac_oov\tjac_title\tprefix96\tsame_class\tsame_tgt\tsame_tpl\tkeep_adj\tmean_shift",
    ]
    for name, r in results.items():
        lines.append(
            "\t".join(
                [
                    name,
                    str(r["mean_jaccard_body"]),
                    str(r["mean_jaccard_in_dic"]),
                    str(r["mean_jaccard_oov"]),
                    str(r["mean_jaccard_title"]),
                    str(r["mean_prefix96"]),
                    str(r["frac_same_class"]),
                    str(r["frac_same_redir_target"]),
                    str(r["frac_same_template"]),
                    str(r["frac_original_adjacencies_kept"]),
                    str(r["mean_abs_index_shift"]),
                ]
            )
        )
    lines.append("")
    lines.append("# article_only (non-redirect pairs; ~99.73% of text bytes)")
    lines.append(
        "order\tjac_body\tjac_dic\tjac_oov\tjac_title\tprefix96\tsame_class\tsame_tpl"
    )
    for name, r in art_results.items():
        lines.append(
            "\t".join(
                [
                    name,
                    str(r["mean_jaccard_body"]),
                    str(r["mean_jaccard_in_dic"]),
                    str(r["mean_jaccard_oov"]),
                    str(r["mean_jaccard_title"]),
                    str(r["mean_prefix96"]),
                    str(r["frac_same_class"]),
                    str(r["frac_same_template"]),
                ]
            )
        )
    (OUT_DIR / "page_stats.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("pages", n, "classes", dict(class_counts), "byte_mass", dict(byte_mass))
    print("title_cluster", cluster_info)
    print("wrote", OUT_DIR / "page_stats.json")


if __name__ == "__main__":
    main()
