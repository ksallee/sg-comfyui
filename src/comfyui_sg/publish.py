"""Writing to SG: Versions, uploads, attachments and PublishedFiles.

Publish path only — REST through sg_groundtruth, `requests` for the presigned PUT, nothing else.
Every call here is verified by a probe; see corpus recipe 001.
"""
import json

import requests

from sg_groundtruth.client import FPTError

from . import site


def _ok(r, what, cut=300):
    """The response, or an FPTError naming the step and what the server said."""
    if not r.ok:
        raise FPTError(f"Could not {what}. Check the values on the node, then run again. "
                       f"The site answered {r.status_code}. {r.text[:cut]}")
    return r


def create_version(sg, project_id, code, fields=None):
    """probe 012 — entity links are {type, id}; project is required despite not being schema-mandatory."""
    body = {"project": {"type": "Project", "id": int(project_id)}, "code": code}
    body.update(fields or {})
    r = _ok(sg.post("/entity/versions", json=body), "create the Version")
    return r.json()["data"]["id"]


def upload(sg, version_id, payload, filename, field=None):
    """Three-step presigned upload (probe 013).

    field=None attaches the file as a standalone Attachment entity instead of filling a field (probe 014).
    """
    label = field or "attachment"
    path = f"/entity/versions/{version_id}/_upload" if field is None \
        else f"/entity/versions/{version_id}/{field}/_upload"
    b = _ok(sg.get(path, params={"filename": filename}), f"start the {label} upload").json()

    put = requests.put(b["links"]["upload"], data=payload, timeout=300)
    if not put.ok:
        raise FPTError(f"Sending the {label} file to storage failed. Check the network "
                       f"connection, then run again. The upload server answered {put.status_code}.")

    # upload_data must be present even though it is empty (probe 013).
    _ok(sg.post(b["links"]["complete_upload"],
                 json={"upload_info": b["data"], "upload_data": {}}), f"finish the {label} upload")


def upload_file(sg, version_id, path, filename, field=None):
    """The same three-step upload, streamed off disk rather than held in memory.

    A clip is the one payload here with no ceiling — a long plate is gigabytes — and reading it into
    a bytes object only to hand it to `requests` doubles that for nothing.
    """
    with open(path, "rb") as fh:
        upload(sg, version_id, fh, filename, field=field)


def attach_json(sg, version_id, obj, filename):
    upload(sg, version_id, json.dumps(obj, indent=2).encode(), filename, field=None)


def storages(sg):
    """Every LocalStorage row, with the root it defines per platform (recipe 004).

    Read at publish time rather than cached with the editor's lookups: a path that does not sit under
    one of these roots is refused with 400 code 104, so this is the one read the frames' destination
    depends on.
    """
    r = _ok(sg.get("/entity/local_storages",
                    params={"fields": "code,mac_path,windows_path,linux_path"}),
            "read the storage list", cut=200)
    return [{"id": d["id"], **d["attributes"]} for d in r.json().get("data", [])
            if d["attributes"].get("code")]


def published_file_type(sg, candidates):
    """(the first of `candidates` this site has, a sentence where the site would not say).

    Matched case-insensitively (recipe 004). Never creates one: PublishedFileType has no `project`,
    so a create adds it to every show on the site. A miss returns None with no sentence, because a
    site that genuinely has no such type is the caller's story to tell; a site that refused the read
    is this function's, and the two must not be reported as one.
    """
    r = sg.get("/entity/published_file_types", params={"fields": "code", "page[size]": 200})
    if not r.ok:
        return None, (f"The Published File Type list could not be read, so the file was registered "
                      f"without a type. Run again. The site answered {r.status_code}.")
    have = {(d["attributes"].get("code") or "").strip().lower(): d["id"]
            for d in r.json().get("data", [])}
    for want in candidates:
        if want.strip().lower() in have:
            return {"type": "PublishedFileType", "id": have[want.strip().lower()]}, ""
    return None, ""


def published_files_of(sg, version_ids, exact=None):
    """(every PublishedFile hanging off these Versions, a sentence where the search failed).

    The upstream half of a dependency link.

    `upstream_published_files` is the PublishedFile-level twin of `sg_ai_generated_from`: the node
    already knows which Versions this one came from, and where those Versions carry files, the files
    are what a downstream tool actually opens.

    `exact` is {version_id: [published_file_id]} for ancestors a Load node actually read a file from
    (lineage.py). Those Versions are not searched: the dependency is the one file that was opened,
    not every file that Version ever published, which on a Version carrying a sequence AND its mp4 is
    the difference between a true link and a plausible one. Every other ancestor gets the search,
    because approximate is the honest answer where nothing narrower is known.
    """
    exact = exact or {}
    ids = [int(v) for v in version_ids if v]
    out = [{"type": "PublishedFile", "id": int(i)} for v in ids for i in exact.get(v, [])]
    rest = [v for v in ids if v not in exact]
    if not rest:
        return out, ""
    r = sg.post("/entity/published_files/_search", headers=site.ARRAY_JSON, json={
        "filters": [["version", "in", [{"type": "Version", "id": i} for i in rest]]],
        "fields": ["code"], "page": {"size": 200}})
    if not r.ok:
        return out, (f"The source versions' published files could not be read, so nothing upstream "
                     f"was linked. Run again. The site answered {r.status_code}.")
    return out + [{"type": "PublishedFile", "id": d["id"]} for d in r.json().get("data", [])], ""


def create_published_file(sg, project_id, code, name, local_path, fields=None):
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
    r = _ok(sg.post("/entity/published_files", json=body), "create the Published File", cut=400)
    d = r.json()["data"]
    return d["id"], d["attributes"].get("path") or {}


def resolve_entity(sg, entity_type, project_id, name, field="code"):
    """A dropdown carries names; SG links want {type, id} (probe 012). One explicit lookup."""
    r = _ok(sg.get(site.route(entity_type), params={
        "filter[project.Project.id]": int(project_id),
        f"filter[{field}]": name, "fields": field, "page[size]": 2,
    }), f"find the {entity_type}", cut=200)
    data = r.json().get("data", [])
    if not data:
        raise FPTError(f"No {entity_type} named {name} on project {project_id}. "
                       f"Check the spelling, or pick another one.")
    return data[0]["id"]
