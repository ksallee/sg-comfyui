"""Site access: credentials, profile, and the live lookups the node's pickers read.

ComfyUI does not load .env.local, so the node does it. Values are never logged — an error names the
missing key, never its value.

Everything here is setup path: it serves the editor, never the publish path. All of it is cached and
all of it fails soft, because INPUT_TYPES is re-evaluated on every /object_info request (server.py:756)
— that is every page load and every node search — and a node that cannot reach the site must still
load, or the operator cannot open a graph that contains it.
"""
import json
import os
import threading
import time
from pathlib import Path

from . import _deps  # noqa: F401  puts sg_groundtruth on sys.path
from sg_groundtruth.client import FPT, FPTError

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env.local"
PROFILE = ROOT / "profile.local.json"

# probe 004 — _search rejects application/json with 415 and demands a vendor type.
ARRAY_JSON = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
# probe 030 — boolean logic needs the hash type. api3_array's flat list is an implicit `and` and has
# no spelling for `or`; api3_hash takes {"logical_operator", "conditions"} and expresses both, nested.
HASH_JSON = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}


def filter_headers(filters):
    """The Content-Type this filter shape requires (probe 030). The two are not interchangeable."""
    return HASH_JSON if isinstance(filters, dict) else ARRAY_JSON

# Setup-path data: projects, entities, statuses, schema. It changes when someone edits the site, not
# while a graph is open, and every one of these lookups happens inside INPUT_TYPES — which ComfyUI
# re-runs on every /object_info, i.e. every page load and every node search. At 60s a tab opened a
# minute after the last one paid 4.2s on the largest endpoint in the app and looked hung. The
# "refresh from site" button exists for when the wait is actually wanted.
TTL = 600.0
_cache = {}


def _load_env():
    if not ENV.is_file():
        return
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def client():
    _load_env()
    return FPT.from_env()


def profile():
    """What this site actually practices. Written by the inspector; hand-editable.

    Absent until the inspector has run, so every reader must tolerate {} rather than guess a
    convention (DESIGN: site profile).
    """
    if not PROFILE.is_file():
        return {}
    try:
        return json.loads(PROFILE.read_text())
    except json.JSONDecodeError as e:
        raise FPTError(f"{PROFILE.name} is not valid JSON: {e}")


def default_project():
    """The project the node opens on. `project_id` is the older flat spelling of the same thing."""
    p = profile()
    return int(p.get("default_project") or p.get("project_id") or 0)


def for_project(project_id=None):
    """The profile values in force for one project.

    Top-level keys are the site default; a `projects: {"<id>": {...}}` block overrides them per show.
    DESIGN says the profile is keyed per project because one studio runs shows with different
    conventions — where every show agrees, the block is simply absent.

    This is why two graphs open in one ComfyUI can publish into two projects that link Versions
    differently: `link_type` and `link_field` are resolved from the project the operator picked on
    the node, not from one global setting.
    """
    p = profile()
    out = {k: v for k, v in p.items() if k != "projects"}
    out.update((p.get("projects") or {}).get(str(project_id or default_project()), {}))
    return out


def _cached(key, fetch):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    try:
        value = fetch()
    except Exception:
        return hit[1] if hit else []   # stale beats empty; empty beats an unopenable graph
    _cache[key] = (time.time(), value)
    return value


def forget(*prefixes):
    """Drop cached lookups a write just invalidated.

    Without this, three publish nodes in one execution each read the version count from before any of
    them wrote, and all three propose the same next version.
    """
    for key in [k for k in _cache if k and k[0] in prefixes]:
        _cache.pop(key, None)


def warm():
    """Fill the setup caches in the background at import, off the first page load.

    Everything here is read on the first /object_info, and doing it then costs ~4s on the largest
    endpoint in the app — which reads as ComfyUI hanging. Failures are ignored: an unreachable site
    must still let the editor open (that is what _cached already guarantees), this only decides when
    the waiting happens.
    """
    def run():
        try:
            pid = default_project()
            projects()
            if pid:
                statuses(pid)
                link_type_choices(pid)
                links(pid)
        except Exception:
            pass
    threading.Thread(target=run, name="fpt-warm", daemon=True).start()


def route(entity_type):
    """Flow PT routes are the lowercased plural: Shot -> /entity/shots (recipe 001)."""
    return f"/entity/{entity_type.lower()}s"


def projects():
    """(name, id) for projects worth publishing into.

    probe 018 — do NOT filter on sg_status: it is null on most real projects, this sandbox included, so
    `sg_status is Active` hides working shows. The checkboxes are the reliable discriminators. Demo
    projects are excluded because publishing into the shipped demo show is never the intent; set
    `show_all_projects` in the profile to see everything.
    """
    show_all = bool(profile().get("show_all_projects"))   # site-wide: it is about the picker, not a show

    def fetch():
        filters = [] if show_all else [["is_template", "is", False],
                                       ["is_demo", "is", False],
                                       ["archived", "is", False]]
        r = client().post("/entity/projects/_search", headers=ARRAY_JSON,
                          json={"filters": filters, "fields": ["name"], "page": {"size": 500}})
        return [] if not r.ok else [(d["attributes"]["name"], d["id"]) for d in r.json()["data"]
                                    if d["attributes"].get("name")]
    return _cached(("projects", show_all), fetch)


def project_name(project_id):
    return next((n for n, i in projects() if i == int(project_id or 0)), "")


# Flow PT's own convention: the name leads, the type is shown after it as context. Putting the type
# first would mean typing a name no longer jumps to it in a combo.
def label_for(name, entity_type):
    return f"{name} ({entity_type})"


def link_types(project_id, limit=100):
    """Entity types Versions on this project ACTUALLY link to, most used first.

    `Version.entity` accepts 15 types site-wide (Asset, Shot, Sequence, Level, MocapTake, Reel,
    ShootDay, Delivery, Launch, Camera, Slate, SourceClip and three CustomEntity slots), so a single
    link type was never Flow PT's model — one show hangs Versions off Shots, another off Assets, and
    plenty use several at once. Searching all 15 would be slow and mostly empty, so this asks what the
    show does and searches that. `link_types` in the profile overrides it.
    """
    p = for_project(project_id)
    if p.get("link_types"):
        return list(p["link_types"])

    def fetch():
        r = client().get("/entity/versions", params={
            "filter[project.Project.id]": int(project_id), "fields": "entity",
            "sort": "-id", "page[size]": limit})
        if not r.ok:
            return []
        seen = {}
        for d in r.json()["data"]:
            e = ((d.get("relationships") or {}).get("entity") or {}).get("data") or {}
            if e.get("type"):
                seen[e["type"]] = seen.get(e["type"], 0) + 1
        return [t for t, _ in sorted(seen.items(), key=lambda kv: -kv[1])]

    # Observed first, then the common containers. Observation alone is circular: a brand new Asset
    # cannot be picked because no Version points at one yet, which is exactly when you need to.
    out = list(_cached(("link_types", int(project_id)), fetch))
    for t in (p.get("link_type", "Shot"), "Shot", "Asset", "Sequence"):
        if t and t not in out:
            out.append(t)
    # Keep only what the field will actually accept. Old rows can point at a type the schema no
    # longer allows — this site has Versions on Project, which is not in valid_types — and offering
    # it would produce a picker that cannot be written back.
    allowed = valid_link_types(project_id)
    return [t for t in out if t in allowed] or out


def valid_link_types(project_id=None, field="entity", entity_type="Version"):
    """What the link field accepts, straight from the schema. 15 types on this site."""
    def fetch():
        params = {"project_id": int(project_id)} if project_id else {}
        r = client().get(f"/schema/{entity_type}/fields/{field}", params=params)
        if not r.ok:
            return []
        return r.json()["data"]["properties"].get("valid_types", {}).get("value") or []
    return _cached(("valid_link_types", int(project_id or 0), entity_type, field), fetch)


# A readable, selectable "no restriction". An empty string cannot be chosen back once you leave it —
# a combo shows nothing to click — so the absence of a filter has to be a real option.
ALL_TYPES = "(all types)"
# An empty option cannot be chosen back once you leave it — a combo renders nothing to click — so
# "no value" has to be a real, visible entry. Same reason as ALL_TYPES.
NO_VALUE = "(none)"


def unset(value):
    """"" for anything that means no value, so callers never test for the label themselves."""
    return "" if not value or value in (NO_VALUE, ALL_TYPES) else value
PER_TYPE = 500       # a full list, capped so a pathological show cannot wedge the editor


def link_type_choices(project_id):
    """What to offer in the link_type combo: no restriction, then what this show uses, then the rest
    the field accepts. A type nothing links to yet still has to be pickable — that is precisely the
    case when a show is starting."""
    used = link_types(project_id)
    rest = [t for t in valid_link_types(project_id) if t not in used]
    return [ALL_TYPES] + used + sorted(rest)


def chosen_types(link_type, project_id):
    """None when the operator asked for everything, else the one type they picked."""
    if not link_type or link_type == ALL_TYPES:
        return None
    return [link_type]


def links(project_id, q="", types=None):
    """(label, type, id) — the whole list, for ComfyUI's own dropdown to search.

    Narrowing belongs to `link_type`, not to a second search box: the editor already has a searchable
    dropdown, and a bespoke one beside it behaves differently (its filter is a plain substring over
    what is loaded) which is worse than having none. So this returns everything for the chosen type,
    or for every type the show uses when none is chosen, sorted by name because a browsable list
    should be predictable.
    """
    if not project_id:
        return []
    out = []
    for t in (types or link_types(project_id)):
        for name, eid in entities(t, project_id, q=q, limit=PER_TYPE, sort="code"):
            out.append((label_for(name, t), t, eid))
    return out


def split_link(label):
    """`bunny_030_0090 (Shot)` -> ("Shot", "bunny_030_0090"). A bare name keeps its type unknown."""
    label = (label or "").strip()
    if label.endswith(")") and " (" in label:
        name, _, t = label[:-1].rpartition(" (")
        return t, name
    return "", label


def entities(entity_type, project_id, q="", field="code", limit=200, sort="code"):
    """(name, id) for a link picker, filtered server-side.

    probe 017 — `contains` is real, and an unknown operator 400s rather than passing silently, so a bad
    filter cannot masquerade as an unfiltered list.
    """
    if not entity_type or not project_id:
        return []

    def fetch():
        filters = [["project", "is", {"type": "Project", "id": int(project_id)}]]
        # Multi-word search the way the Flow PT UI does it: `foo bar` matches names containing BOTH,
        # and only the name is searched — the type is shown, never matched (probe 017: filters AND,
        # and `contains` is real).
        filters += [[field, "contains", term] for term in (q or "").split()]
        r = client().post(f"{route(entity_type)}/_search", headers=ARRAY_JSON,
                          json={"filters": filters, "fields": [field], "sort": sort,
                                "page": {"size": limit}})
        return [] if not r.ok else [(d["attributes"][field], d["id"]) for d in r.json()["data"]
                                    if d["attributes"].get(field)]
    return _cached(("entities", entity_type, int(project_id), q, field, limit, sort), fetch)


def tasks_for(link_type, link_id, limit=200):
    """(content, id) for the Tasks hanging off one entity.

    probe 017 — an entity field filters on a FULL {type, id} hash; {id} alone and bare ints both 400.
    """
    if not link_type or not link_id:
        return []

    def fetch():
        r = client().post("/entity/tasks/_search", headers=ARRAY_JSON,
                          json={"filters": [["entity", "is", {"type": link_type, "id": int(link_id)}]],
                                "fields": ["content"], "page": {"size": limit}})
        return [] if not r.ok else [(d["attributes"]["content"], d["id"]) for d in r.json()["data"]
                                    if d["attributes"].get("content")]
    return _cached(("tasks", link_type, int(link_id)), fetch)


def versions(project_id, link_type="", link_id=0, q="", limit=200):
    """(code, id) for the Versions worth offering, newest first.

    probe 017 — `contains` filters server-side; probe 005 — narrowing by the link entity is the way an
    operator actually thinks about it ("the plates on this shot"), so it is a filter, not a scroll.
    """
    if not project_id:
        return []

    def fetch():
        filters = [["project", "is", {"type": "Project", "id": int(project_id)}]]
        if link_type and link_id:
            filters.append(["entity", "is", {"type": link_type, "id": int(link_id)}])
        if q:
            filters.append(["code", "contains", q])
        r = client().post("/entity/versions/_search", headers=ARRAY_JSON,
                          json={"filters": filters, "fields": ["code"], "sort": "-id",
                                "page": {"size": limit}})
        return [] if not r.ok else [(d["attributes"]["code"], d["id"]) for d in r.json()["data"]
                                    if d["attributes"].get("code")]
    return _cached(("versions", int(project_id), link_type, int(link_id), q), fetch)


def version_filters(project_id, link_type="", link_id=0, task_id=0, terms=(), statuses=()):
    """The Flow PT filter the pickers add up to — the API's own language, not a private format.

    Returned so it can be shown and copied: a power user or an agent that needs something the widgets
    cannot express edits this array and hands it straight back (DESIGN: data-driven, with an eject
    hatch). Array form, since that is what _search takes (probe 004).
    """
    filters = [["project", "is", {"type": "Project", "id": int(project_id)}]]
    if link_type and link_id:
        filters.append(["entity", "is", {"type": link_type, "id": int(link_id)}])
    if task_id:
        filters.append(["sg_task", "is", {"type": "Task", "id": int(task_id)}])
    # Same multi-word rule as the pickers: every word must appear (probe 017).
    filters += [["code", "contains", t] for t in terms if t]
    # `in` takes a plain list for a scalar field, so several statuses are one filter, not a fight
    # with filter_operator (probe 017).
    if statuses:
        filters.append(["sg_status_list", "in", list(statuses)])
    return filters


def find_versions(project_id, link_type="", link_id=0, task_id=0, terms=(), statuses=(),
                  sort="-id", limit=200, filters=None):
    """(code, status, id) for Versions matching a rule, newest first.

    Every part is optional and narrows: an entity, a Task on it, words that must all appear in the
    code, a set of statuses any of which will do. That is the shape an artist thinks in — "the newest
    approved depth on this shot" — rather than an id. `filters` overrides the lot.
    """
    if not project_id and not filters:
        return []
    if filters is None:
        filters = version_filters(project_id, link_type, link_id, task_id, terms, statuses)

    def fetch():
        # An array is the implicit `and`; a dict carries `logical_operator` and needs the other
        # Content-Type (probe 030).
        r = client().post("/entity/versions/_search", headers=filter_headers(filters),
                          json={"filters": filters, "fields": ["code", "sg_status_list"],
                                "sort": sort, "page": {"size": limit}})
        return [] if not r.ok else [(d["attributes"].get("code") or "",
                                     d["attributes"].get("sg_status_list") or "", d["id"])
                                    for d in r.json()["data"]]
    key = ("find", json.dumps(filters, sort_keys=True, default=str), sort, limit)
    return _cached(key, fetch)


def versions_on(link_type, link_id, project_id, limit=200, sort="-id"):
    """(code, status, id) for every Version on one entity, newest first.

    probe 017 — an entity field filters on a full {type, id} hash. Status comes back so the caller can
    ask for the latest APPROVED one without a second round trip.
    """
    if not link_type or not link_id:
        return []

    def fetch():
        r = client().post("/entity/versions/_search", headers=ARRAY_JSON,
                          json={"filters": [["project", "is", {"type": "Project", "id": int(project_id)}],
                                            ["entity", "is", {"type": link_type, "id": int(link_id)}]],
                                "fields": ["code", "sg_status_list"], "sort": sort,
                                "page": {"size": limit}})
        return [] if not r.ok else [(d["attributes"].get("code") or "",
                                     d["attributes"].get("sg_status_list") or "", d["id"])
                                    for d in r.json()["data"]]
    return _cached(("versions_on", link_type, int(link_id), int(project_id), sort), fetch)


def version_numbers(link_type, link_id, project_id, field, limit=200):
    """Existing values of a site's real version-number field, for the next one."""
    if not (link_type and link_id and field):
        return []

    def fetch():
        r = client().post("/entity/versions/_search", headers=ARRAY_JSON,
                          json={"filters": [["project", "is", {"type": "Project", "id": int(project_id)}],
                                            ["entity", "is", {"type": link_type, "id": int(link_id)}]],
                                "fields": [field], "page": {"size": limit}})
        return [] if not r.ok else [d["attributes"].get(field) for d in r.json()["data"]]
    return _cached(("vnums", link_type, int(link_id), int(project_id), field), fetch)


def status_lookup(project_id):
    """{typed: code} accepting either what the UI shows or what the API stores.

    'Approved', 'approved' and 'apr' all mean the same thing, and an operator reading the Flow PT web
    UI has only ever seen the first. Codes are what the API wants (probe 009), so both are accepted
    and neither is guessed at.
    """
    out = {}
    for label, code in statuses(project_id):
        out[label.strip().lower()] = code
        out[code.strip().lower()] = code
    return out


def resolve_statuses(project_id, typed):
    """(codes, unrecognised) for whatever the operator wrote."""
    look = status_lookup(project_id)
    codes, bad = [], []
    for t in typed:
        c = look.get(str(t).strip().lower())
        if c and c not in codes:
            codes.append(c)
        elif not c:
            bad.append(str(t).strip())
    return codes, bad


def status_colors():
    """{code: "r,g,b"} for every status the site defines.

    probe 010 — Status.bg_color is comma-separated RGB, not hex, and is enough to render a badge
    without resolving the icon sprite. Site-wide: the colour of `apr` does not change per project,
    only whether a project offers it (probe 009).
    """
    def fetch():
        r = client().get("/entity/statuses", params={"fields": "code,bg_color", "page[size]": 200})
        return {} if not r.ok else {d["attributes"]["code"]: d["attributes"].get("bg_color")
                                    for d in r.json()["data"] if d["attributes"].get("code")}
    return _cached(("status_colors",), fetch)


def status_icons():
    """{code: {"kind", "url", "html"}} — what can actually be drawn for a status.

    probe 010 — Status.icon is an ENTITY link, so it arrives under relationships, and resolves three
    ways by display_type. `image` is a custom upload whose url IS a self-contained data: URI, and
    `html` is a text badge. `image_map` is the 94 standard icons, addressed by a key like `icon_apr`
    into a sprite whose location that probe never found — 23 of 25 icons here are that kind, so the
    colour badge is not a fallback, it is the main path.
    """
    def fetch():
        r = client().get("/entity/statuses", params={"fields": "code,icon", "page[size]": 200})
        if not r.ok:
            return {}
        by_icon = {}
        for d in r.json()["data"]:
            ic = ((d.get("relationships") or {}).get("icon") or {}).get("data")
            if ic and d["attributes"].get("code"):
                by_icon.setdefault(ic["id"], []).append(d["attributes"]["code"])
        if not by_icon:
            return {}
        r2 = client().post("/entity/icons/_search", headers=ARRAY_JSON,
                           json={"filters": [["id", "in", list(by_icon)]],
                                 "fields": ["display_type", "url", "html"],
                                 "page": {"size": 200}})
        out = {}
        for d in (r2.json().get("data", []) if r2.ok else []):
            a = d["attributes"]
            for code in by_icon.get(d["id"], []):
                out[code] = {"kind": a.get("display_type"),
                             # newlines in the base64 break an <img src> (probe 010)
                             "url": (a.get("url") or "").replace("\n", ""),
                             "html": a.get("html") or ""}
        return out
    return _cached(("status_icons",), fetch)


def resolve_paths(paths, project_id, link_type="", link_id=0, task_id=0, extra=None):
    """{path: value} for template paths like `entity.Shot.code` or `task.Task.content`.

    The prefix names which entity to read — `entity` the thing the Version hangs off, `task` its Task,
    `project` the show — and the last segment is the field. A middle segment is the entity type, which
    Flow PT's own dotted syntax carries (probe 003) and which we can ignore because the id already
    tells us what we are reading.
    """
    out = dict(extra or {})
    wanted = {}
    for p in paths:
        if p in out:
            continue
        bits = p.split(".")
        prefix, field = bits[0], bits[-1]
        if prefix == "entity" and link_type and link_id:
            wanted.setdefault((link_type, int(link_id)), []).append((p, field))
        elif prefix in ("task", "sg_task") and task_id:
            wanted.setdefault(("Task", int(task_id)), []).append((p, field))
        elif prefix == "project" and project_id:
            wanted.setdefault(("Project", int(project_id)), []).append((p, field))

    for (etype, eid), items in wanted.items():
        fields = sorted({f for _, f in items})

        def fetch(etype=etype, eid=eid, fields=tuple(fields)):
            r = client().get(f"{route(etype)}/{eid}", params={"fields": ",".join(fields)})
            return r.json()["data"]["attributes"] if r.ok else {}
        attrs = _cached(("paths", etype, eid, tuple(fields)), fetch) or {}
        for path, field in items:
            v = attrs.get(field)
            out[path] = v.get("name") if isinstance(v, dict) else v
    return out


def statuses(project_id, entity_type="Version", field="sg_status_list"):
    """(display label, code) actually usable in this project.

    probe 009 — usable is valid_values MINUS hidden_values, read with project_id; valid_values alone is
    identical at every scope and is not the answer. Labels matter: 'pndvs' means nothing to a user.
    """
    if not project_id:
        return []

    def fetch():
        r = client().get(f"/schema/{entity_type}/fields/{field}", params={"project_id": int(project_id)})
        if not r.ok:
            return []
        p = r.json()["data"]["properties"]
        valid = p["valid_values"]["value"] or []
        hidden = p["hidden_values"]["value"] or []
        shown = p["display_values"]["value"] or {}
        return [(shown.get(v, v), v) for v in valid if v not in hidden]
    return _cached(("statuses", int(project_id), entity_type, field), fetch)
