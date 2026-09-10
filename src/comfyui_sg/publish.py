"""Writing to SG: Versions, uploads, attachments and PublishedFiles.

Publish path only. REST through sg_groundtruth, `requests` for the presigned PUT. Every call here is
verified by a probe; see corpus recipe 001.
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
    """probe 012: entity links are {type, id}, and project is required though not schema-mandatory."""
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
    """The same three-step upload, streamed off disk rather than read into memory.

    A clip is the one payload here with no size ceiling. Reading it into a bytes object to hand to
    `requests` doubles the memory it takes.
    """
    with open(path, "rb") as fh:
        upload(sg, version_id, fh, filename, field=field)


def attach_json(sg, version_id, obj, filename):
    upload(sg, version_id, json.dumps(obj, indent=2).encode(), filename, field=None)


def storages(sg):
    """Every LocalStorage row, with the root it defines per platform (recipe 004).

    Read at publish time rather than cached with the editor's lookups. A path outside one of these
    roots is refused with 400 code 104.
    """
    r = _ok(sg.get("/entity/local_storages",
                    params={"fields": "code,mac_path,windows_path,linux_path"}),
            "read the storage list", cut=200)
    return [{"id": d["id"], **d["attributes"]} for d in r.json().get("data", [])
            if d["attributes"].get("code")]


def published_file_type(sg, candidates):
    """(the first of `candidates` this site has, a sentence where the read failed).

    Matched case-insensitively (recipe 004). Never creates one: PublishedFileType has no `project`,
    so a create adds it to every show on the site. A miss returns None with no sentence. A site that
    has no such type is the caller's to report; a site that refused the read is reported here.
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
    """(every PublishedFile on these Versions, a sentence where the search failed).

    The upstream half of a dependency link. `upstream_published_files` is the PublishedFile-level
    twin of `sg_ai_generated_from`, and a downstream tool opens files rather than Versions.

    `exact` is {version_id: [published_file_id]} for ancestors a Load node read a file from
    (lineage.py). Those Versions are not searched: the dependency is the one file that was opened,
    not every file that Version published. Every other ancestor gets the search.
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
    """recipe 004: one create, forward slashes only, the server splits the root off `local_path`.

    The 201 returns the resolved `path`, so nothing needs reading back: `local_storage`,
    `relative_path`, every `local_path_*` whose root the LocalStorage row defines, and
    `path_cache_storage` come back filled. Returns (id, path) for the caller to report.

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
    """A dropdown gives a name; an SG link needs {type, id} (probe 012). One explicit lookup."""
    r = _ok(sg.get(site.route(entity_type), params={
        "filter[project.Project.id]": int(project_id),
        f"filter[{field}]": name, "fields": field, "page[size]": 2,
    }), f"find the {entity_type}", cut=200)
    data = r.json().get("data", [])
    if not data:
        raise FPTError(f"No {entity_type} named {name} on project {project_id}. "
                       f"Check the spelling, or pick another one.")
    return data[0]["id"]
