"""Pick the one Version a Fetch node should read, from a filter rather than an id.

The rule is Flow PT's own, not one this project invents: **order newest-first, optionally require a
status**. There is no "approved" concept in the API — approved is one status code among many, the
codes differ per project (probe 009), and a show may care about `rev`, `ip`, a custom code, or none at
all. So the operator picks the status and empty means any.

An earlier version of this module hardcoded "latest approved". That was this project inventing
vocabulary the API does not have.
"""
from . import site

PINNED = "pinned id"
NEWEST = "newest matching"
MODES = [NEWEST, PINNED]

BY_ID = "id (creation order)"
BY_CREATED = "created_at"
BY_VERSION = "version number in the code"
ORDERS = [BY_ID, BY_CREATED, BY_VERSION]


def pick(link_type, link_id, project_id, match="", status="", order=BY_ID, regex=""):
    """(version_id, code, why) — `why` is shown to the operator; nothing is guessed silently."""
    rows = site.versions_on(link_type, link_id, project_id,
                            sort="-created_at" if order == BY_CREATED else "-id")
    if not rows:
        return 0, "", f"no Versions on {link_type} {link_id}"

    if match:
        rows = [r for r in rows if match.lower() in (r[0] or "").lower()]
        if not rows:
            return 0, "", f"nothing on {link_type} {link_id} has {match!r} in its code"
    if status:
        rows = [r for r in rows if r[1] == status]
        if not rows:
            return 0, "", f"nothing on {link_type} {link_id} has status {status!r}"

    if order == BY_VERSION and regex:
        from . import naming
        ranked = [(p["version"], c, i) for c, _, i in rows if (p := naming.parse(c, regex))]
        if ranked:
            _, code, vid = max(ranked, key=lambda x: x[0])
            return vid, code, f"highest version among {len(ranked)} matching the convention"
        # fall through: nothing parsed, so ordering by code would be a lie

    code, st, vid = rows[0]
    where = "created_at" if order == BY_CREATED else "id"
    return vid, code, (f"newest by {where} of {len(rows)}"
                       + (f" with status {status!r}" if status else ""))
