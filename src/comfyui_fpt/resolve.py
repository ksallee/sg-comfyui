"""Pick the one Version a Fetch node should read, from a rule rather than an id.

This is what turns two nodes into a pipeline: step N publishes `shot010_comp_v003`, step N+1 asks for
"the latest on this Shot" and gets it, without anyone copying an id between graphs.

Ordering prefers the convention's version number over creation order, because a re-published v002 is
newer by id but older by intent. Falls back to id when no convention matches (probe: Kids Room scores
0% and there is nothing to parse).
"""
from . import naming, site

LATEST = "latest"
LATEST_APPROVED = "latest approved"
PINNED = "pinned id"
MODES = [PINNED, LATEST, LATEST_APPROVED]


def candidates(link_type, link_id, project_id, match=""):
    rows = site.versions_on(link_type, link_id, project_id)
    return [r for r in rows if not match or match.lower() in r[0].lower()]


def pick(mode, link_type, link_id, project_id, match="", approved_status="", regex=""):
    """(version_id, code, why) — `why` is shown to the operator, never guessed at silently."""
    rows = candidates(link_type, link_id, project_id, match)
    if not rows:
        return 0, "", f"no Versions on {link_type} {link_id}" + (f" matching {match!r}" if match else "")

    if mode == LATEST_APPROVED:
        if not approved_status:
            return 0, "", ("no approved status in the profile — status codes are per project "
                           "(probe 009), so which one means approved cannot be assumed")
        rows = [r for r in rows if r[1] == approved_status]
        if not rows:
            return 0, "", f"nothing on {link_type} {link_id} has status {approved_status!r}"

    parsed = [(naming.parse(c, regex), c, i) for c, _, i in rows] if regex else []
    usable = [(p["version"], c, i) for p, c, i in parsed if p]
    if usable:
        v, code, vid = max(usable, key=lambda x: x[0])
        return vid, code, f"highest version in {len(usable)} matching the convention"
    code, _, vid = rows[0]
    return vid, code, "newest by id — no code matched the convention"
