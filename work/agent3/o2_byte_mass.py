# Split O2 first-template mass: schema (infobox/taxobox/coor) vs hatnotes.
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(r"C:\Users\vivi\hutter")
sys.path.insert(0, str(ROOT / "work" / "agent3"))
from page_stats import PAGE_RE, TITLE_RE, TEXT_RE, first_template, page_class, SRC

OUT = ROOT / "work" / "agent3" / "O2_BYTES.md"

HAT = (
    "otheruses", "otheruses1", "spoiler", "wiktionary", "wikiquote",
    "redirect", "r from", "see also", "for", "distinguish", "about",
    "featured article", "main", "details", "further",
)
SCHEMA_PREFIX = ("infobox", "taxobox", "coor", "geobox", "speciesbox")


def kind(tpl: str) -> str:
    t = tpl.strip().lower()
    if any(t.startswith(p) or t.replace(" ", "_").startswith(p) for p in SCHEMA_PREFIX):
        return "schema"
    if any(t.startswith(h) for h in HAT):
        return "hatnote"
    return "other"


def main():
    raw = SRC.read_bytes()
    pages = []
    for m in PAGE_RE.finditer(raw):
        body = m.group(1)
        tm = TITLE_RE.search(body)
        xm = TEXT_RE.search(body)
        if not tm or not xm:
            continue
        title = tm.group(1).decode("utf-8", "replace")
        text = xm.group(1).decode("utf-8", "replace")
        nbytes = len(text.encode("utf-8", "replace"))
        tpl = first_template(text)
        pages.append({"nbytes": nbytes, "tpl": tpl, "cls": page_class(title, text), "kind": kind(tpl) if tpl else "empty"})

    file_n = 3000000
    bytes_all = sum(p["nbytes"] for p in pages)
    df = Counter(p["tpl"] for p in pages if p["tpl"])
    rep = {t for t, c in df.items() if c >= 2}

    def mass(pred):
        return sum(p["nbytes"] for p in pages if pred(p))

    schema_rep = mass(lambda p: p["kind"] == "schema" and p["tpl"] in rep)
    hat_rep = mass(lambda p: p["kind"] == "hatnote" and p["tpl"] in rep)
    other_rep = mass(lambda p: p["kind"] == "other" and p["tpl"] in rep)
    any_rep = mass(lambda p: p["tpl"] in rep)

    by_tpl = Counter()
    for p in pages:
        if p["tpl"]:
            by_tpl[p["tpl"]] += p["nbytes"]

    lines = [
        "# O2 first-template byte-mass gate (enwik8.3m, no fxcm)",
        "",
        f"pages={len(pages)} page_text_bytes={bytes_all}",
        f"repeating DF>=2 templates={len(rep)} bytes on those pages={any_rep} ({100*any_rep/file_n:.2f}% of file)",
        "",
        "## Split: schema vs hatnote (the 60% figure is not Taxobox)",
        f"- schema infobox/taxobox/coor repeating-class pages: {schema_rep} ({100*schema_rep/file_n:.2f}% of file)",
        f"- hatnote otheruses/spoiler/wiktionary/... repeating-class pages: {hat_rep} ({100*hat_rep/file_n:.2f}% of file)",
        f"- other repeating first-templates: {other_rep} ({100*other_rep/file_n:.2f}% of file)",
        "",
        "Grouping on first-template **including hatnotes** clumps unrelated articles that happen to start with {{otheruses}}. That is not schema locality.",
        "Modified O2: key = first infobox/taxobox/coor template, else empty, original index. Inverse still free via <id>.",
        "Kill unmodified O2 as a codec run. Keep schema-only O2 as the leftover ordering experiment (still no 3MB fxcm until 10MB).",
        "",
        "| template | kind | DF | page-text bytes | % of file |",
        "|---|---|---:|---:|---:|",
    ]
    for t, c in df.most_common(20):
        lines.append(f"| `{t}` | {kind(t)} | {c} | {by_tpl[t]} | {100*by_tpl[t]/file_n:.2f} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
