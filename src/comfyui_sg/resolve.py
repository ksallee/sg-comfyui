"""Pick the one Version a Load node should read, from a rule rather than an id.

The rule is an entity, optionally a Task on it, words that must appear in the name, and any of a set
of statuses. Each part is optional and each one narrows. "approved" is one status code among the
ones that project allows (probe 009).

"newest" is ambiguous. A re-published v002 is newer by id but older by intent, so the convention's
version number is offered alongside id and created_at.
"""
from . import naming, site

BY_VERSION = "version number in the name"
BY_CREATED = "created_at"
BY_ID = "id (creation order)"
ORDERS = [BY_VERSION, BY_CREATED, BY_ID]

SORT = {BY_CREATED: "-created_at", BY_ID: "-id", BY_VERSION: "-id"}


# `naming.template_regex` pins the values it is handed and writes this for the rest, so numbering
# counts one link's own history. Ranking has nothing to pin, and a root name can contain an
# underscore, so the unpinned fields widen to match one.
UNPINNED = "[^_]*"


def _terms(name_contains):
    return [t for t in (name_contains or "").split() if t]


def regex_from(template):
    """A matcher for the codes a version-name template produces, naming a `version` group.

    A site with no `code_regex` ranks by this.
    """
    t = (template or "").strip() or naming.DEFAULT_TEMPLATE
    return naming.template_regex(t, {}).replace(UNPINNED, ".*")


def filters_for(project_id, link_type="", link_id=0, task_id=0, name_contains="", statuses=()):
    """The SG filter these widget values add up to."""
    return site.version_filters(project_id, link_type, link_id, task_id,
                                _terms(name_contains), statuses)


def combine(base, extra):
    """The fields' filter with the operator's own conditions ANDed on.

    A `_search` filter array is an implicit AND (probe 004), so extra conditions append. A dict is a
    group with its own `logical_operator` (probe 030) and appends as one element, which is how
    "these fields, and also (a or b)" is said.

    Additive, never a replacement.
    """
    if not extra:
        return list(base)
    return list(base) + (list(extra) if isinstance(extra, list) else [extra])


def pick(project_id, link_type="", link_id=0, task_id=0, name_contains="", statuses=(),
         order=BY_VERSION, regex="", filters=None, where="", template=""):
    """(version_id, code, why), with `why` shown to the operator.

    `filters` is ANDed onto what the widgets add up to. It narrows, never replaces.

    `where` is what the operator called the link. Only ids reach here, and "nothing on Shot 7514"
    names a row they never typed.

    `regex` is the convention measured on this project. `template` is the version-name template it
    publishes with, and ranking falls back to it where no convention was measured. `why` says which
    of the two ranked.
    """
    terms = _terms(name_contains)
    combined = combine(filters_for(project_id, link_type, link_id, task_id, name_contains, statuses),
                       filters) if filters else None
    rows = site.find_versions(project_id, link_type, link_id, task_id, terms, statuses,
                              sort=SORT.get(order, "-id"), filters=combined)
    if not rows:
        if filters:
            return 0, "", ("No Version matches these fields plus the extra filter. "
                           "Widen the filter, or clear it.")
        where = where or (f"{link_type} {link_id}" if link_id else f"project {project_id}")
        bits = [b for b in (f"a name containing {name_contains}" if terms else "",
                            f"status {', '.join(str(s) for s in statuses)}" if statuses else "",
                            "a task" if task_id else "") if b]
        return 0, "", (f"No Version on {where}" + (" with " + ", ".join(bits) if bits else "")
                       + ". Pick a different link, or clear some of the fields.")

    if order == BY_VERSION:
        rx, matched = (regex, "the project's name convention") if regex else \
            (regex_from(template), "the version name template")
        ranked = [(p["version"], c, i) for c, _, i in rows if (p := naming.parse(c, rx))]
        if ranked:
            _, code, vid = max(ranked, key=lambda x: x[0])
            return vid, code, f"highest version of {len(ranked)} matching {matched}"

    code, _, vid = rows[0]
    how = "created_at" if order == BY_CREATED else "id"
    return vid, code, f"newest by {how} of {len(rows)}"
