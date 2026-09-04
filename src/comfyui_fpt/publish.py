"""Writing to Flow PT. Every call here is verified by a probe; see corpus recipe 001.

Publish path only: REST through sg_groundtruth, requests for the presigned PUT, nothing else.
"""
import json

import requests

from . import _deps  # noqa: F401  puts sg_groundtruth on sys.path
from sg_groundtruth.client import FPTError


def create_version(fpt, project_id, code, fields=None):
    """probe 012 — entity links are {type, id}; project is required despite not being schema-mandatory."""
    body = {"project": {"type": "Project", "id": int(project_id)}, "code": code}
    body.update(fields or {})
    r = fpt.post("/entity/versions", json=body)
    if not r.ok:
        raise FPTError(f"create version {r.status_code}: {r.text[:300]}")
    return r.json()["data"]["id"]


def upload(fpt, version_id, payload, filename, field=None):
    """Three-step presigned upload (probe 013).

    field=None attaches the file as a standalone Attachment entity instead of filling a field (probe 014).
    """
    path = f"/entity/versions/{version_id}/_upload" if field is None \
        else f"/entity/versions/{version_id}/{field}/_upload"
    r = fpt.get(path, params={"filename": filename})
    if not r.ok:
        raise FPTError(f"upload init {field or 'attachment'} {r.status_code}: {r.text[:300]}")
    b = r.json()

    put = requests.put(b["links"]["upload"], data=payload, timeout=300)
    if not put.ok:
        raise FPTError(f"upload put {field or 'attachment'} {put.status_code}")

    # upload_data must be present even though it is empty (probe 013).
    done = fpt.post(b["links"]["complete_upload"], json={"upload_info": b["data"], "upload_data": {}})
    if not done.ok:
        raise FPTError(f"upload complete {field or 'attachment'} {done.status_code}: {done.text[:300]}")


def attach_json(fpt, version_id, obj, filename):
    upload(fpt, version_id, json.dumps(obj, indent=2).encode(), filename, field=None)


def storages(fpt):
    """Every LocalStorage row, with the root it defines per platform (recipe 004).

    Read at publish time, not cached with the editor's lookups: a path that does not sit under one of
    these roots is refused with 400 code 104, so this is the one read the frames' destination depends
    on.
    """
    r = fpt.get("/entity/local_storages",
                params={"fields": "code,mac_path,windows_path,linux_path"})
    if not r.ok:
        raise FPTError(f"local storages {r.status_code}: {r.text[:200]}")
    return [{"id": d["id"], **d["attributes"]} for d in r.json().get("data", [])
            if d["attributes"].get("code")]


def published_file_type(fpt, candidates):
    """The first of `candidates` this site already has, matched case-insensitively (recipe 004).

    Never creates one: PublishedFileType has no `project`, so a create adds it to every show on the
    site. A miss returns None and the caller says so — an unlabelled publish is honest, an invented
    site-wide type is not.
    """
    r = fpt.get("/entity/published_file_types", params={"fields": "code", "page[size]": 200})
    if not r.ok:
        return None
    have = {(d["attributes"].get("code") or "").strip().lower(): d["id"]
            for d in r.json().get("data", [])}
    for want in candidates:
        if want.strip().lower() in have:
            return {"type": "PublishedFileType", "id": have[want.strip().lower()]}
    return None


def published_files_of(fpt, version_ids, exact=None):
    """Every PublishedFile hanging off these Versions — the upstream half of a dependency link.

    `upstream_published_files` is the PublishedFile-level twin of `sg_ai_generated_from`: the node
    already knows which Versions this one came from, and where those Versions carry files, the files
    are what a downstream tool actually opens.

    `exact` is {version_id: [published_file_id]} for ancestors a Load node actually read a file
    from (lineage.py). Those Versions are not searched: the dependency is the one file that was
    opened, not every file that Version ever published, which on a Version carrying a sequence AND
    its mp4 is the difference between a true link and a plausible one. Every other ancestor still
    gets the search, because approximate is the honest answer where nothing narrower is known.
    """
    exact = exact or {}
    ids = [int(v) for v in version_ids if v]
    out = [{"type": "PublishedFile", "id": int(i)} for v in ids for i in exact.get(v, [])]
    rest = [v for v in ids if v not in exact]
    if not rest:
        return out
    from .site import ARRAY_JSON
    r = fpt.post("/entity/published_files/_search", headers=ARRAY_JSON, json={
        "filters": [["version", "in", [{"type": "Version", "id": i} for i in rest]]],
        "fields": ["code"], "page": {"size": 200}})
    if not r.ok:
        return out
    return out + [{"type": "PublishedFile", "id": d["id"]} for d in r.json().get("data", [])]


def create_published_file(fpt, project_id, code, name, local_path, fields=None):
    """recipe 004 — one create, forward slashes only, and the server splits the root off `local_path`.

    The 201 already carries the resolved `path`, so nothing needs reading back: `local_storage`,
    `relative_path` and every `local_path_*` whose root the LocalStorage row defines come back filled,
    and `path_cache_storage` with them. Returns (id, path) so the caller can report what resolved.

    Nothing on the server makes this unique: the identical body posted twice returns two 201s, so the
    version number is the client's convention and the guard is the query that produced it.
    """
    body = {"project": {"type": "Project", "id": int(project_id)},
            "code": code, "name": name, "path": {"local_path": local_path}}
    body.update(fields or {})
    r = fpt.post("/entity/published_files", json=body)
    if not r.ok:
        raise FPTError(f"create published file {r.status_code}: {r.text[:400]}")
    d = r.json()["data"]
    return d["id"], d["attributes"].get("path") or {}


def resolve_entity(fpt, entity_type, project_id, name, field="code"):
    """A dropdown carries names; Flow PT links want {type, id} (probe 012). One explicit lookup."""
    from .site import route
    r = fpt.get(route(entity_type), params={
        "filter[project.Project.id]": int(project_id),
        f"filter[{field}]": name, "fields": field, "page[size]": 2,
    })
    if not r.ok:
        raise FPTError(f"resolve {entity_type} {r.status_code}: {r.text[:200]}")
    data = r.json().get("data", [])
    if not data:
        raise FPTError(f"no {entity_type} named {name!r} in project {project_id}")
    return data[0]["id"]
