"""Version naming conventions: infer one, match it, produce the next.

Where the version number lives is site-specific. A Toolkit-driven site usually carries a real numeric
field (`sg_version_number` or similar) and that is authoritative when present. Many sites do not — this
one has none — and then the version lives inside `code` as a freeform convention that differs per show.

So: use the field if the profile names one, otherwise infer the convention, show it to the operator
with its coverage, and store it as data. Nothing here is hardcoded either way.

Validated against the reference show, where one pattern covers 99 of 100 codes:

    bunny_030_0090_comp_v002   ->  link=bunny_030_0090  task=comp  version=2

and the code contains its own link entity name in 99 of 100 rows, which is what makes per-link
numbering possible without a structured field.
"""
import re
import string
from collections import Counter

# Ordered: the first pattern that covers the sample wins. Each must name `version`; `link` and `task`
# are optional captures, present when the convention encodes them.
PATTERNS = [
    # {output} is what a stream IS — depth, normals, mask. A graph with several image outputs needs it,
    # or every pass collapses onto one name. {task} is the show's pipeline step, a different thing.
    ("{link}_{task}_{output}_v{version}",
     r"^(?P<link>.+)_(?P<task>[A-Za-z]+)_(?P<output>[A-Za-z0-9]+)_v(?P<version>\d+)$"),
    ("{link}_{output}_v{version}", r"^(?P<link>.+)_(?P<output>[A-Za-z0-9]+)_v(?P<version>\d+)$"),
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


def version_field_candidates(schema):
    """Numeric Version fields that could be the version number, for the operator to choose from.

    Proposed, never auto-adopted: `sg_first_frame` is numeric too, and picking wrong would silently
    misnumber every publish.
    """
    return sorted(k for k, v in (schema or {}).items()
                  if v.get("data_type", {}).get("value") in ("number", "float")
                  and "version" in k.lower() and "transcoding" not in k.lower())


def next_number(existing_numbers):
    """Next value for a real version-number field. Authoritative when the site has one."""
    ns = [int(n) for n in existing_numbers if isinstance(n, (int, float))]
    return max(ns, default=0) + 1


# What each token may contain when a template is turned into a concrete regex.
TOKEN_RX = {"link": r".+?", "task": r"[A-Za-z][A-Za-z0-9]*", "output": r".+?", "version": r"\d+"}


def regex_from_template(template, link=""):
    """A concrete regex for one template, anchoring {link} literally when the link is known.

    Without that anchor a non-greedy {link} swallows part of {output}: `sbx_0020_depth_v001` parsed as
    link='sbx', output='0020_depth', so numbering for 'depth' never found its own history and every
    publish produced v001 again — two Versions, one code.
    """
    out, i = "", 0
    for m in re.finditer(r"\{(\w+)\}", template):
        out += re.escape(template[i:m.start()])
        name = m.group(1)
        out += re.escape(link) if (name == "link" and link) else f"(?P<{name}>{TOKEN_RX.get(name, '.+?')})"
        i = m.end()
    return "^" + out + re.escape(template[i:]) + "$"


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


def next_code(template, regex, existing, link="", task="", output=""):
    """The next code for one link, following the convention the site already uses.

    `existing` is every code already on that link. Numbering is per link AND per output: two shots
    each have their own v001, and a depth pass does not count a normals pass as history.
    """
    # Anchored on this link, so `depth` finds its own history and not another output's.
    rx = regex_from_template(template, link) if template else regex
    kept = [c for c in existing
            if (p := parse(c, rx)) and (not output or p.get("output") == output)]
    n = max((parse(c, rx)["version"] for c in kept), default=0) + 1
    w = width(rx, kept) if kept else width(regex, existing)
    out = template.replace("{version}", str(n).zfill(w))
    return (out.replace("{link}", link or "").replace("{task}", task or "")
               .replace("{output}", output or ""))


def describe(template, regex, matched, total):
    pct = (100 * matched // total) if total else 0
    return f"{template}  ({matched}/{total} of recent codes, {pct}%)"


# --- templates in Flow PT's own vocabulary -------------------------------------------------------
#
# A code is written the way the site already talks about fields: `{entity.Shot.code}_{output}_v{version:03d}`.
# Dotted paths are what filters and `?fields` use (probe 003/016), so a TD reading a template sees
# names they already know instead of a private token language.

# Any format spec, not just zero-padding: the renderer hands it to Python, so what is accepted here
# has to be everything the mini-language allows, or a path with a spec is never even looked up.
FIELD_RE = re.compile(r"\{([a-zA-Z_][\w.]*?)(?::([^{}]*))?\}")
# Toolkit spells an optional key with square brackets, so a TD writing a template here writes the
# same thing: [_{sg_task.Task.content}] disappears entirely when the task is not set, separator and
# all, rather than leaving a stray underscore.
OPTIONAL_RE = re.compile(r"\[([^\[\]]*)\]")
FRAME_SUFFIX = r"(?:_\d{2,})?"   # publish_version appends `_01` per frame of a batch
LEGACY_VERSION_RE = re.compile(r"%(0\d+)d")   # only the printf part; a preceding `v` is literal

DEFAULT_TEMPLATE = "{entity.code}_{output}_v{version:03d}"


def normalise_template(template):
    """Accept `v%04d` beside `{version:04d}` — printf padding is what a TD writes by habit."""
    return LEGACY_VERSION_RE.sub(lambda m: "{version:%sd}" % m.group(1), template or "")


def template_fields(template):
    """The paths a template needs, minus `version`, so a caller knows what to fetch.

    Optional blocks are included: whether they survive depends on the value, which is why the value
    has to be looked up first.
    """
    return [m.group(1) for m in FIELD_RE.finditer(normalise_template(template))
            if m.group(1) != "version"]


def _drop_unfilled(template, values):
    """Remove every [optional block] whose fields have no value, and unwrap the rest."""
    def keep(m):
        inner = m.group(1)
        for f in FIELD_RE.finditer(inner):
            if f.group(1) != "version" and not values.get(f.group(1)):
                return ""
        return inner
    return OPTIONAL_RE.sub(keep, template)


class _Paths(string.Formatter):
    """Python's own formatter, with the whole dotted path used as the key.

    `str.format` reads `{a.b}` as attribute access and `{a[b]}` as item access, but a template path
    like `entity.Shot.code` is one key, not a walk. Overriding get_field is what lets Flow PT's own
    dotted syntax and Python's format spec coexist — so `{sg_version_number:03d}` pads, `{code:>12}`
    aligns, and anything the mini-language grows works without being taught here.
    """

    def get_field(self, name, args, kwargs):
        return kwargs.get(name), name

    def format_field(self, value, spec):
        # An absent path collapses to empty rather than leaving a brace behind, and takes its spec
        # with it: zero-padding nothing would write "000".
        if value in (None, ""):
            return ""
        try:
            return format(value, spec)
        except (TypeError, ValueError):
            # A numeric spec on a value that arrived as text: Flow PT returns numbers as strings
            # often enough that refusing here would be pedantry.
            coerce = int if spec[-1:] in ("d", "b", "o", "x", "X") else (
                float if spec[-1:] in ("e", "E", "f", "F", "g", "G", "%") else None)
            if coerce:
                try:
                    return format(coerce(str(value).strip()), spec)
                except ValueError:
                    pass
            return str(value)


_FORMATTER = _Paths()


def render(template, values, version=None):
    """Fill a template. A path with no value collapses to empty rather than leaving a brace behind."""
    vals = dict(values)
    if version is not None:
        vals["version"] = int(version)
    out = _FORMATTER.vformat(_drop_unfilled(normalise_template(template), values), (), vals)
    # A missing middle token would otherwise leave a doubled or trailing separator.
    return re.sub(r"[_\-.]{2,}", "_", out).strip("_-.")


def template_regex(template, values):
    """A matcher for codes this template has produced, with the known values pinned.

    Pinning is what makes numbering per link and per output: the depth pass of one shot counts its
    own history and nobody else's.
    """
    out, i = "", 0
    # The matcher has to accept both shapes, since existing codes were written both ways.
    t = normalise_template(template)
    t = OPTIONAL_RE.sub(lambda m: m.group(1), t) if _all_filled(t, values) else \
        _drop_unfilled(t, values)
    for m in FIELD_RE.finditer(t):
        out += re.escape(t[i:m.start()])
        path, pad = m.group(1), m.group(2)
        if path == "version":
            out += r"(?P<version>\d+)"
        else:
            v = values.get(path)
            out += re.escape(str(v)) if v else r"[^_]*"
        i = m.end()
    # A batch publishes one Version per frame and appends `_01`, `_02` ... to the rendered code
    # (publish_version), which no longer matches the convention that produced it. Anchored strictly,
    # a re-run then counts zero previous versions and mints v001 on top of the run already there.
    # The suffix is ours, so the matcher has to know about it.
    return "^" + out + re.escape(t[i:]) + FRAME_SUFFIX + "$"


def _all_filled(template, values):
    return all(values.get(m.group(1)) for m in FIELD_RE.finditer(template)
               if m.group(1) != "version" and OPTIONAL_RE.search(template))


def next_version(codes, template, values):
    """The next version number for this template and these values."""
    rx = re.compile(template_regex(template, values))
    used = [int(m.group("version")) for m in (rx.match(c or "") for c in codes) if m]
    return max(used, default=0) + 1
