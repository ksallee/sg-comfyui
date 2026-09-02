"""Version naming conventions: infer one, match it, produce the next.

A Version has NO version-number field — PublishedFile does, Version does not — so the version lives
inside `code` as a naming convention that differs per site and per show. Nothing here may be
hardcoded; the convention is inferred, shown to the operator with its coverage, and stored in the
profile as data.

Validated against the reference show, where one pattern covers 99 of 100 codes:

    bunny_030_0090_comp_v002   ->  link=bunny_030_0090  task=comp  version=2

and the code contains its own link entity name in 99 of 100 rows, which is what makes per-link
numbering possible without a structured field.
"""
import re
from collections import Counter

# Ordered: the first pattern that covers the sample wins. Each must name `version`; `link` and `task`
# are optional captures, present when the convention encodes them.
PATTERNS = [
    ("{link}_{task}_v{version}", r"^(?P<link>.+)_(?P<task>[A-Za-z]+)_v(?P<version>\d+)$"),
    ("{link}_v{version}",        r"^(?P<link>.+)_v(?P<version>\d+)$"),
    ("{link}.v{version}",        r"^(?P<link>.+)\.v(?P<version>\d+)$"),
    ("{link}_{task}.{version}",  r"^(?P<link>.+)_(?P<task>[A-Za-z]+)\.(?P<version>\d+)$"),
    ("{link}-v{version}",        r"^(?P<link>.+)-v(?P<version>\d+)$"),
]


def infer(codes):
    """(template, regex, matched, total) for the pattern that best fits real codes.

    Returns the best even when coverage is poor — the caller shows the number and lets the operator
    judge, the same way every other inference in this project works. Coverage is the evidence.
    """
    codes = [c for c in codes if isinstance(c, str) and c.strip()]
    if not codes:
        return None, None, 0, 0
    best = max(((t, rx, sum(1 for c in codes if re.match(rx, c))) for t, rx in PATTERNS),
               key=lambda x: x[2])
    return best[0], best[1], best[2], len(codes)


def parse(code, regex):
    m = re.match(regex, code or "")
    if not m:
        return None
    d = m.groupdict()
    d["version"] = int(d["version"])
    return d


def width(regex, codes):
    """Zero-padding actually in use, so v001 does not become v1 on the next publish."""
    ns = [re.match(regex, c).group("version") for c in codes if re.match(regex, c)]
    return Counter(len(n) for n in ns).most_common(1)[0][0] if ns else 3


def next_code(template, regex, existing, link="", task=""):
    """The next code for one link, following the convention the site already uses.

    `existing` is every code already on that link. Numbering is per link, not global — two shots each
    have their own v001.
    """
    parsed = [p for p in (parse(c, regex) for c in existing) if p]
    n = max((p["version"] for p in parsed), default=0) + 1
    w = width(regex, existing)
    out = template.replace("{version}", str(n).zfill(w))
    return out.replace("{link}", link or "").replace("{task}", task or "")


def describe(template, regex, matched, total):
    pct = (100 * matched // total) if total else 0
    return f"{template}  ({matched}/{total} of recent codes, {pct}%)"
