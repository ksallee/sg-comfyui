"""Credentials, the site profile, and the cached live lookups the node's pickers read.

Credentials are loaded from .env.local into a mapping handed straight to the client, never into
os.environ: ComfyUI is a long-lived process shared with every other installed custom node, and
anything in its environment is readable by all of them. Values are never logged; an error names the
missing key, never its value.

Everything here is setup path — it serves the editor, never the publish path. All of it is cached and
all of it fails soft, because INPUT_TYPES is re-evaluated on every /object_info request
(server.py:756), which is every page load and every node search, and a node that cannot reach the
site must still load or the operator cannot open a graph containing it.
"""
import datetime
import json
import re
import threading
import time
from pathlib import Path

import requests

from sg_groundtruth.client import FPT, FPTError
from sg_groundtruth.env import load as load_env

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "profile.local.json"

# probe 004 — _search rejects application/json with 415 and demands a vendor type.
ARRAY_JSON = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
# probe 030 — boolean logic needs the hash type. api3_array's flat list is an implicit `and` and has
# no spelling for `or`; api3_hash takes {"logical_operator", "conditions"} and expresses both, nested.
HASH_JSON = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}

# Setup-path data — projects, entities, statuses, schema — changes when someone edits the site, not
# while a graph is open. Every lookup here runs inside INPUT_TYPES, which ComfyUI re-runs on every
# /object_info, so the TTL is long: the largest endpoint in the app costs ~4s cold, and paying that
# on a page load reads as ComfyUI hanging. The "refresh from site" button forces a read.
TTL = 600.0
_cache = {}


def client():
    """A connected client. Credentials travel as an argument and are never put in os.environ."""
    return FPT.from_env(load_env(ROOT))


def route(entity_type):
    """Flow PT routes are the lowercased plural: Shot -> /entity/shots (recipe 001)."""
    return f"/entity/{entity_type.lower()}s"


def filter_headers(filters):
    """The Content-Type this filter shape requires (probe 030). The two are not interchangeable."""
    return HASH_JSON if isinstance(filters, dict) else ARRAY_JSON


def _is(field, entity_type, entity_id):
    """One `is` filter on an entity field.

    probe 017 — an entity field filters on a FULL {type, id} hash; {id} alone and a bare int both 400.
    """
    return [field, "is", {"type": entity_type, "id": int(entity_id)}]


def _search(entity_type, filters, fields, sort=None, limit=200):
    """The rows one _search returns, or [] on any error."""
    body = {"filters": filters, "fields": list(fields), "page": {"size": limit}}
    if sort:
        body["sort"] = sort
    r = client().post(f"{route(entity_type)}/_search", headers=filter_headers(filters), json=body)
    return r.json()["data"] if r.ok else []


def _pairs(rows, field):
    """(value, id) for rows that have the field filled."""
    return [(d["attributes"][field], d["id"]) for d in rows if d["attributes"].get(field)]


def _coded(rows):
    """(code, status, id) — the shape every Version picker consumes."""
    return [(d["attributes"].get("code") or "", d["attributes"].get("sg_status_list") or "", d["id"])
            for d in rows]


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
        raise FPTError(f"{PROFILE.name} is not valid JSON. Fix the file, then reload the page. {e}")


def default_project():
    """The project the node opens on. `project_id` is the older flat spelling of the same thing."""
    p = profile()
    return int(p.get("default_project") or p.get("project_id") or 0)


def for_project(project_id=None):
    """The profile values in force for one project.

    Top-level keys are the site default; a `projects: {"<id>": {...}}` block overrides them per show.
    This is what lets two graphs open in one ComfyUI publish into two projects that link Versions
    differently: `link_type` and `link_field` resolve from the project picked on the node, never from
    one global setting.
    """
    p = profile()
    out = {k: v for k, v in p.items() if k != "projects"}
    out.update((p.get("projects") or {}).get(str(project_id or default_project()), {}))
    return out


def provenance_map(project_id=None):
    """(mapping, mode) — where this show wants each piece of provenance to land.

    Per project like everything else here: a field one show uses for the seed may mean something
    else on the next.
    """
    block = for_project(project_id).get("provenance") or {}
    return dict(block.get("map") or {}), block.get("mode") or "fields"


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

    Three publish nodes in one execution must each see what the previous one wrote, or all three read
    the version count from before any of them wrote and all three propose the same next version.
    """
    for key in [k for k in _cache if k and k[0] in prefixes]:
        _cache.pop(key, None)


def warm():
    """Fill the setup caches in a background thread at import, off the first page load.

    Failures are ignored — _cached already guarantees an unreachable site still lets the editor open.
    This only decides when the waiting happens.
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


# A project row is drawn the way Flow PT draws one: thumbnail, name, code. `code` is a second unique
# text field, set on a minority of shows (entity_types/Project), and `image` is a presigned S3 URL,
# re-signed on every read and good for ~900s from that read (field_types/image) — longer than TTL, so
# a cached row's URL is still live and a stale one degrades to a blank tile. This prefix means the
# thumbnail is still transcoding and would render as a placeholder, so it is dropped rather than shown.
PENDING = "/images/status/transient/"


def project_cards():
    """{name, id, code, image} for projects worth publishing into.

    probe 018 — do NOT filter on sg_status: it is null on most real projects, this sandbox included,
    so `sg_status is Active` hides working shows. The checkboxes are the reliable discriminators.
    Demo projects are excluded because publishing into the shipped demo show is never the intent; set
    `show_all_projects` in the profile to see everything.
    """
    show_all = bool(profile().get("show_all_projects"))   # site-wide: it is about the picker, not a show

    def fetch():
        filters = [] if show_all else [["is_template", "is", False],
                                       ["is_demo", "is", False],
                                       ["archived", "is", False]]
        out = []
        for d in _search("Project", filters, ["name", "code", "image"], limit=500):
            a = d["attributes"]
            if not a.get("name"):
                continue
            image = a.get("image") or ""
            out.append({"name": a["name"], "id": d["id"], "code": a.get("code") or "",
                        "image": "" if PENDING in image else image})
        return out
    return _cached(("projects", show_all), fetch)


def projects():
    """(name, id), which is what every caller that only identifies a project wants."""
    return [(p["name"], p["id"]) for p in project_cards()]


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
    plenty use several at once. Searching all 15 is slow and mostly empty, so this asks what the show
    does and searches that. `link_types` in the profile overrides it.
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


# A combo renders nothing to click for an empty string, so an empty choice cannot be selected back
# once left. "No restriction" and "no value" are therefore real, visible entries.
ALL_TYPES = "(all types)"
NO_VALUE = "(none)"

PER_TYPE = 500       # a full list, capped so a pathological show cannot wedge the editor


def unset(value):
    """The empty string for anything meaning no value, so callers never test for the labels."""
    return "" if not value or value in (NO_VALUE, ALL_TYPES) else value


def link_type_choices(project_id):
    """What the link_type combo offers: no restriction, what this show uses, then the rest the field
    accepts. A type nothing links to yet still has to be pickable — that is precisely the case when a
    show is starting."""
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

    Narrowing belongs to `link_type`, not to a second search box: the editor's dropdown is already
    searchable, and a bespoke one beside it would filter by plain substring over what is loaded. So
    this returns everything for the chosen type, or for every type the show uses when none is chosen,
    sorted by name because a browsable list should be predictable.
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

    probe 017 — `contains` is real, and an unknown operator 400s rather than passing silently, so a
    bad filter cannot masquerade as an unfiltered list.
    """
    if not entity_type or not project_id:
        return []

    def fetch():
        # Multi-word search the way the Flow PT UI does it: `foo bar` matches names containing BOTH,
        # and only the name is searched — the type is shown, never matched (probe 017: filters AND).
        filters = [_is("project", "Project", project_id)]
        filters += [[field, "contains", term] for term in (q or "").split()]
        return _pairs(_search(entity_type, filters, [field], sort=sort, limit=limit), field)
    return _cached(("entities", entity_type, int(project_id), q, field, limit, sort), fetch)


def tasks_for(link_type, link_id, limit=200):
    """(content, id) for the Tasks hanging off one entity."""
    if not link_type or not link_id:
        return []

    def fetch():
        rows = _search("Task", [_is("entity", link_type, link_id)], ["content"], limit=limit)
        return _pairs(rows, "content")
    return _cached(("tasks", link_type, int(link_id)), fetch)


def versions(project_id, link_type="", link_id=0, q="", limit=200):
    """(code, id) for the Versions worth offering, newest first.

    probe 005 — narrowing by the link entity is how an operator thinks about it ("the plates on this
    shot"), so it is a filter rather than a scroll.
    """
    if not project_id:
        return []

    def fetch():
        filters = [_is("project", "Project", project_id)]
        if link_type and link_id:
            filters.append(_is("entity", link_type, link_id))
        if q:
            filters.append(["code", "contains", q])
        return _pairs(_search("Version", filters, ["code"], sort="-id", limit=limit), "code")
    return _cached(("versions", int(project_id), link_type, int(link_id), q), fetch)


def version_filters(project_id, link_type="", link_id=0, task_id=0, terms=(), statuses=()):
    """The Flow PT filter the pickers add up to — the API's own language, not a private format.

    Returned so it can be shown and copied: a power user or an agent that needs something the widgets
    cannot express edits this array and hands it straight back (DESIGN: data-driven, with an eject
    hatch). Array form, since that is what _search takes (probe 004).
    """
    filters = [_is("project", "Project", project_id)]
    if link_type and link_id:
        filters.append(_is("entity", link_type, link_id))
    if task_id:
        filters.append(_is("sg_task", "Task", task_id))
    # Same multi-word rule as the pickers: every word must appear (probe 017).
    filters += [["code", "contains", t] for t in terms if t]
    # `in` takes a plain list for a scalar field, so several statuses are one filter rather than a
    # fight with filter_operator (probe 017).
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
        return _coded(_search("Version", filters, ["code", "sg_status_list"],
                              sort=sort, limit=limit))
    key = ("find", json.dumps(filters, sort_keys=True, default=str), sort, limit)
    return _cached(key, fetch)


def versions_on(link_type, link_id, project_id, limit=200, sort="-id"):
    """(code, status, id) for every Version on one entity, newest first.

    Status comes back so the caller can ask for the latest approved one without a second round trip.
    """
    if not link_type or not link_id:
        return []
    return find_versions(project_id, link_type, link_id, sort=sort, limit=limit)


def cached_published_files(version_id):
    """The files on one Version, cached like every other site read.

    The panel asks for this on every preview, and scrubbing a picker must not turn into a request per
    keystroke. `forget("files")` is not needed: a publish takes a new version number, so the next
    preview asks about a different Version.
    """
    from . import media
    return _cached(("files", int(version_id)),
                   lambda: media.published_files(client(), int(version_id)))


def version_numbers(link_type, link_id, project_id, field, limit=200):
    """Existing values of a site's real version-number field, for the next one."""
    if not (link_type and link_id and field):
        return []

    def fetch():
        filters = [_is("project", "Project", project_id), _is("entity", link_type, link_id)]
        return [d["attributes"].get(field)
                for d in _search("Version", filters, [field], limit=limit)]
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


# recipe 010 — `url` reads as an empty string unless `image_data` is asked for in the SAME call, so
# ask for both. Dotted through the entity link, one call returns the Icon's own columns flattened
# into attributes (probe 003); undotted, `icon` is {id, name, type} and costs a second call.
ICON_FIELDS = ("display_type", "image_map_key", "html", "url", "image_data")


def _stylesheets():
    """The web app's own CSS, concatenated. ~771KB on the probed site, so cached.

    recipe 010 — the stock icon sheet is not in the REST API at all. `image_map_key` is a CSS class in
    a stylesheet the site names in its own root page, behind a per-release hash, so both are
    rediscovered rather than hardcoded. Neither fetch carries the Authorization header.
    """
    def fetch():
        base = client().site
        root = requests.get(base, timeout=30)
        if not root.ok:
            return ""
        out = []
        for href in re.findall(r"""href=["']([^"']+\.css[^"']*)["']""", root.text, re.I):
            r = requests.get(href if href.startswith("http") else f"{base}{href}", timeout=60)
            if r.ok:
                out.append(r.text)
        return "\n".join(out)
    return _cached(("stylesheets",), fetch) or ""


def _sprite(key):
    """The crop for one stock icon: the sheet, the offset into it, and the size to take.

    None when the rule is not found — the signal to fall back to the colour badge.
    """
    css = _stylesheets()
    m = re.search(r"\.%s\b[^{}]*\{([^{}]*)\}" % re.escape(key), css) if key and css else None
    if not m:
        return None
    decl = m.group(1)
    href = re.search(r"url\(\s*['\"]?([^'\")]+)", decl)
    offset = re.search(r"(-?\d+)px\s+(-?\d+)px", decl)
    size = re.search(r"width:\s*(\d+)px.*?height:\s*(\d+)px", decl, re.S)
    if not (href and offset and size):
        return None
    url = href.group(1)
    return {"kind": "sprite",
            "url": url if url.startswith("http") else f"{client().site}{url}",
            "offset": [int(offset.group(1)), int(offset.group(2))],
            "size": [int(size.group(1)), int(size.group(2))]}


def status_icons():
    """{code: icon} — what can actually be drawn for a status, all three renderings resolved.

    recipe 010. `image_map` is the 94 stock icons and resolves through the site's stylesheet;
    `image` is a custom upload whose url is a self-contained data: URI; `html` is a text badge.
    """
    def fetch():
        fields = "code," + ",".join(f"icon.Icon.{f}" for f in ICON_FIELDS)
        r = client().get("/entity/statuses", params={"fields": fields, "page[size]": 200})
        if not r.ok:
            return {}
        out = {}
        for d in r.json()["data"]:
            a = d["attributes"]
            code, display = a.get("code"), a.get("icon.Icon.display_type")
            if not code:
                continue
            if display == "image_map":
                icon = _sprite(a.get("icon.Icon.image_map_key"))
            elif display == "image":
                # newlines in the base64 break an <img src> (probe 010)
                icon = {"kind": "data_uri", "url": (a.get("icon.Icon.url") or "").replace("\n", "")}
            elif display == "html":
                icon = {"kind": "text", "html": a.get("icon.Icon.html") or ""}
            else:
                icon = None
            if icon:
                out[code] = icon
        return out
    return _cached(("status_icons",), fetch)


# What a bare `{entity}` / `{sg_task}` / `{project}` resolves to. A Task is named by `content` and a
# Project by `name`; everything a Version hangs off is named by `code` (entity_types/Task, /Shot).
NAME_FIELD = {"Task": "content", "Project": "name"}


def resolve_paths(paths, project_id, link_type="", link_id=0, task_id=0, extra=None):
    """{path: value} for template paths like `entity.Shot.code` or `task.Task.content`.

    The prefix names which entity to read — `entity` the thing the Version hangs off, `task` its Task,
    `project` the show — and the last segment is the field. A middle segment is the entity type, which
    Flow PT's own dotted syntax carries (probe 003) and which is ignorable here because the id already
    says what is being read.
    """
    out = dict(extra or {})
    wanted = {}
    for p in paths:
        if p in out:
            continue
        bits = p.split(".")
        prefix = bits[0]
        who = ((link_type, int(link_id)) if prefix == "entity" and link_type and link_id
               else ("Task", int(task_id)) if prefix in ("task", "sg_task") and task_id
               else ("Project", int(project_id)) if prefix == "project" and project_id
               else None)
        if not who:
            continue
        # A BARE token is that link's own name, the way Flow PT hands one back in a relationship
        # dict; which field that is depends on the type (NAME_FIELD).
        #
        # A DOTTED token is handed to the server verbatim, minus the hops we already hold an id for:
        # `sg_task.Task.entity.Shot.code` becomes `entity.Shot.code` asked of that Task. probe 003 —
        # the answer comes back flat under the literal dotted key, which is why `field` is both what
        # is asked for and what is read.
        field = NAME_FIELD.get(who[0], "code") if len(bits) == 1 else (".".join(bits[2:]) or bits[-1])
        wanted.setdefault(who, []).append((p, field))

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


def status_usage(project_id, days=30, entity_type="Version", field="sg_status_list"):
    """{code: count} — how often this show actually used each status recently.

    probe 020 — one `_summarize` with `grouping` returns a count per distinct value for the price of
    one call, so this is cheap enough to sit in a picker. The schema's order is alphabetical-ish and
    says nothing about the show; what a person reaches for is what they reached for last month.
    """
    if not project_id:
        return {}

    def fetch():
        since = (datetime.datetime.now(datetime.timezone.utc)
                 - datetime.timedelta(days=int(days))).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = client().post(f"{route(entity_type)}/_summarize", headers=ARRAY_JSON, json={
            "filters": [_is("project", "Project", project_id),
                        ["created_at", "greater_than", since]],
            "summary_fields": [{"field": "id", "type": "count"}],
            "grouping": [{"field": field, "type": "exact", "direction": "asc"}]})
        if not r.ok:
            return {}
        return {g.get("group_value"): (g.get("summaries") or {}).get("id", 0)
                for g in (r.json().get("data") or {}).get("groups", []) if g.get("group_value")}
    return _cached(("status_usage", int(project_id), int(days), entity_type, field), fetch)


def statuses(project_id, entity_type="Version", field="sg_status_list"):
    """(display label, code) actually usable in this project.

    probe 009 — usable is valid_values MINUS hidden_values, read with project_id; valid_values alone
    is identical at every scope and is not the answer. Labels matter: 'pndvs' means nothing to a user.
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
