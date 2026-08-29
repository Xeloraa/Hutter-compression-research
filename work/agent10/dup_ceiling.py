# Cross-page exact-duplicate ceiling on enwik8.3m (Class B for A4).
from collections import Counter
from pathlib import Path
import hashlib
import sys

ROOT = Path(r"C:\Users\vivi\hutter")
sys.path.insert(0, str(ROOT / "work" / "agent3"))
from page_stats import PAGE_RE, TEXT_RE, SRC

OUT = ROOT / "work" / "agent10" / "DUP_CEILING.md"


def main():
    raw = SRC.read_bytes()
    bodies = []
    lines = []
    for m in PAGE_RE.finditer(raw):
        xm = TEXT_RE.search(m.group(1))
        if not xm:
            continue
        text = xm.group(1)
        bodies.append(text)
        for line in text.split(b"\n"):
            line = line.strip()
            if len(line) >= 24:
                lines.append(line)
    extra_body = 0
    seen = set()
    for b in bodies:
        h = hashlib.md5(b).digest()
        if h in seen:
            extra_body += len(b)
        else:
            seen.add(h)
    extra_line = 0
    seenl = set()
    for l in lines:
        h = hashlib.md5(l).digest()
        if h in seenl:
            extra_line += len(l)
        else:
            seenl.add(h)
    file_n = len(raw)
    text = "\n".join(
        [
            "# Exact-duplicate ceiling (enwik8.3m pages, no codec)",
            "",
            f"pages_with_text={len(bodies)} long_lines(>=24B)={len(lines)}",
            f"duplicate_page_bodies extra_bytes={extra_body} ({100*extra_body/file_n:.3f}% of file)",
            f"duplicate_long_lines extra_bytes={extra_line} ({100*extra_line/file_n:.3f}% of file)",
            "",
            "This prefix is redirect-heavy (0.27% of bytes). Extra exact page bodies here are not a megabyte lever.",
            "At enwik9 the object to measure is the PHDA9 tail / infobox field tables (cmix-lex payload_lex), not 3 MB stubs.",
            "Do not run 3 MB fxcm on a duplicate-page reorder.",
        ]
    )
    OUT.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
