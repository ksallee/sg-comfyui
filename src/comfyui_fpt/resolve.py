"""Pick the one Version a Load node should read, from a rule rather than an id.

The rule is what an artist would say out loud — *the newest approved depth on this shot* — so it is
an entity, optionally a Task on it, words that must appear in the name, and any of a set of statuses,
each part optional and each one narrowing. Nothing here invents vocabulary Flow PT does not have:
"approved" is one status code among the ones that project allows (probe 009).

Ordering is a choice because "newest" is ambiguous — a re-published v002 is newer by id but older by
intent — so the convention's version number is offered alongside id and created_at.
"""
from . import site

BY_VERSION = "version number in the name"
BY_CREATED = "created_at"
BY_ID = "id (creation order)"
ORDERS = [BY_VERSION, BY_CREATED, BY_ID]

SORT = {BY_CREATED: "-created_at", BY_ID: "-id", BY_VERSION: "-id"}


def _terms(name_contains):
    return [t for t in (name_contains or "").split() if t]


def filters_for(project_id, link_type="", link_id=0, task_id=0, name_contains="", statuses=()):
    """The Flow PT filter these widget values add up to."""
    return site.version_filters(project_id, link_type, link_id, task_id,
                                _terms(name_contains), statuses)


def combine(base, extra):
    """The fields' filter with the operator's own conditions ANDed on.

    A `_search` filter array is an implicit AND (probe 004), so extra conditions simply append. A
    dict is a group carrying its own `logical_operator` (probe 030) and appends as ONE element, which
    is how "these fields, and also (a or b)" is said.

    Additive, never a replacement: an escape hatch that switched the pickers off would let an
    operator set a status, see nothing change, and have no way to find out why.
    """
    if not extra:
        return list(base)
    return list(base) + (list(extra) if isinstance(extra, list) else [extra])


def pick(project_id, link_type="", link_id=0, task_id=0, name_contains="", statuses=(),
         order=BY_VERSION, regex="", filters=None, where=""):
    """(version_id, code, why) — `why` is shown to the operator; nothing is guessed silently.

    `filters` is ANDed onto what the widgets add up to. It narrows, never replaces, so every field on
    the node keeps meaning what it says.

    `where` is what the operator called the link. Only ids reach here, and "nothing on Shot 7514"
    names a row they never typed; the caller knows the label they picked.
    """
    terms = _terms(name_contains)
    combined = combine(filters_for(project_id, link_type, link_id, task_id, name_contains, statuses),
                       filters) if filters else None
    rows = site.find_versions(project_id, link_type, link_id, task_id, terms, statuses,
                              sort=SORT.get(order, "-id"), filters=combined)
    if not rows:
        if filters:
            return 0, "", "nothing matches these fields plus the extra filter"
        where = where or (f"{link_type} {link_id}" if link_id else f"project {project_id}")
        bits = [b for b in (f"name containing {name_contains!r}" if terms else "",
                            f"status in {list(statuses)}" if statuses else "",
                            "a task" if task_id else "") if b]
        return 0, "", f"nothing on {where}" + (" with " + ", ".join(bits) if bits else "")

    if order == BY_VERSION and regex:
        from . import naming
        ranked = [(p["version"], c, i) for c, _, i in rows if (p := naming.parse(c, regex))]
        if ranked:
            _, code, vid = max(ranked, key=lambda x: x[0])
            return vid, code, f"highest version of {len(ranked)} matching the convention"

    code, _, vid = rows[0]
    how = "created_at" if order == BY_CREATED else "id"
    return vid, code, f"newest by {how} of {len(rows)}"
