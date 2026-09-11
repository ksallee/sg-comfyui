"""The template language for Version codes and PublishedFile paths, and version numbering.

A template is written in SG's own vocabulary: dotted field paths to any depth
(`{entity.Shot.code}`), Python's format spec (`{version:03d}`), `[optional blocks]` that vanish
when their fields are empty, and printf padding (`v%04d`) as a synonym for a version spec.

Where the version number is recorded is site-specific. A site with a numeric field on Version uses
`next_number`. A site without one records the version inside `code` as a convention, matched with
`next_version`.
"""
import re
import string

# Any format spec, not just zero-padding: the spec is handed to Python, so a path with one is still
# recognised as a field.
FIELD_RE = re.compile(r"\{([a-zA-Z_][\w.]*?)(?::([^{}]*))?\}")
# Toolkit spells an optional key with square brackets, and so does a template here:
# `[_{sg_task.Task.content}]` disappears entirely, separator and all, when the task is not set.
OPTIONAL_RE = re.compile(r"\[([^\[\]]*)\]")
FRAME_SUFFIX = r"(?:_\d{2,})?"                # publish_version appends `_01` per frame of a batch
LEGACY_VERSION_RE = re.compile(r"%(0\d+)d")   # only the printf part; a preceding `v` is literal

DEFAULT_TEMPLATE = "{root_name}_v{version:03d}"
# recipe 004: `name` is the stream and `code` is one version of it. The versioned name is composed
# from this template, never derived by stripping a version token back out of one.
# The pipeline step through the Task, by `short_name` as Toolkit's own {Step} key reads it: steps
# are the studio's fixed vocabulary where Task names are free text. A Version with no Task renders
# the entity alone, because an empty token drops out with its separator (render).
DEFAULT_ROOT_TEMPLATE = "{entity}_{sg_task.Task.step.Step.short_name}"

# What the editor offers inside a template, one list per kind. Each token has one sentence for the
# operator, and the entity type it descends into where the editor may read that type's fields from
# the schema. The list is where a template starts, not the vocabulary: a dotted field path to any
# depth works (probe 003).
_LINK_TOKENS = [
    # `{entity}` descends into the type this project links a Version to, and `tokens` fills that in:
    # it is per project (probe 005).
    ("{entity}", "The name of the Shot or Asset this node is linked to.", ""),
    ("{sg_task}", "The name of the Task this node is linked to.", "Task"),
    ("{sg_task.Task.step.Step.short_name}", "The pipeline step of that Task, short, such as RTO.",
     ""),
    ("{sg_task.Task.step}", "The pipeline step of that Task in full, such as Roto.", "Step"),
    ("{project}", "The name of the project.", "Project"),
]
_VERSION_TOKEN = ("{version:03d}", "The version number, padded to three digits.", "")
_ROOT_TOKEN = ("{root_name}", "The root name, from the Root name template.", "")
_NAME_TOKEN = ("{version_name}", "The Version name, from the Version name template.", "")
_EXT_TOKEN = ("{ext}", "The extension of the files being written, such as .exr.", "")
_FRAME_TOKEN = ("%04d", "The frame number, padded to four digits.", "")

TOKENS = {
    "root": _LINK_TOKENS,
    "name": [_ROOT_TOKEN, _VERSION_TOKEN] + _LINK_TOKENS,
    "sequence": [_ROOT_TOKEN, _NAME_TOKEN, _FRAME_TOKEN, _EXT_TOKEN, _VERSION_TOKEN] + _LINK_TOKENS,
    # A still is one file and has no frame number, so it takes the movie's list.
    "still": [_ROOT_TOKEN, _NAME_TOKEN, _EXT_TOKEN, _VERSION_TOKEN] + _LINK_TOKENS,
    "movie": [_ROOT_TOKEN, _NAME_TOKEN, _EXT_TOKEN, _VERSION_TOKEN] + _LINK_TOKENS,
}


def tokens(kind, link_types=("Shot",)):
    """The tokens a template of this kind may use. `kind` is root, name, sequence, still or movie.

    `link_types` is what this node links a Version to: the picked link's type, else the types the
    project uses. One type is what `{entity}` descends into; several are offered as `types`, and
    the operator picks the hop.
    """
    types = [link_types] if isinstance(link_types, str) else list(link_types)
    rows = []
    for t, note, into in TOKENS.get(kind, ()):
        row = {"token": t, "note": note, "type": into}
        if t == "{entity}":
            row["type"] = types[0] if len(types) == 1 else ""
            row["types"] = types
        rows.append(row)
    return rows


def next_number(existing_numbers):
    """Next value for a site's own numeric version field, which is authoritative where it exists."""
    ns = [int(n) for n in existing_numbers if isinstance(n, (int, float))]
    return max(ns, default=0) + 1


def parse(code, regex):
    """The named groups one convention's regex finds in a code, with `version` as an int.

    `regex` is the profile's `code_regex`, which must name a `version` group.
    """
    m = re.match(regex, code or "")
    if not m:
        return None
    d = m.groupdict()
    d["version"] = int(d["version"])
    return d


def normalise_template(template):
    """Accept `v%04d` beside `{version:04d}`. Printf padding is what a TD writes by habit."""
    return LEGACY_VERSION_RE.sub(lambda m: "{version:%sd}" % m.group(1), template or "")


def template_fields(template):
    """The field paths a template needs, minus `version`, so a caller can fetch them.

    Optional blocks are included: whether one survives depends on its value, so the value has to be
    looked up first.
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
    """Python's own formatter with the dotted path used as the key.

    `str.format` reads `{a.b}` as attribute access and `{a[b]}` as item access, but a template path
    like `entity.Shot.code` is one key, not a lookup chain. Overriding `get_field` lets SG's dotted
    syntax and Python's format spec coexist, so `{sg_version_number:03d}` pads and `{code:>12}`
    aligns without either being taught here.
    """

    def get_field(self, name, args, kwargs):
        return kwargs.get(name), name

    def format_field(self, value, spec):
        # An absent path collapses to empty and takes its spec with it: zero-padding nothing would
        # write "000".
        if value in (None, ""):
            return ""
        try:
            return format(value, spec)
        except (TypeError, ValueError):
            # SG returns numbers as strings, so a numeric spec on text coerces rather than
            # refuses.
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


def _all_filled(template, values):
    return all(values.get(m.group(1)) for m in FIELD_RE.finditer(template)
               if m.group(1) != "version" and OPTIONAL_RE.search(template))


def template_regex(template, values):
    """A matcher for codes this template has produced, with the known values pinned.

    Pinning is what makes numbering per link and per stream: the depth pass of one shot counts its
    own history and nobody else's.
    """
    out, i = "", 0
    # Existing codes were written with the optional blocks both kept and dropped, so the matcher has
    # to accept whichever shape these values produce.
    t = normalise_template(template)
    t = OPTIONAL_RE.sub(lambda m: m.group(1), t) if _all_filled(t, values) else \
        _drop_unfilled(t, values)
    for m in FIELD_RE.finditer(t):
        out += re.escape(t[i:m.start()])
        path = m.group(1)
        if path == "version":
            out += r"(?P<version>\d+)"
        else:
            v = values.get(path)
            out += re.escape(str(v)) if v else r"[^_]*"
        i = m.end()
    # A batch publishes one Version per frame and appends `_01`, `_02` and so on to the rendered
    # code (publish_version). The matcher accepts that suffix. Anchored strictly, a re-run would
    # count zero previous versions and mint v001 on top of the run already there.
    return "^" + out + re.escape(t[i:]) + FRAME_SUFFIX + "$"


def next_version(codes, template, values):
    """The next version number for this template and these values."""
    rx = re.compile(template_regex(template, values))
    used = [int(m.group("version")) for m in (rx.match(c or "") for c in codes) if m]
    return max(used, default=0) + 1
