"""Pick the one Version a Fetch node should read, from a rule rather than an id.

The rule is what an artist would say out loud: *the newest approved depth on this shot*. So it is an
entity, optionally a Task on it, words that must appear in the name, and any of a set of statuses —
each part optional, each one narrowing. Nothing here invents vocabulary Flow PT does not have;
"approved" is simply one status code among the ones that project allows (probe 009).

Ordering is a choice because "newest" is ambiguous: a re-published v002 is newer by id but older by
intent, so the convention's version number is offered alongside id and created_at.
"""
from . import site

BY_VERSION = "version number in the name"
BY_CREATED = "created_at"
BY_ID = "id (creation order)"
ORDERS = [BY_VERSION, BY_CREATED, BY_ID]

SORT = {BY_CREATED: "-created_at", BY_ID: "-id", BY_VERSION: "-id"}


def pick(project_id, link_type="", link_id=0, task_id=0, name_contains="", statuses=(),
         order=BY_VERSION, regex=""):
    """(version_id, code, why) — `why` is shown to the operator; nothing is guessed silently."""
    terms = [t for t in (name_contains or "").split() if t]
    rows = site.find_versions(project_id, link_type, link_id, task_id, terms, statuses,
                              sort=SORT.get(order, "-id"))
    if not rows:
        where = f"{link_type} {link_id}" if link_id else f"project {project_id}"
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
