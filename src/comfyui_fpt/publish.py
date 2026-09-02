"""Writing to Flow PT. Every call here is verified by a probe; see corpus recipe 001.

Publish path only: REST through fpt_llm_api, requests for the presigned PUT, nothing else.
"""
import json

import requests

from . import _deps  # noqa: F401  puts fpt_llm_api on sys.path
from fpt_llm_api.client import FPTError


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


def resolve_entity(fpt, entity_type, project_id, name, field="code"):
    """A dropdown carries names; Flow PT links want {type, id} (probe 012). One explicit lookup."""
    from .site import entity_route
    r = fpt.get(entity_route(entity_type), params={
        "filter[project.Project.id]": int(project_id),
        f"filter[{field}]": name, "fields": field, "page[size]": 2,
    })
    if not r.ok:
        raise FPTError(f"resolve {entity_type} {r.status_code}: {r.text[:200]}")
    data = r.json().get("data", [])
    if not data:
        raise FPTError(f"no {entity_type} named {name!r} in project {project_id}")
    return data[0]["id"]
