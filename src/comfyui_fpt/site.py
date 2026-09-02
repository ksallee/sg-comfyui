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
import time
from pathlib import Path

from . import _deps  # noqa: F401  puts fpt_llm_api on sys.path
from fpt_llm_api.client import FPT, FPTError

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env.local"
PROFILE = ROOT / "profile.local.json"

# probe 004 — _search rejects application/json with 415 and demands a vendor type.
ARRAY_JSON = {"Content-Type": "application/vnd+shotgun.api3_array+json"}

TTL = 60.0
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


def entities(entity_type, project_id, q="", field="code", limit=200):
    """(name, id) for a link picker, filtered server-side.

    probe 017 — `contains` is real, and an unknown operator 400s rather than passing silently, so a bad
    filter cannot masquerade as an unfiltered list.
    """
    if not entity_type or not project_id:
        return []

    def fetch():
        filters = [["project", "is", {"type": "Project", "id": int(project_id)}]]
        if q:
            filters.append([field, "contains", q])
        r = client().post(f"{route(entity_type)}/_search", headers=ARRAY_JSON,
                          json={"filters": filters, "fields": [field], "page": {"size": limit}})
        return [] if not r.ok else [(d["attributes"][field], d["id"]) for d in r.json()["data"]
                                    if d["attributes"].get(field)]
    return _cached(("entities", entity_type, int(project_id), q, field), fetch)


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


def versions_on(link_type, link_id, project_id, limit=200):
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
                                "fields": ["code", "sg_status_list"], "sort": "-id",
                                "page": {"size": limit}})
        return [] if not r.ok else [(d["attributes"].get("code") or "",
                                     d["attributes"].get("sg_status_list") or "", d["id"])
                                    for d in r.json()["data"]]
    return _cached(("versions_on", link_type, int(link_id), int(project_id)), fetch)


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
