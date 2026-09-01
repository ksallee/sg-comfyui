"""Regenerate probes/findings/INDEX.md — the cheap layer an agent reads before opening any finding."""
import re
from collections import defaultdict
from pathlib import Path

FINDINGS = Path(__file__).resolve().parent / "findings"


def parse(f):
    m = re.match(r"---\n(.*?)\n---", f.read_text(), re.S)
    if not m:
        return None
    head = m.group(1)
    tags = re.search(r"tags:\s*\[(.*?)\]", head)
    verdict = re.search(r"verdict:\s*(.+)", head)
    return {
        "slug": f.stem,
        "tags": [t.strip() for t in (tags.group(1) if tags else "").split(",") if t.strip()],
        "verdict": (verdict.group(1).strip() if verdict else "—"),
    }


def main():
    entries = sorted(filter(None, (parse(f) for f in FINDINGS.glob("[0-9]*.md"))), key=lambda e: e["slug"])
    by_tag = defaultdict(list)
    for e in entries:
        for t in e["tags"]:
            by_tag[t].append(e["slug"])

    out = ["# Findings index", "",
           "Read this first. Open a finding only when its verdict does not already answer the question.", ""]
    for e in entries:
        out.append(f"- **{e['slug']}** — {e['verdict']}  \n  `{' '.join(e['tags'])}`")
    out += ["", "## By tag", ""]
    for tag in sorted(by_tag):
        out.append(f"- **{tag}** — {', '.join(by_tag[tag])}")
    (FINDINGS / "INDEX.md").write_text("\n".join(out) + "\n")
    print(f"indexed {len(entries)} findings, {len(by_tag)} tags")


if __name__ == "__main__":
    main()
